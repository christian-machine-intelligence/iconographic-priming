#!/usr/bin/env python3
"""Fetch and preprocess images from Wikipedia for the priming bundle.

For each entry in manifest.json, hits the Wikipedia REST summary endpoint to
get the article's lead image, downloads the original, resizes to the configured
long-edge limit, strips EXIF, and writes JPEG to data/images/<category>/<id>.jpg.
Updates manifest.json in place with the resolved source_url and image hash.
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import time
from pathlib import Path

import requests
from PIL import Image

REQUEST_DELAY_SEC = 1.5
RETRY_ON_429_SEC = 30
MAX_429_RETRIES = 3

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "images" / "manifest.json"
WP_REST = "https://en.wikipedia.org/api/rest_v1/page/summary/{slug}"
USER_AGENT = "iconographic-priming-research/0.1 (research; tim@icmi-proceedings.com)"

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})


def _get(url: str, *, timeout: int) -> requests.Response:
    """GET with 429-retry: back off and retry up to MAX_429_RETRIES times."""
    for attempt in range(MAX_429_RETRIES + 1):
        r = _session.get(url, timeout=timeout)
        if r.status_code != 429 or attempt == MAX_429_RETRIES:
            r.raise_for_status()
            return r
        wait = RETRY_ON_429_SEC * (attempt + 1)
        print(f"  [429] backing off {wait}s ...", flush=True)
        time.sleep(wait)
    raise RuntimeError("unreachable")


def fetch_json(url: str) -> dict:
    return _get(url, timeout=30).json()


def fetch_bytes(url: str) -> bytes:
    return _get(url, timeout=60).content


def resolve_image_url(slug: str) -> tuple[str, str]:
    """Return (image_url, attribution_url) for a Wikipedia article slug."""
    summary = fetch_json(WP_REST.format(slug=slug))
    img = summary.get("originalimage") or summary.get("thumbnail")
    if not img or "source" not in img:
        raise RuntimeError(f"No image found in summary for {slug}")
    page_url = summary.get("content_urls", {}).get("desktop", {}).get("page", "")
    return img["source"], page_url


def preprocess(raw: bytes, max_long_edge: int, quality: int) -> tuple[bytes, tuple[int, int]]:
    img = Image.open(io.BytesIO(raw))
    img = img.convert("RGB")
    w, h = img.size
    long_edge = max(w, h)
    if long_edge > max_long_edge:
        scale = max_long_edge / long_edge
        new_size = (round(w * scale), round(h * scale))
        img = img.resize(new_size, Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=quality, optimize=True)
    return out.getvalue(), img.size


def main() -> int:
    with open(MANIFEST, encoding="utf-8") as f:
        manifest = json.load(f)

    pp = manifest["preprocessing"]
    images = manifest["images"]
    out_dir = ROOT / "data" / "images"

    updated = []
    for entry in images:
        cat = entry["category"]
        eid = entry["id"]
        slug = entry["wp_slug"]
        out_path = out_dir / cat / f"{eid}.jpg"

        if out_path.exists() and entry.get("sha256"):
            print(f"[skip] {eid} (already fetched)")
            updated.append(entry)
            continue

        # Strip any prior failure state before re-attempt
        entry = {k: v for k, v in entry.items() if k != "fetch_error"}

        try:
            url, page_url = resolve_image_url(slug)
            print(f"[fetch] {eid} <- {url[:80]}")
            raw = fetch_bytes(url)
            jpeg, (W, H) = preprocess(raw, pp["max_long_edge_px"], pp["quality"])
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(jpeg)
            entry.update({
                "source_url": url,
                "wikipedia_url": page_url,
                "file": str(out_path.relative_to(ROOT)),
                "width": W,
                "height": H,
                "bytes": len(jpeg),
                "sha256": hashlib.sha256(jpeg).hexdigest(),
            })
            print(f"  -> {out_path.name} {W}x{H} {len(jpeg)//1024}KB")
        except Exception as e:
            print(f"[FAIL] {eid}: {type(e).__name__}: {e}", file=sys.stderr)
            entry["fetch_error"] = str(e)
        updated.append(entry)
        time.sleep(REQUEST_DELAY_SEC)

    manifest["images"] = updated
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    n_ok = sum(1 for e in updated if "sha256" in e)
    print(f"\nDone: {n_ok}/{len(updated)} images successfully fetched.")
    return 0 if n_ok == len(updated) else 1


if __name__ == "__main__":
    sys.exit(main())
