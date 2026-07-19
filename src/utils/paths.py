"""Project path helpers."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ENV = "ALPHA_HUNTER_WORKSPACE"


def resolve_workspace_root(value: str | Path | None = None) -> Path:
    """Resolve one process-wide mutable workspace without changing defaults."""
    configured = value if value is not None else os.getenv(WORKSPACE_ENV)
    if configured is None or not str(configured).strip():
        return PROJECT_ROOT
    return Path(str(configured)).expanduser().resolve()


WORKSPACE_ROOT = resolve_workspace_root()
DATA_DIR = WORKSPACE_ROOT / "data"
LOGS_DIR = WORKSPACE_ROOT / "logs"
MEMORY_DIR = WORKSPACE_ROOT / "memory"
CONTENT_DIR = WORKSPACE_ROOT / "content"
LABS_DIR = WORKSPACE_ROOT / "labs"
REPORTS_DIR = WORKSPACE_ROOT / "reports"


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
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
