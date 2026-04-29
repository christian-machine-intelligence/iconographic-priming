<p align="center">
  <img src="data/images/sacred/sacred_07_fra_angelico_annunciation.jpg" alt="Fra Angelico, Annunciation (San Marco, c. 1440). Wikimedia Commons (PD-old-100)." width="100%">
  <br>
  <em>Fra Angelico, Annunciation (San Marco, c. 1440). Wikimedia Commons (PD-old-100).</em>
</p>

# And Their Eyes Were Opened

**Christian Multimodal Reasoning in Opus 4.6**

> *"And their eyes were opened, and they knew him; and he vanished out of their sight."* — Luke 24:31 (KJV)

This repository contains the code, image bundle, and per-call result records (24,000 trials) for ICMI Working Paper No. 19, which tests whether sacred Christian imagery — attached as an image input to a multimodal language model — produces an effect on moral reasoning analogous to the psalm-injection finding of [ICMI-011](https://icmi-proceedings.com/ICMI-011-virtuebench-2.html) §5.2.

**Paper:** [ICMI-019 on icmi-proceedings.com](https://icmi-proceedings.com/ICMI-019-and-their-eyes-were-opened.html)

## Key Finding

On Claude Opus 4.6, the *Annunciation* produces a Bonferroni-significant **+9.3 pp accuracy gain on temperance scenarios** of VirtueBench-2 (Cohen's *h* = 0.32), with significant gains on prudence (+1.6) and courage (+3.2). A content-free image control produces no detectable effect; Hokusai's *The Great Wave off Kanagawa* produces an intermediate effect. GPT-5.4 shows no significant gain on any virtue under any image condition.

Reasoning traces show Opus 4.6 spontaneously narrativizing the *Annunciation* into its moral reasoning — naming the painter, the Latin inscription on the fresco, and the Dominican context of San Marco — while GPT-5.4 does not engage the image. We argue, as one interpretation among several consistent ones, that a sacred image functions as a compact, thickly encoded cue into the Christian moral content the model already carries from pretraining. See the paper for the four falsification predictions in §6.2.

## The four image conditions

| Annunciation (sacred) | Hokusai (figural reference) | Blank gray (content-free control) |
|:---:|:---:|:---:|
| ![Fra Angelico, *Annunciation*](data/images/sacred/sacred_07_fra_angelico_annunciation.jpg) | ![Hokusai, *The Great Wave*](data/images/neutral/neutral_03_hokusai_great_wave.jpg) | ![1568×1024 mid-gray rectangle](data/images/neutral/neutral_11_blank_gray.jpg) |
| Fra Angelico, *Annunciation* (San Marco), c. 1440 | Hokusai, *The Great Wave off Kanagawa*, c. 1831 | 1568×1024 mid-gray rectangle |

Plus a fourth text-only baseline (no image attached). Each cell is 150 base scenarios × 5 runs = 750 calls; the full study is 24,000 calls across two models, four virtues, four arms.

## Repo layout

```
iconographic-priming/
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
│   ├── clients/                     Async API wrappers (anthropic, openai)
│   ├── runner.py                    Per-call orchestration: cache → API → score
│   ├── run_experiment.py            CLI to run a sweep across (model × virtue × arm)
│   ├── analyze.py                   Bootstrap CI, permutation test, Bonferroni
│   └── four_arm.py                  Four-arm comparison chart + reference rates
│
├── scripts/                         Top-level reproduction scripts
│   ├── 00_setup.sh                  Fetch images + generate blank-gray control
│   ├── 01_run_paper.sh              Run all four arms on both models
│   ├── 02_analyze_paper.sh          Generate the chart and stats
│   ├── fetch_images.py              Fetches Annunciation + Hokusai from Wikimedia
│   └── make_blank_gray.py           Generates the gray control programmatically
│
└── results/
    ├── cache/                       Per-call cache (empty in release; rebuilds during run)
    ├── runs/                        Raw result records (one dir per arm × timestamp)
    │   ├── 20260428_192221Z/        Baseline records (4.6 + 5.4 × 4 virtues = 8 jsonl)
    │   ├── 20260429_011040Z/        Blank-gray records (8 jsonl)
    │   ├── 20260428_205406Z/        Hokusai records (8 jsonl)
    │   └── 20260428_194406Z/        Annunciation records (8 jsonl)
    └── four_arm/
        ├── four_arm_comparison.png  Headline chart
        └── reference_rates.md       Verbal-reference rates per (model, virtue, arm)
```

## Reproducing the experiment from scratch

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

# 5. Generate the chart and stats
bash scripts/02_analyze_paper.sh <baseline-run-dir> <blank-gray-run-dir> <hokusai-run-dir> <annunciation-run-dir>
```

## Reproducing the analysis only (no API calls)

The release ships with the JSONL records from the original run, so the analysis can be regenerated without re-calling the APIs:

```sh
bash scripts/02_analyze_paper.sh
# (defaults to the included run dirs)
```

## VirtueBench-2 dependency

The runner imports `virtue_bench` from a clone of the upstream benchmark. By default, `01_run_paper.sh` clones [christian-machine-intelligence/virtue-bench-2](https://github.com/christian-machine-intelligence/virtue-bench-2) to `/tmp/virtue-bench-2`. Override with `VBE_PATH`.

## Cache

Cache keys include `(model, scenario_text, image_id, virtue, base_id, run_index, ab_seed, system_prompt, temperature)`. Reruns hit cache and incur zero API cost. The release ships with an empty cache; running the experiment populates it.

## License

Code: MIT. Image bundle: see [data/images/manifest.json](data/images/manifest.json) for per-image attribution and license. The Annunciation and Great Wave are public domain (PD-old-100); the blank-gray control is CC0.

## Citation

```bibtex
@misc{hwang2026eyes,
  title  = {And Their Eyes Were Opened: Christian Multimodal Reasoning in Opus 4.6},
  author = {Hwang, Tim},
  year   = {2026},
  number = {ICMI Working Paper No. 19},
  url    = {https://icmi-proceedings.com/ICMI-019-and-their-eyes-were-opened.html}
}
```
