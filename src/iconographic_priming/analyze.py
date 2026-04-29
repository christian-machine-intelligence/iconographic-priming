"""Analysis: load JSONL results, compute per-arm accuracy, run paired permutation tests
across (Baseline, Neutral, Sacred), apply Bonferroni correction, emit a results table.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = PROJECT_ROOT / "results" / "runs"


def load_records(run_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for jsonl in sorted(run_dir.glob("*.jsonl")):
        for line in jsonl.open(encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("infra_error"):
                continue  # exclude infra failures from accuracy stats
            if r.get("model_answer") is None:
                continue  # unparseable response = miss; treat as incorrect
            rows.append(r)
    return rows


def accuracy_by(rows: Iterable[dict], *keys: str) -> dict[tuple, float]:
    by: dict[tuple, list[bool]] = defaultdict(list)
    for r in rows:
        k = tuple(r[key] for key in keys)
        by[k].append(bool(r["correct"]))
    return {k: sum(v) / len(v) if v else float("nan") for k, v in by.items()}


def bootstrap_ci(correct: list[bool], n_boot: int = 10_000, alpha: float = 0.05,
                 rng: np.random.Generator | None = None) -> tuple[float, float, float]:
    rng = rng or np.random.default_rng(42)
    arr = np.asarray(correct, dtype=np.int8)
    n = len(arr)
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    means = arr[rng.integers(0, n, size=(n_boot, n))].mean(axis=1)
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return float(arr.mean()), float(lo), float(hi)


def cohens_h(p1: float, p2: float) -> float:
    """Cohen's h effect size for proportions."""
    def phi(p: float) -> float:
        p = min(max(p, 0.0), 1.0)
        return 2 * math.asin(math.sqrt(p))
    return phi(p1) - phi(p2)


def permutation_test_paired(
    rows_a: list[dict],
    rows_b: list[dict],
    *,
    pair_keys: tuple[str, ...] = ("model", "virtue", "variant", "base_id", "run_index"),
    n_permutations: int = 10_000,
    rng_seed: int = 0,
) -> tuple[float, float]:
    """Paired permutation test: shuffle the arm label within each (model,...,run_index)
    tuple, recompute Δ = mean(a.correct) − mean(b.correct), and count tail extremity.

    Returns (delta_obs, two_sided_p).
    """
    by_key_a = {tuple(r[k] for k in pair_keys): bool(r["correct"]) for r in rows_a}
    by_key_b = {tuple(r[k] for k in pair_keys): bool(r["correct"]) for r in rows_b}
    common = set(by_key_a) & set(by_key_b)
    if not common:
        return float("nan"), float("nan")
    keys = sorted(common)
    a = np.array([by_key_a[k] for k in keys], dtype=np.int8)
    b = np.array([by_key_b[k] for k in keys], dtype=np.int8)

    rng = np.random.default_rng(rng_seed)
    diffs = a.astype(np.int16) - b.astype(np.int16)
    n = len(diffs)
    # Compare in integer sum space to avoid floating-point boundary errors:
    # |perm_sum| >= |obs_sum| is exact, while |perm_mean| >= |obs_mean| can
    # silently miss equal-but-not-identical floats.
    obs_sum = int(diffs.sum())
    delta_obs = obs_sum / n

    flips = rng.choice([-1, 1], size=(n_permutations, n)).astype(np.int16)
    perm_sums = (flips * diffs[None, :]).sum(axis=1)
    p = float((np.abs(perm_sums) >= abs(obs_sum)).mean())
    p = max(p, 1.0 / n_permutations)
    return delta_obs, p


def bonferroni(ps: list[float], alpha: float = 0.05) -> list[tuple[float, bool]]:
    n = len(ps)
    return [(min(p * n, 1.0), p * n <= alpha) for p in ps]


