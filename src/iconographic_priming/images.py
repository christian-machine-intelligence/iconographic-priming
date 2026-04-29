"""Image bundle loading, encoding, and deterministic per-scenario selection."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
MANIFEST_PATH = DATA_DIR / "images" / "manifest.json"


@dataclass(frozen=True)
class ImageEntry:
    id: str
    category: str  # "sacred" or "neutral"
    title: str
    artist: str
    year: int
    file: Path
    sha256: str
    width: int
    height: int


def load_manifest(manifest_path: Path = MANIFEST_PATH) -> list[ImageEntry]:
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    entries = []
    for raw in manifest["images"]:
        if "fetch_error" in raw or "sha256" not in raw:
            raise ValueError(f"Manifest entry {raw['id']} is unfetched or errored. Run scripts/fetch_images.py first.")
        entries.append(ImageEntry(
            id=raw["id"],
            category=raw["category"],
            title=raw["title"],
            artist=raw["artist"],
            year=raw["year"],
            file=PROJECT_ROOT / raw["file"],
            sha256=raw["sha256"],
            width=raw["width"],
            height=raw["height"],
        ))
    return entries


def by_category(entries: list[ImageEntry], category: str) -> list[ImageEntry]:
    return sorted([e for e in entries if e.category == category], key=lambda e: e.id)


@lru_cache(maxsize=None)
def encode_image(file_path: str) -> str:
    """Read JPEG and return base64 string. Cached because the bundle is small and reused thousands of times."""
    return base64.b64encode(Path(file_path).read_bytes()).decode("ascii")


def select_image(entries: list[ImageEntry], *, base_id: str, run_index: int) -> ImageEntry:
    """Deterministic image selection: rotate through the bundle by (base_id, run_index).

    Same (base_id, run_index) pair always picks the same image, so paired baseline /
    neutral / sacred rows align — both arms see the *same position in the bundle* for
    a given scenario+run, which keeps statistical pairing meaningful.
    """
    if not entries:
        raise ValueError("Empty image bundle")
    key = f"{base_id}|{run_index}".encode()
    h = int.from_bytes(hashlib.sha256(key).digest()[:8], "big")
    return entries[h % len(entries)]
