from __future__ import annotations

import re
import shutil
from pathlib import Path

from fastapi import UploadFile

from .config import DATA_ROOT, JOBS_ROOT, ensure_data_dirs


def file_paths(file_id: str) -> dict[str, Path]:
    ensure_data_dirs()
    root = DATA_ROOT / "files" / file_id
    root.mkdir(parents=True, exist_ok=True)
    return {"root": root}


def job_paths(job_id: str) -> dict[str, Path]:
    ensure_data_dirs()
    root = JOBS_ROOT / job_id
    paths = {
        "root": root,
        "work": root / "work",
        "output": root / "output",
        "logs": root / "logs",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def sanitize_filename(name: str) -> str:
    candidate = Path(name).name
    stem = Path(candidate).stem
    suffix = Path(candidate).suffix or ".mp4"
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    if not safe_stem:
        safe_stem = "video"
    safe_suffix = re.sub(r"[^A-Za-z0-9.]+", "", suffix)
    if not safe_suffix.startswith("."):
        safe_suffix = f".{safe_suffix}" if safe_suffix else ".mp4"
    return f"{safe_stem}{safe_suffix}"


def persist_upload(file_id: str, upload: UploadFile, desired_name: str | None = None) -> tuple[Path, int, str]:
    paths = file_paths(file_id)
    stored_filename = sanitize_filename(desired_name or upload.filename or "video.mp4")
    destination = paths["root"] / stored_filename
    size_bytes = 0
    with destination.open("wb") as f:
        while True:
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            size_bytes += len(chunk)
            f.write(chunk)
    return destination, size_bytes, stored_filename


def remove_file_tree(stored_path: str) -> None:
    root = Path(stored_path).parent
    shutil.rmtree(root, ignore_errors=True)
