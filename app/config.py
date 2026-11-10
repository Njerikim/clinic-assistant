"""Runtime settings, read from the environment at call time (easy to override in tests)."""
import json
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

DEMO_KEYS = {
    "demo-key-clinic-a": "clinic_a",
    "demo-key-clinic-b": "clinic_b",
}


def data_dir() -> Path:
    """Rollback = point INDEX_VERSION at the previous folder (data/v1, data/v2, ...)."""
    return BASE / "data" / os.getenv("INDEX_VERSION", "v1")


def min_score() -> float:
    """Below this similarity we refuse to answer instead of guessing."""
    return float(os.getenv("MIN_SCORE", "0.20"))


def tenant_keys() -> dict[str, str]:
    """API key -> tenant id. Set TENANT_KEYS='{"key":"clinic_a"}' outside demos."""
    raw = os.getenv("TENANT_KEYS")
    return json.loads(raw) if raw else dict(DEMO_KEYS)
