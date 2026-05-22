"""Run the FastAPI API with the repo's local venv when available.

Why this exists:
- Avoids "uvicorn: command not found" when the venv isn't activated.
- Avoids confusion about current working directory and PYTHONPATH.

Usage:
  python3 scripts/run_api.py

Optional env vars:
  OPENROUTER_API_KEY=...  (required for chat + embeddings calls)
  HOST=127.0.0.1
  PORT=8000
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _find_venv_python(repo_root: Path) -> Path | None:
    candidates = [
        repo_root / ".venv" / "bin" / "python",
        repo_root / ".venv" / "bin" / "python3",
        repo_root / ".venv" / "Scripts" / "python.exe",  # Windows
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    host = os.environ.get("HOST", "127.0.0.1")
    port = os.environ.get("PORT", "8000")

    venv_python = _find_venv_python(repo_root)
    python_exe = str(venv_python) if venv_python else sys.executable

    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(repo_root))

    cmd = [
        python_exe,
        "-m",
        "uvicorn",
        "app.main:app",
        "--reload",
        "--host",
        host,
        "--port",
        port,
    ]

    try:
        return subprocess.call(cmd, cwd=str(repo_root), env=env)
    except FileNotFoundError:
        print("Could not find a Python executable to start the server.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