def analyze_run(run_dir: Path) -> str:
    rows = load_records(run_dir)
    if not rows:
        return f"No valid records in {run_dir}\n"

    models = sorted({r["model"] for r in rows})
    virtues = sorted({r["virtue"] for r in rows})
    variants = sorted({r["variant"] for r in rows})

    out = [f"# Iconographic Priming Results — {run_dir.name}", ""]
    out.append(f"Records: {len(rows)} (after dropping infra errors and unparseable responses)")
    out.append(f"Models: {', '.join(models)}")
    out.append(f"Virtues: {', '.join(virtues)}    Variants: {', '.join(variants)}")
    out.append("")

    # Per-arm accuracy with bootstrap 95% CI per (model, virtue, variant).
    out.append("## Per-arm accuracy (95% bootstrap CI)")
    out.append("")
    rng = np.random.default_rng(42)
    for model in models:
        for virtue in virtues:
            for variant in variants:
                out.append(f"### {model} — {virtue}/{variant}")
                out.append("")
                out.append("| Arm | n | Accuracy | 95% CI |")
                out.append("|---|---|---|---|")
                for arm in ("baseline", "neutral", "sacred"):
                    cell = [bool(r["correct"]) for r in rows
                            if r["model"] == model and r["virtue"] == virtue
                            and r["variant"] == variant and r["arm"] == arm]
                    if not cell:
                        out.append(f"| {arm} | 0 | N/A | N/A |")
                        continue
                    acc, lo, hi = bootstrap_ci(cell, rng=rng)
                    out.append(f"| {arm} | {len(cell)} | {acc:.3f} | [{lo:.3f}, {hi:.3f}] |")
                out.append("")

    # Pairwise contrasts with paired permutation test, Bonferroni-corrected.
    out.append("## Pairwise contrasts (paired permutation test, Bonferroni-corrected)")
    out.append("")
    contrasts = [("sacred", "neutral"), ("sacred", "baseline"), ("neutral", "baseline")]
    raw_results: list[tuple] = []
    for model in models:
        for virtue in virtues:
            for variant in variants:
                cell = [r for r in rows if r["model"] == model and r["virtue"] == virtue
                        and r["variant"] == variant]
                for a, b in contrasts:
                    rows_a = [r for r in cell if r["arm"] == a]
                    rows_b = [r for r in cell if r["arm"] == b]
                    delta, p = permutation_test_paired(rows_a, rows_b)
                    p_a = sum(1 for r in rows_a if r["correct"]) / max(len(rows_a), 1)
                    p_b = sum(1 for r in rows_b if r["correct"]) / max(len(rows_b), 1)
                    h = cohens_h(p_a, p_b)
                    raw_results.append((model, virtue, variant, a, b, delta, p, h))

    # Apply Bonferroni across all (model × virtue × variant × contrast) tests.
    ps = [t[6] for t in raw_results]
    corrected = bonferroni(ps, alpha=0.05) if ps else []
    out.append(f"_Total tests: {len(raw_results)}, Bonferroni α/n = {0.05 / max(len(raw_results), 1):.4f}_")
    out.append("")
    out.append("| Model | Virtue/Variant | Contrast | Δacc | p (raw) | p (Bonf) | reject@0.05 | Cohen's h |")
    out.append("|---|---|---|---|---|---|---|---|")
    for (model, virtue, variant, a, b, delta, p, h), (p_corr, reject) in zip(raw_results, corrected):
        sig = "✓" if reject else "—"
        out.append(
            f"| {model} | {virtue}/{variant} | {a} vs {b} "
            f"| {delta:+.3f} | {p:.4f} | {p_corr:.4f} | {sig} | {h:+.3f} |"
        )

    out.append("")
    out.append("Headline contrast = Sacred vs Neutral (the test of 'religious content effect').")
    out.append("If both Sacred-vs-Neutral rows reject at Bonferroni-corrected α=0.05,")
    out.append("the iconography hypothesis is supported on this slice.")
    return "\n".join(out) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", type=Path, default=None,
                   help="Run directory under results/runs/ (default: latest).")
    p.add_argument("--out", type=Path, default=None,
                   help="Output markdown path (default: <run-dir>/analysis.md).")
    args = p.parse_args()

    run_dir = args.run_dir
    if run_dir is None:
        runs = sorted(RUNS_DIR.iterdir())
        if not runs:
            print("No runs found.", file=sys.stderr)
            return 1
        run_dir = runs[-1]
    out_path = args.out or run_dir / "analysis.md"

    md = analyze_run(run_dir)
    out_path.write_text(md, encoding="utf-8")
    print(md)
    print(f"Wrote {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
