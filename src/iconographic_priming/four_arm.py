"""4-arm comparison chart: Baseline / Blank-gray / Hokusai / Annunciation
across the four cardinal virtues, for Opus 4.6 + GPT-5.4.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from .analyze import bootstrap_ci

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VIRTUE_ORDER = ["prudence", "justice", "courage", "temperance"]

ARM_INFO = [
    ("baseline",     "Baseline (no image)",         "#777777"),
    ("blank_gray",   "Blank gray (control)",        "#bbbbbb"),
    ("hokusai",      "Hokusai (Great Wave)",        "#5b8def"),
    ("annunciation", "Annunciation (Fra Angelico)", "#c44e52"),
]


def load_arm_records(run_dir: Path, model: str, virtue: str, file_arm: str) -> list[dict]:
    """Load records from one (model, virtue) cell of one run dir, filtering to file_arm."""
    p = run_dir / f"{model}__{virtue}__ratio__{file_arm}.jsonl"
    if not p.exists():
        return []
    rows = []
    for line in p.open():
        r = json.loads(line)
        if r.get("correct") is None:
            continue
        rows.append(r)
    return rows


def get_cell(model: str, virtue: str, arm: str, *, paths: dict) -> list[bool]:
    if arm == "baseline":
        rows = load_arm_records(paths["baseline"], model, virtue, "baseline")
    elif arm == "blank_gray":
        rows = load_arm_records(paths["blank_gray"], model, virtue, "neutral")
    elif arm == "hokusai":
        rows = load_arm_records(paths["hokusai"], model, virtue, "neutral")
    elif arm == "annunciation":
        rows = load_arm_records(paths["annunciation"], model, virtue, "sacred")
    else:
        raise ValueError(arm)
    return [bool(r["correct"]) for r in rows]


def plot(paths: dict, out_path: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(13, 9), sharey=True)
    models = [("claude-opus-4-6", "Claude Opus 4.6"), ("gpt-5.4", "GPT-5.4")]
    rng = np.random.default_rng(42)

    for ax, (model, display) in zip(axes, models):
        n_v = len(VIRTUE_ORDER)
        x_v = np.arange(n_v)
        bar_w = 0.20

        for arm_idx, (arm, label, color) in enumerate(ARM_INFO):
            accs, lows, highs = [], [], []
            for v in VIRTUE_ORDER:
                cell = get_cell(model, v, arm, paths=paths)
                acc, lo, hi = bootstrap_ci(cell, rng=rng) if cell else (float("nan"),)*3
                accs.append(acc * 100 if not np.isnan(acc) else 0)
                lows.append((acc - lo) * 100 if not np.isnan(lo) else 0)
                highs.append((hi - acc) * 100 if not np.isnan(hi) else 0)

            offset = (arm_idx - 1.5) * bar_w
            ax.bar(x_v + offset, accs, bar_w, label=label, color=color,
                   edgecolor="black", linewidth=0.4,
                   yerr=[lows, highs], capsize=3,
                   error_kw={"elinewidth": 1, "ecolor": "black"})
            for i, acc in enumerate(accs):
                if acc > 0:
                    ax.text(x_v[i] + offset, acc + 0.7, f"{acc:.0f}",
                            ha="center", va="bottom", fontsize=8)

        ax.set_xticks(x_v)
        ax.set_xticklabels([v.capitalize() for v in VIRTUE_ORDER], fontsize=11)
        ax.set_ylim(50, 102)
        ax.set_ylabel("Accuracy (%)", fontsize=11)
        ax.set_title(display, fontsize=12, fontweight="bold", loc="left")
        ax.grid(axis="y", linestyle=":", alpha=0.4)
        ax.set_axisbelow(True)
        if ax is axes[0]:
            ax.legend(loc="lower right", framealpha=0.95, fontsize=9, ncol=2)

    fig.suptitle(
        "Four-arm comparison: bare image presence does not produce the effect\n"
        "(VirtueBench-2 ratio variant, n=750 per cell)",
        fontsize=13, fontweight="bold",
    )
    fig.text(0.5, -0.005,
             "Blank-gray = 1568×1024 mid-gray rectangle (content-free control). "
             "Error bars: 95% bootstrap CIs.",
             ha="center", fontsize=9, color="#444444")
    plt.tight_layout(rect=[0, 0.01, 1, 0.96])
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_path}", file=sys.stderr)


def reference_rates_table(paths: dict) -> str:
    """How often does each model verbally engage the image?"""
    HOK = re.compile(r"\b(hokusai|wave|kanagawa|fuji|mount fuji|tsunami|ukiyo|japan|woodblock|katsushika)\b", re.I)
    ANN = re.compile(r"\b(annunciation|fra angelico|gabriel|virgin mary|the virgin|mother of god|theotokos)\b", re.I)
    GRAY = re.compile(r"\b(gray|grey|blank|uniform|featureless|empty|plain|absence of|"
                      r"no (?:visible|distinct|content|image)|nothing visible)\b", re.I)

    out = ["## Verbal reference rates (sacred/neutral arms)", ""]
    out.append("| Model | Virtue | Blank-gray refs | Hokusai refs | Annunciation refs |")
    out.append("|---|---|---|---|---|")
    for model, display in [("claude-opus-4-6", "Opus 4.6"), ("gpt-5.4", "GPT-5.4")]:
        for v in VIRTUE_ORDER:
            blank = load_arm_records(paths["blank_gray"], model, v, "neutral")
            hok = load_arm_records(paths["hokusai"], model, v, "neutral")
            ann = load_arm_records(paths["annunciation"], model, v, "sacred")
            blank_hits = sum(1 for r in blank if GRAY.search(r.get("response", "")))
            hok_hits = sum(1 for r in hok if HOK.search(r.get("response", "")))
            ann_hits = sum(1 for r in ann if ANN.search(r.get("response", "")))
            out.append(f"| {display} | {v} "
                       f"| {blank_hits}/{len(blank)} ({blank_hits/max(len(blank),1)*100:.0f}%) "
                       f"| {hok_hits}/{len(hok)} ({hok_hits/max(len(hok),1)*100:.0f}%) "
                       f"| {ann_hits}/{len(ann)} ({ann_hits/max(len(ann),1)*100:.0f}%) |")
    return "\n".join(out) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--baseline-dir", type=Path, required=True)
    p.add_argument("--blank-gray-dir", type=Path, required=True)
    p.add_argument("--hokusai-dir", type=Path, required=True)
    p.add_argument("--annunciation-dir", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, default=PROJECT_ROOT / "results" / "four_arm")
    args = p.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "baseline":     args.baseline_dir,
        "blank_gray":   args.blank_gray_dir,
        "hokusai":      args.hokusai_dir,
        "annunciation": args.annunciation_dir,
    }

    plot(paths, args.out_dir / "four_arm_comparison.png")
    md = reference_rates_table(paths)
    md_path = args.out_dir / "reference_rates.md"
    md_path.write_text(md, encoding="utf-8")
    print(md)
    print(f"Wrote {md_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
