"""Sharded JSON-per-call cache so retries and reruns don't re-bill API calls."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class CallKey:
    model: str
    scenario_text: str
    image_id: Optional[str]   # None for baseline arm
    virtue: str
    variant: str
    base_id: str
    run_index: int
    ab_seed: int
    system_prompt: str
    temperature: float

    def hash(self) -> str:
        sys_h = hashlib.sha256(self.system_prompt.encode()).hexdigest()[:8]
        payload = json.dumps({
            "m": self.model,
            "s": hashlib.sha256(self.scenario_text.encode()).hexdigest()[:16],
            "img": self.image_id or "_none",
            "v": self.virtue,
            "var": self.variant,
            "bid": self.base_id,
            "ri": self.run_index,
            "abs": self.ab_seed,
            "sys": sys_h,
            "t": round(self.temperature, 3),
        }, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:24]


def cache_path(cache_dir: Path, key_hash: str) -> Path:
    return cache_dir / key_hash[:2] / f"{key_hash}.json"


def cache_get(cache_dir: Path, key: CallKey) -> Optional[dict]:
    p = cache_path(cache_dir, key.hash())
    if not p.exists():
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def cache_put(cache_dir: Path, key: CallKey, value: dict) -> None:
    p = cache_path(cache_dir, key.hash())
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False)
    tmp.replace(p)
