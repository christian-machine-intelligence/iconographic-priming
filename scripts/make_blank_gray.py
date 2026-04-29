#!/usr/bin/env python3
"""Generate the content-free control image (1568x1024 mid-gray) and append to manifest."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "images" / "manifest.json"
OUT = ROOT / "data" / "images" / "neutral" / "neutral_11_blank_gray.jpg"


def main() -> int:
    W, H = 1568, 1024
    arr = np.full((H, W, 3), 128, dtype=np.uint8)
    # Imperceptible noise prevents any flat-image rejection at API boundaries.
    noise = np.random.RandomState(42).randint(-2, 3, arr.shape, dtype=np.int16)
    arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr, "RGB").save(OUT, quality=92, optimize=True)
    data = OUT.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    print(f"Wrote {OUT.relative_to(ROOT)}: {W}x{H}, {len(data)//1024} KB, sha256={sha[:16]}…")

    # Append to manifest if not present.
    m = json.loads(MANIFEST.read_text())
    existing = next((e for e in m["images"] if e["id"] == "neutral_11_blank_gray"), None)
    entry = {
        "id": "neutral_11_blank_gray",
        "category": "neutral",
        "title": "Blank Gray (control)",
        "artist": "(programmatically generated)",
        "year": 2026,
        "wp_slug": None,
        "license": "CC0 — generated for this study",
        "rationale": "Content-free image control: 1568x1024 mid-gray with imperceptible noise.",
        "source_url": None,
        "wikipedia_url": None,
        "file": str(OUT.relative_to(ROOT)),
        "width": W,
        "height": H,
        "bytes": len(data),
        "sha256": sha,
    }
    if existing:
        existing.update(entry)
    else:
        m["images"].append(entry)
    MANIFEST.write_text(json.dumps(m, indent=2, ensure_ascii=False))
    print(f"Manifest updated: {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
