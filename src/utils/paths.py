"""Project path helpers."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
MEMORY_DIR = PROJECT_ROOT / "memory"
CONTENT_DIR = PROJECT_ROOT / "content"
LABS_DIR = PROJECT_ROOT / "labs"


def ensure_project_directories() -> None:
    """Create runtime directories required by the Market System."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    (MEMORY_DIR / "daily").mkdir(parents=True, exist_ok=True)
    (MEMORY_DIR / "tokens").mkdir(parents=True, exist_ok=True)
    (MEMORY_DIR / "narratives").mkdir(parents=True, exist_ok=True)
    (MEMORY_DIR / "signals").mkdir(parents=True, exist_ok=True)
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    (CONTENT_DIR / "notes").mkdir(parents=True, exist_ok=True)
    (CONTENT_DIR / "threads").mkdir(parents=True, exist_ok=True)
    (CONTENT_DIR / "x").mkdir(parents=True, exist_ok=True)
    LABS_DIR.mkdir(parents=True, exist_ok=True)
