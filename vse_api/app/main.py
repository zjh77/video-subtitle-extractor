from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from . import db
from .config import ensure_data_dirs
from .job_queue import job_queue
from .schemas import (
    FileListResponse,
    FileResponse as FileModel,
    JobCreateRequest,
    JobListResponse,
    JobLogResponse,
    JobResponse,
)
from .storage import job_paths, persist_upload, remove_file_tree


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


app = FastAPI(title="VSE Web API", version="0.2.0")


@app.on_event("startup")
def on_startup() -> None:
    ensure_data_dirs()
    db.init_db()
    job_queue.start()


@app.on_event("shutdown")
def on_shutdown() -> None:
    job_queue.stop()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/files", response_model=FileModel)
async def create_file(
    file: UploadFile = File(...),
    drama_name: str = Form(...),
    episode_label: str | None = Form(None),
    filename: str | None = Form(None),
) -> dict:
    file_id = f"file_{uuid4().hex}"
    stored_path, size_bytes, stored_filename = persist_upload(file_id, file, desired_name=filename)
    record = {
        "id": file_id,
        "drama_name": drama_name,
        "episode_label": episode_label,
        "original_filename": file.filename or stored_filename,
        "stored_filename": stored_filename,
        "stored_path": str(stored_path),
        "size_bytes": size_bytes,
        "mime_type": file.content_type,
        "status": "ready",
        "created_at": utc_now(),
    }
    db.create_file(record)
    return _require_file(file_id)


@app.get("/api/files", response_model=FileListResponse)
def list_files(drama_name: str | None = None, limit: int = 100) -> dict[str, list[dict]]:
    return {"items": db.list_files(drama_name=drama_name, limit=limit)}


@app.get("/api/files/{file_id}", response_model=FileModel)
def get_file(file_id: str) -> dict:
    return _require_file(file_id)


@app.delete("/api/files/{file_id}")
def delete_file(file_id: str, force: bool = False) -> dict[str, str]:
    file_record = _require_file(file_id)
    jobs = db.list_jobs_for_file(file_id)
    if jobs:
        if not force:
            raise HTTPException(
                status_code=409,
                detail="File already has related jobs; delete those jobs first or use force=true",
            )
        for job in jobs:
            shutil.rmtree(job["job_dir"], ignore_errors=True)
            db.delete_job(job["id"])
    remove_file_tree(file_record["stored_path"])
    db.delete_file(file_id)
    return {"status": "deleted"}


@app.post("/api/jobs", response_model=JobResponse)
def create_job(payload: JobCreateRequest) -> dict:
    file_record = _require_file(payload.file_id)
    if file_record["status"] != "ready":
        raise HTTPException(status_code=409, detail="File is not ready for job creation")

    job_id = f"job_{uuid4().hex}"
    paths = job_paths(job_id)
    area = payload.subtitle_area
    record = {
        "id": job_id,
        "file_id": file_record["id"],
        "drama_name": file_record["drama_name"],
        "episode_label": file_record["episode_label"],
        "status": "queued",
        "mode": payload.mode,
        "language": payload.language,
        "generate_txt": int(payload.generate_txt),
        "subtitle_ymin": area.ymin if area else None,
        "subtitle_ymax": area.ymax if area else None,
        "subtitle_xmin": area.xmin if area else None,
        "subtitle_xmax": area.xmax if area else None,
        "job_dir": str(paths["root"]),
        "log_path": str(paths["logs"] / "job.log"),
        "result_srt_path": None,
        "result_txt_path": None,
        "progress": 0,
        "stage": "queued",
        "error_message": None,
        "created_at": utc_now(),
        "started_at": None,
        "finished_at": None,
    }
    db.create_job(record)
    job_queue.submit(job_id)
    return _require_job(job_id)


@app.get("/api/jobs", response_model=JobListResponse)
def list_jobs(drama_name: str | None = None, status: str | None = None, limit: int = 100) -> dict[str, list[dict]]:
    return {"items": db.list_jobs(drama_name=drama_name, status=status, limit=limit)}


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> dict:
    return _require_job(job_id)


@app.get("/api/jobs/{job_id}/logs", response_model=JobLogResponse)
def get_job_logs(job_id: str) -> dict[str, str]:
    job = _require_job(job_id)
    log_path = Path(job["log_path"])
    content = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    return {"job_id": job_id, "content": content}


@app.get("/api/jobs/{job_id}/files/{kind}")
def download_job_file(job_id: str, kind: str) -> FileResponse:
    job = _require_job(job_id)
    if kind == "srt":
        path = job.get("result_srt_path")
    elif kind == "txt":
        path = job.get("result_txt_path")
    else:
        raise HTTPException(status_code=404, detail="Unsupported file kind")

    if not path or not Path(path).exists():
        raise HTTPException(status_code=404, detail="Requested file is not available")

    return FileResponse(path=path, filename=Path(path).name)


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str) -> dict[str, str]:
    job = _require_job(job_id)
    shutil.rmtree(job["job_dir"], ignore_errors=True)
    db.delete_job(job_id)
    return {"status": "deleted"}


def _require_file(file_id: str) -> dict:
    file_record = db.get_file(file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
    return file_record


def _require_job(job_id: str) -> dict:
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
