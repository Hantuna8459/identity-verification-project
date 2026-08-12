from __future__ import annotations

from pathlib import Path

FIELDCHECK_DIR = Path(__file__).resolve().parent
BACKEND_DIR = FIELDCHECK_DIR.parent
REPO_ROOT = BACKEND_DIR.parent

DEFAULT_MODEL_DIR = REPO_ROOT / "models"
DEFAULT_LOCAL_RUNS_DIR = FIELDCHECK_DIR / "local_runs"
DEFAULT_LOCAL_CASES_DIR = FIELDCHECK_DIR / "local_cases"
