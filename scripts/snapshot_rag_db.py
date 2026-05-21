"""Create a portable offline snapshot of the local RAG database.

What it snapshots:
  - Chroma persistence directory (default: ./chroma_db)
  - Optional: processed corpus artifacts (./data/*.jsonl, ./data/urls.txt)

Usage:
  PYTHONPATH="$PWD" .venv/bin/python -u scripts/snapshot_rag_db.py --out snapshots

Restore:
  - Extract the tar.gz and place the `chroma_db/` folder back in the project root
    (or set `CHROMA_PERSIST_DIR` to the restored location).
"""

from __future__ import annotations

import argparse
import tarfile
from datetime import datetime
from pathlib import Path

from app.core.config import settings


def _add_if_exists(tar: tarfile.TarFile, path: Path, arcname: str) -> None:
    if path.exists():
        tar.add(str(path), arcname=arcname)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=str, default="snapshots")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"rag_snapshot_{ts}.tar.gz"

    chroma_dir = Path(settings.CHROMA_PERSIST_DIR)
    data_dir = Path("data")

    with tarfile.open(out_path, "w:gz") as tar:
        _add_if_exists(tar, chroma_dir, arcname="chroma_db")
        _add_if_exists(tar, data_dir / "urls.txt", arcname="data/urls.txt")
        _add_if_exists(tar, data_dir / "raw_pages.jsonl", arcname="data/raw_pages.jsonl")
        _add_if_exists(tar, data_dir / "processed_pages.jsonl", arcname="data/processed_pages.jsonl")

    print(f"Wrote snapshot: {out_path}")


if __name__ == "__main__":
    main()
