#!/usr/bin/env bash
# 01_run_paper.sh — reproduce the four-arm paper protocol on Opus 4.6 and GPT-5.4.
#
# Runs:
#   - baseline (no image)
#   - blank-gray neutral arm
#   - Hokusai-pinned neutral arm
#   - Annunciation-pinned sacred arm
#
# All four arms × 4 cardinal virtues × 5 runs × 2 models = 24,000 calls.
# At concurrency 20 against current API tier limits, ~30-45 min wall-clock,
# ~$175 total inference (assuming no cache).
#
# Cache is keyed on (model, scenario_text, image_id, virtue, base_id, run_index,
# ab_seed, system_prompt, temperature) — reruns hit cache and incur zero API cost.
set -euo pipefail
cd "$(dirname "$0")/.."

# Load API keys. By convention this project sources them from a sibling project.
ENV_FILE="${ENV_FILE:-../sacramental-alignment/.env}"
if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
elif [[ -z "${ANTHROPIC_API_KEY:-}" || -z "${OPENAI_API_KEY:-}" ]]; then
    echo "ERROR: Set ANTHROPIC_API_KEY and OPENAI_API_KEY (or point ENV_FILE at a .env)" >&2
    exit 1
fi

# Some user environments set ANTHROPIC_BASE_URL to a Claude Code internal endpoint
# that does not serve all models. Unset for direct API use.
unset ANTHROPIC_BASE_URL || true

export VBE_PATH="${VBE_PATH:-/tmp/virtue-bench-2}"
if [[ ! -d "$VBE_PATH" ]]; then
    echo "Cloning VirtueBench-2 to $VBE_PATH ..."
    git clone --depth=1 https://github.com/christian-machine-intelligence/virtue-bench-2.git "$VBE_PATH"
fi
export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"

# Each arm writes to its own timestamped directory. We keep the four runs separate
# so it's easy to inspect a single arm's records, and so analysis can pull from a
# named directory per arm.
COMMON_ARGS=(
    --models claude-opus-4-6 gpt-5.4
    --virtues prudence justice courage temperance
    --variants ratio
    --runs 5
    --concurrency 20
)

echo "==> Arm 1/4: baseline (no image)"
python3 -m iconographic_priming.run_experiment "${COMMON_ARGS[@]}" --arms baseline

echo "==> Arm 2/4: blank-gray (content-free image)"
python3 -m iconographic_priming.run_experiment "${COMMON_ARGS[@]}" \
    --arms neutral --neutral-image neutral_11_blank_gray

echo "==> Arm 3/4: Hokusai (non-religious figural reference)"
python3 -m iconographic_priming.run_experiment "${COMMON_ARGS[@]}" \
    --arms neutral --neutral-image neutral_03_hokusai_great_wave

echo "==> Arm 4/4: Annunciation (Fra Angelico, sacred treatment)"
python3 -m iconographic_priming.run_experiment "${COMMON_ARGS[@]}" \
    --arms sacred --sacred-image sacred_07_fra_angelico_annunciation

echo ""
echo "All four arms complete. Run dirs (most recent four):"
ls -1t results/runs | head -4
