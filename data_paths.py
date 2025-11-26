"""Central helpers for choosing a writable data directory.

The project historically stored runtime JSON under ``./data`` inside the repo,
which gets wiped whenever Render clones the repository for a fresh deploy.
This module picks a more durable location when available (persistent disks,
explicit env overrides, etc.) while falling back to the legacy path locally.
"""
from __future__ import annotations

import os
import shutil
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEED_DATA_DIR = ROOT / "data"

_ENV_KEYS = (
    "VULNMAP_DATA_DIR",
    "PERSISTENT_DATA_DIR",
    "DATA_DIR_OVERRIDE",
    "DATA_DIR",
)


def _candidate_dirs() -> list[Path]:
    candidates: list[Path] = []
    seen: set[Path] = set()

    for key in _ENV_KEYS:
        val = os.getenv(key)
        if val:
            path = Path(val).expanduser()
            if path not in seen:
                candidates.append(path)
                seen.add(path)

    render_disk_root = os.getenv("RENDER_DISK_ROOT")
    if render_disk_root:
        path = Path(render_disk_root).expanduser()
        candidate = path / "vulnmap-data"
        if candidate not in seen:
            candidates.append(candidate)
            seen.add(candidate)

    default_render_disk = Path("/var/lib/render/data")
    if os.getenv("RENDER") and default_render_disk.exists():
        candidate = default_render_disk / "vulnmap-data"
        if candidate not in seen:
            candidates.append(candidate)
            seen.add(candidate)

    local_runtime = ROOT / "runtime_data"
    if local_runtime not in seen:
        candidates.append(local_runtime)
        seen.add(local_runtime)

    return candidates


def _bootstrap_seed_data(target: Path) -> None:
    if not SEED_DATA_DIR.exists():
        return
    try:
        if SEED_DATA_DIR.samefile(target):
            return
    except FileNotFoundError:
        pass
    for src in SEED_DATA_DIR.rglob("*"):
        rel = src.relative_to(SEED_DATA_DIR)
        dest = target / rel
        if src.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
        else:
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)


@lru_cache(maxsize=1)
def get_data_dir() -> Path:
    for candidate in _candidate_dirs():
        try:
            candidate.mkdir(parents=True, exist_ok=True)
        except Exception:
            continue
        if candidate.exists():
            _bootstrap_seed_data(candidate)
            return candidate
    SEED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return SEED_DATA_DIR
