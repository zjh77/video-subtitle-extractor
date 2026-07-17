from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


FileStatus = Literal["uploading", "ready", "deleted"]
JobStatus = Literal["queued", "running", "succeeded", "failed"]


class SubtitleAreaPayload(BaseModel):
    ymin: int = Field(ge=0)
    ymax: int = Field(ge=0)
    xmin: int = Field(ge=0)
    xmax: int = Field(ge=0)


class FileResponse(BaseModel):
    id: str
    drama_name: str
    episode_label: str | None = None
    original_filename: str
    stored_filename: str
    stored_path: str
    size_bytes: int
    mime_type: str | None = None
    status: FileStatus
    created_at: str


class FileListResponse(BaseModel):
    items: list[FileResponse]


class JobCreateRequest(BaseModel):
    file_id: str
    mode: str = "fast"
    language: str = "ch"
    generate_txt: bool = True
    subtitle_area: SubtitleAreaPayload | None = None


class JobResponse(BaseModel):
    id: str
    file_id: str
    drama_name: str
    episode_label: str | None = None
    status: JobStatus
    mode: str
    language: str
    generate_txt: bool
    subtitle_ymin: int | None = None
    subtitle_ymax: int | None = None
    subtitle_xmin: int | None = None
    subtitle_xmax: int | None = None
    job_dir: str
    log_path: str
    result_srt_path: str | None = None
    result_txt_path: str | None = None
    progress: float
    stage: str | None = None
    error_message: str | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None


class JobListResponse(BaseModel):
    items: list[JobResponse]


class JobLogResponse(BaseModel):
    job_id: str
    content: str
