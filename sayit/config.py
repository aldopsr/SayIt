"""Pemuat konfigurasi terpusat."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "settings.yaml"


@lru_cache(maxsize=4)
def load_config(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def project_path(relative: str | Path) -> Path:
    """Ubah path relatif di konfigurasi menjadi path absolut di dalam proyek."""
    p = Path(relative)
    return p if p.is_absolute() else PROJECT_ROOT / p
