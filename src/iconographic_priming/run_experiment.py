"""Main entrypoint: run the iconographic-priming experiment.

Iterates over (model × arm × run × scenario), calls the API (or hits cache),
streams scored results to JSONL files (one per stratum) under results/runs/<ts>/.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Make sure VirtueBench-2 is importable.
VBE_PATH = Path(os.environ.get("VBE_PATH", "/tmp/virtue-bench-2"))
if VBE_PATH.exists() and str(VBE_PATH / "src") not in sys.path:
    sys.path.insert(0, str(VBE_PATH / "src"))

# Ensure the data dir is set so the loader finds the CSVs in the cloned repo.
os.environ.setdefault("VBE_DATA", str(VBE_PATH / "data"))

# Patch DATA_DIR before import (constants.py resolves relative to its own location).
from virtue_bench.core import constants as _vb_constants  # noqa: E402

_vb_constants.DATA_DIR = VBE_PATH / "data"

from virtue_bench.core.constants import DEFAULT_SYSTEM_PROMPT  # noqa: E402
from virtue_bench.core.loader import load_scenarios, prepare_samples  # noqa: E402

from .clients.anthropic_client import AnthropicClient  # noqa: E402
from .clients.openai_client import OpenAIClient  # noqa: E402
from .images import by_category, load_manifest  # noqa: E402
from .runner import ARMS, CallSpec, run_one_call, select_image_for_arm  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "results" / "cache"
RUNS_DIR = PROJECT_ROOT / "results" / "runs"

# §5.2 used psalms in system prompt. We can't put images in system prompt (API
# constraint), so the image is in the user message. Adding this neutral line to the
# system prompt keeps system text identical across arms (constant whether or not
# an image is attached).
SYSTEM_PROMPT = (
    DEFAULT_SYSTEM_PROMPT
    + "You may receive supplementary visual context with each scenario.\n"
)

DEFAULT_BASE_SEED = 42  # matches VirtueBench-2's default
DEFAULT_TEMPERATURE = 0.7  # matches §5.2

# Models that removed user-controllable temperature. We record 1.0 (the model
# default) in the cache key so these runs don't collide with 0.7 runs of the
# same scenario+image. The client skips the param at API send time.
NO_TEMP_MODELS = {"claude-opus-4-7", "gpt-5.5"}


def _effective_temperature(model_id: str, requested: float) -> float:
    return 1.0 if any(model_id.startswith(m) for m in NO_TEMP_MODELS) else requested


def _client_for(model_id: str):
    if model_id.startswith("claude-"):
        return AnthropicClient(model=model_id)
    if model_id.startswith("gpt-") or model_id.startswith("o"):
        return OpenAIClient(model=model_id)
    raise ValueError(f"Unknown model family for: {model_id}")


def _stratum_path(out_dir: Path, model_id: str, arm: str, virtue: str, variant: str) -> Path:
    safe_model = model_id.replace("/", "_")
    return out_dir / f"{safe_model}__{virtue}__{variant}__{arm}.jsonl"


async def run_stratum(
    *,
    model_id: str,
    arm: str,
    virtue: str,
    variant: str,
    runs: int,
    base_seed: int,
    temperature: float,
    limit: int | None,
    out_dir: Path,
    cache_dir: Path,
    sacred_bundle,
    neutral_bundle,
    concurrency: int,
    pinned_sacred_id: str | None = None,
    pinned_neutral_id: str | None = None,
) -> dict:
    """Run all (run_index × scenario) calls for one (model, arm, virtue, variant) cell.

    Streams results to a JSONL file. Returns summary stats.
    """
    client = _client_for(model_id)
    sem = asyncio.Semaphore(concurrency)

    out_path = _stratum_path(out_dir, model_id, arm, virtue, variant)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Build the full call list across all runs.
    all_specs: list[tuple[CallSpec, object]] = []  # (spec, image_or_None)
    eff_temp = _effective_temperature(model_id, temperature)
    for run_idx in range(runs):
        ab_seed = base_seed + run_idx
        scenarios = load_scenarios(virtue, variants=[variant])
        samples = prepare_samples(scenarios, seed=ab_seed, limit=limit)
        for s in samples:
            spec = CallSpec(
                model_id=model_id,
                arm=arm,
                scenario_text=s.prompt,
                target=s.target,
                virtue=virtue,
                variant=variant,
                base_id=s.scenario.base_id,
                run_index=run_idx,
                ab_seed=ab_seed,
                system_prompt=SYSTEM_PROMPT,
                temperature=eff_temp,
            )
            # If the arm is pinned to a single image, override the rotation.
            if arm == "sacred" and pinned_sacred_id:
                image = next(e for e in sacred_bundle if e.id == pinned_sacred_id)
            elif arm == "neutral" and pinned_neutral_id:
                image = next(e for e in neutral_bundle if e.id == pinned_neutral_id)
            else:
                image = select_image_for_arm(
                    arm,
                    sacred_bundle=sacred_bundle,
                    neutral_bundle=neutral_bundle,
                    base_id=s.scenario.base_id,
                    run_index=run_idx,
                )
            all_specs.append((spec, image))

    n_total = len(all_specs)
    print(f"  [{model_id} | {virtue}/{variant} | arm={arm}] {n_total} calls "
          f"(runs={runs}, scenarios={n_total // runs}, concurrency={concurrency})", flush=True)

    n_done = 0
    n_correct = 0
    n_infra_err = 0
    n_cache_hits = 0
    t_start = time.time()

    with open(out_path, "w", encoding="utf-8") as f:
        async def process(spec_image):
            nonlocal n_done, n_correct, n_infra_err, n_cache_hits
            spec, image = spec_image
            rec = await run_one_call(spec, client=client, image=image,
                                     cache_dir=cache_dir, sem=sem)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n_done += 1
            if rec.get("from_cache"):
                n_cache_hits += 1
            if rec.get("infra_error"):
                n_infra_err += 1
            elif rec.get("correct"):
                n_correct += 1
            if n_done % 50 == 0 or n_done == n_total:
                rate = n_done / max(time.time() - t_start, 1e-6)
                acc_so_far = n_correct / max(n_done - n_infra_err, 1)
                print(f"    {n_done}/{n_total}  acc={acc_so_far:.3f}  "
                      f"infra_err={n_infra_err}  cache={n_cache_hits}  {rate:.1f}/s",
                      flush=True)

        await asyncio.gather(*(process(si) for si in all_specs))

    elapsed = time.time() - t_start
    n_scored = n_done - n_infra_err
    accuracy = n_correct / n_scored if n_scored else None
    print(f"  [{model_id} | {virtue}/{variant} | arm={arm}] DONE "
          f"acc={accuracy if accuracy is not None else 'N/A'}  "
          f"infra={n_infra_err}/{n_total}  cache={n_cache_hits}  {elapsed:.1f}s -> {out_path.name}",
          flush=True)
    return {
        "model": model_id,
        "arm": arm,
        "virtue": virtue,
        "variant": variant,
        "n_total": n_total,
        "n_correct": n_correct,
        "n_infra_err": n_infra_err,
        "n_cache_hits": n_cache_hits,
        "accuracy": accuracy,
        "elapsed_sec": elapsed,
        "output": str(out_path),
    }


async def run_experiment(args: argparse.Namespace) -> int:
    bundle = load_manifest()
    sacred_bundle = by_category(bundle, "sacred")
    neutral_bundle = by_category(bundle, "neutral")
    print(f"Loaded {len(sacred_bundle)} sacred + {len(neutral_bundle)} neutral images.",
          flush=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    out_dir = RUNS_DIR / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    # Persist run config alongside outputs.
    config = vars(args).copy()
    config["timestamp"] = ts
    config["sacred_bundle_ids"] = [e.id for e in sacred_bundle]
    config["neutral_bundle_ids"] = [e.id for e in neutral_bundle]
    config["sacred_bundle_sha256"] = [e.sha256 for e in sacred_bundle]
    config["neutral_bundle_sha256"] = [e.sha256 for e in neutral_bundle]
    config["system_prompt"] = SYSTEM_PROMPT
    (out_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    summaries: list[dict] = []
    for model_id in args.models:
        for virtue in args.virtues:
            for variant in args.variants:
                for arm in args.arms:
                    summary = await run_stratum(
                        model_id=model_id,
                        arm=arm,
                        virtue=virtue,
                        variant=variant,
                        runs=args.runs,
                        base_seed=args.base_seed,
                        temperature=args.temperature,
                        limit=args.limit,
                        out_dir=out_dir,
                        cache_dir=CACHE_DIR,
                        sacred_bundle=sacred_bundle,
                        neutral_bundle=neutral_bundle,
                        concurrency=args.concurrency,
                        pinned_sacred_id=args.sacred_image,
                        pinned_neutral_id=args.neutral_image,
                    )
                    summaries.append(summary)
                    (out_dir / "summary.json").write_text(
                        json.dumps(summaries, indent=2), encoding="utf-8"
                    )

    print(f"\nAll strata complete. Output: {out_dir}", flush=True)
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run iconographic-priming experiment.")
    p.add_argument("--models", nargs="+", default=["claude-opus-4-6", "gpt-5.4"])
    p.add_argument("--virtues", nargs="+", default=["courage"])
    p.add_argument("--variants", nargs="+", default=["ratio"])
    p.add_argument("--arms", nargs="+", default=list(ARMS),
                   choices=ARMS, help="Which arms to run.")
    p.add_argument("--runs", type=int, default=5)
    p.add_argument("--base-seed", type=int, default=DEFAULT_BASE_SEED)
    p.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    p.add_argument("--limit", type=int, default=None,
                   help="Limit scenarios per (virtue,variant). Useful for smoke tests.")
    p.add_argument("--concurrency", type=int, default=20)
    p.add_argument("--sacred-image", default=None,
                   help="Force the sacred arm to always use this single image id "
                        "(e.g. sacred_07_fra_angelico_annunciation). Default rotates the bundle.")
    p.add_argument("--neutral-image", default=None,
                   help="Force the neutral arm to always use this single image id. "
                        "Default rotates the bundle.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    return asyncio.run(run_experiment(args))


if __name__ == "__main__":
    sys.exit(main())
