# Iconographic Priming on VirtueBench-2

Release accompanying:

> **Hwang, T.** *And Their Eyes Were Opened: Christian Multimodal Reasoning in Opus 4.6.* ICMI Working Paper No. 19, April 2026.

This repository contains the minimum code, data, and result records needed to reproduce the four-arm experiment reported in the paper.

## The three image conditions

| Annunciation (sacred) | Hokusai (figural reference) | Blank gray (content-free control) |
|:---:|:---:|:---:|
| ![Fra Angelico, *Annunciation* (San Marco), c. 1440](data/images/sacred/sacred_07_fra_angelico_annunciation.jpg) | ![Hokusai, *The Great Wave off Kanagawa*, c. 1831](data/images/neutral/neutral_03_hokusai_great_wave.jpg) | ![1568×1024 mid-gray rectangle](data/images/neutral/neutral_11_blank_gray.jpg) |
| Fra Angelico, *Annunciation* (San Marco), c. 1440 | Hokusai, *The Great Wave off Kanagawa*, c. 1831 | 1568×1024 mid-gray rectangle |

Plus a fourth text-only baseline condition (no image attached). Each cell is 150 base scenarios × 5 runs = 750 trials; the full study is 24,000 calls across two models, four virtues, four arms.

The paper is in [PAPER.md](PAPER.md). A self-critique of the paper is in [PAPER_CRITIQUES.md](PAPER_CRITIQUES.md).

## Repo layout

```
iconographic-priming/
├── PAPER.md                         The paper itself
├── PAPER_CRITIQUES.md               Self-critique
├── README.md                        This file
├── pyproject.toml                   Python package metadata
│
├── data/images/                     Image bundle (3 images for the paper)
│   ├── manifest.json                With SHA-256 hashes for reproducibility
│   ├── sacred/sacred_07_fra_angelico_annunciation.jpg
│   └── neutral/
│       ├── neutral_03_hokusai_great_wave.jpg
│       └── neutral_11_blank_gray.jpg
│
├── src/iconographic_priming/        Core library
│   ├── images.py                    Manifest loader, image encoding, selection
│   ├── cache.py                     Per-call cache (sharded JSON)
│   ├── clients/                     Async API wrappers
│   │   ├── anthropic_client.py
│   │   └── openai_client.py
│   ├── runner.py                    Per-call orchestration: cache → API → score
│   ├── run_experiment.py            CLI to run a sweep across (model × virtue × arm)
│   ├── analyze.py                   Bootstrap CI, permutation test, Bonferroni
│   └── four_arm.py                  Paper's four-arm comparison chart + ref-rates
│
├── scripts/                         Top-level reproduction scripts
│   ├── 00_setup.sh                  Fetch images + generate blank-gray control
│   ├── 01_run_paper.sh              Run all four arms on both models
│   ├── 02_analyze_paper.sh          Generate paper's chart and stats
│   ├── fetch_images.py              Fetches Annunciation + Hokusai from Wikimedia
│   └── make_blank_gray.py           Generates the gray control programmatically
│
└── results/
    ├── cache/                       Per-call cache (empty in release; rebuilds during run)
    ├── runs/                        Paper's raw result records (one dir per arm × timestamp)
    │   ├── 20260428_192221Z/        Baseline records (4.6 + 5.4 × 4 virtues = 8 jsonl)
    │   ├── 20260429_011040Z/        Blank-gray records (8 jsonl)
    │   ├── 20260428_205406Z/        Hokusai records (8 jsonl)
    │   └── 20260428_194406Z/        Annunciation records (8 jsonl)
    └── four_arm/
        ├── four_arm_comparison.png  Paper's headline chart
        └── reference_rates.md       Verbal-reference rates per (model, virtue, arm)
```

## Reproducing the paper from scratch

Requirements: Python ≥ 3.10. API keys for both providers. ~$175 in inference budget. ~45 minutes wall-clock at concurrency 20.

```sh
# 1. Install dependencies (one-time)
pip install -e .

# 2. Fetch images and generate the blank-gray control
bash scripts/00_setup.sh

# 3. Set API keys (or have them in ../sacramental-alignment/.env per the project convention)
export ANTHROPIC_API_KEY=...
export OPENAI_API_KEY=...

# 4. Run the full four-arm experiment
bash scripts/01_run_paper.sh

# 5. Generate the paper chart and stats
bash scripts/02_analyze_paper.sh <baseline-run-dir> <blank-gray-run-dir> <hokusai-run-dir> <annunciation-run-dir>
```

Each run of `01_run_paper.sh` produces four new timestamped directories under `results/runs/`. Pass them to `02_analyze_paper.sh` in arm order.

## Reproducing the analysis only (no API calls)

The release ships with the JSONL records from the original paper run, so the analysis can be regenerated without re-calling the APIs:

```sh
bash scripts/02_analyze_paper.sh
# (defaults to the included run dirs)
```

## VirtueBench-2 dependency

The runner imports `virtue_bench` from a clone of the upstream benchmark. By default, `01_run_paper.sh` clones `https://github.com/christian-machine-intelligence/virtue-bench-2` to `/tmp/virtue-bench-2`. Override with `VBE_PATH`.

## Cache

Cache keys include `(model, scenario_text, image_id, virtue, base_id, run_index, ab_seed, system_prompt, temperature)`. Reruns hit cache and incur zero API cost. The release ships with an empty cache; running the experiment populates it.

## License

Code: MIT. Image bundle: see [data/images/manifest.json](data/images/manifest.json) for per-image attribution and license. The Annunciation and Great Wave are public domain (PD-old-100); the blank-gray control is CC0.

## Citation

```bibtex
@misc{hwang2026eyes,
  title={And Their Eyes Were Opened: Evidence of Christian Multimodal Reasoning in Opus 4.6},
  author={Hwang, Tim},
  year={2026},
  institution={Institute for Christian Machine Intelligence}
}
```

## Companion archive

Exploratory work — including the 21-image rotating bundle, the cross-generation comparison against Opus 4.7 / GPT-5.5, the per-image breakdowns, and earlier smoke-test results — is preserved in `../iconographic-priming-archive/`. None of it is needed to reproduce the paper, but it documents the path that led to the four-arm protocol settled on in the final study.
