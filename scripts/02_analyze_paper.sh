#!/usr/bin/env bash
# 02_analyze_paper.sh — produce the paper's four-arm comparison chart and stats.
#
# Usage:
#   bash scripts/02_analyze_paper.sh \
#       <baseline-run-dir> <blank-gray-run-dir> <hokusai-run-dir> <annunciation-run-dir>
#
# With no arguments, defaults to the run dirs accompanying the paper.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"

# Defaults: the run dirs included with the paper release.
BASELINE_DIR="${1:-results/runs/20260428_192221Z}"
BLANK_DIR="${2:-results/runs/20260429_011040Z}"
HOKUSAI_DIR="${3:-results/runs/20260428_205406Z}"
ANNUNC_DIR="${4:-results/runs/20260428_194406Z}"

echo "Sources:"
echo "  Baseline:     $BASELINE_DIR"
echo "  Blank-gray:   $BLANK_DIR"
echo "  Hokusai:      $HOKUSAI_DIR"
echo "  Annunciation: $ANNUNC_DIR"
echo ""

python3 -m iconographic_priming.four_arm \
    --baseline-dir "$BASELINE_DIR" \
    --blank-gray-dir "$BLANK_DIR" \
    --hokusai-dir "$HOKUSAI_DIR" \
    --annunciation-dir "$ANNUNC_DIR"

echo ""
echo "Outputs in: results/four_arm/"
ls -la results/four_arm/ 2>/dev/null
