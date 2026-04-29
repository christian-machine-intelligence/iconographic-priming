#!/usr/bin/env bash
# 00_setup.sh — fetch the two real images from Wikimedia Commons and generate
# the blank-gray control. Idempotent.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"

python3 scripts/fetch_images.py
python3 scripts/make_blank_gray.py

echo ""
echo "Image bundle ready:"
ls -la data/images/sacred/ data/images/neutral/ 2>&1 | grep -v '^d' | grep -v 'total'
