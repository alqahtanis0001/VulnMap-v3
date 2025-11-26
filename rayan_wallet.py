"""Helpers to persist and override Rayan's wallet across restarts."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict

RAYAN_USERNAME = "rayan"
EPSILON = 0.01


def is_rayan(username: str) -> bool:
    return (username or "").strip().lower() == RAYAN_USERNAME


def get_rayan_wallet_file(data_dir: Path) -> Path:
    return Path(data_dir) / "wallet_rayan.json"


def _read_json(path: Path, default):
    try:
        with Path(path).open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json_atomic(path: Path, data) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _sanitize_wallet(wallet: Dict[str, float]) -> Dict[str, float]:
    return {
        "available_balance": round(float(wallet.get("available_balance", 0.0)), 2),
        "total_earned": round(float(wallet.get("total_earned", 0.0)), 2),
    }


def persist_rayan_wallet(data_dir: Path, wallet: Dict[str, float]) -> Dict[str, float]:
    sanitized = _sanitize_wallet(wallet)
    fp = get_rayan_wallet_file(data_dir)
    existing = _read_json(fp, {})
    if existing != sanitized:
        _write_json_atomic(fp, sanitized)
    return sanitized


def load_rayan_wallet(data_dir: Path, computed_wallet: Dict[str, float]) -> Dict[str, float]:
    """
    Persist the latest computed wallet so that new earnings/withdrawals are
    reflected immediately while still keeping a durable snapshot on disk.
    """
    computed = _sanitize_wallet(computed_wallet)
    fp = get_rayan_wallet_file(data_dir)
    persisted = _read_json(fp, None)
    if isinstance(persisted, dict):
        persisted = _sanitize_wallet(persisted)
    else:
        persisted = None

    if not persisted:
        return persist_rayan_wallet(data_dir, computed)

    # If totals suddenly shrink we assume data loss (e.g., redeploy) and keep the persisted snapshot.
    drop = persisted["total_earned"] - computed["total_earned"]
    if drop > EPSILON:
        return persist_rayan_wallet(data_dir, persisted)

    merged = {
        "total_earned": max(persisted["total_earned"], computed["total_earned"]),
        "available_balance": max(0.0, min(computed["available_balance"], computed["total_earned"])),
    }
    return persist_rayan_wallet(data_dir, merged)


def reset_rayan_wallet(data_dir: Path, total_earned: float = 0.0) -> Dict[str, float]:
    """Force Rayan's wallet to a known baseline (e.g., after admin reset)."""
    return persist_rayan_wallet(
        data_dir,
        {"available_balance": 0.0, "total_earned": round(float(total_earned or 0.0), 2)},
    )
