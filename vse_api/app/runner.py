from __future__ import annotations

import traceback
from datetime import datetime, timezone
from pathlib import Path
from types import MethodType

import cv2

from backend.bean.subtitle_area import SubtitleArea as EngineSubtitleArea
from backend.config import config as vse_config
from backend.main import SubtitleExtractor

from . import db
from .storage import job_paths


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_job(job_id: str) -> None:
    job = db.get_job(job_id)
    if not job:
        return

    file_record = db.get_file(job["file_id"])
    if not file_record:
        db.update_job(
            job_id,
            status="failed",
            finished_at=utc_now(),
            stage="failed",
            error_message="Associated file record not found.",
        )
        return

    db.update_job(job_id, status="running", started_at=utc_now(), stage="starting", progress=0)
    paths = job_paths(job_id)
    log_path = Path(job["log_path"])

    def write_log(message: str) -> None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")

    original_config = {
        "mode": vse_config.mode.value,
        "language": vse_config.language.value,
        "generate_txt": vse_config.generateTxt.value,
        "save_directory": vse_config.saveDirectory.value,
    }

    try:
        source_path = Path(file_record["stored_path"])
        if not source_path.exists():
            raise FileNotFoundError(f"Input file does not exist: {source_path}")

        area = _resolve_subtitle_area(job, source_path)

        vse_config.mode.value = job["mode"]
        vse_config.language.value = job["language"]
        vse_config.generateTxt.value = job["generate_txt"]
        vse_config.saveDirectory.value = str(paths["output"])

        extractor = SubtitleExtractor(str(source_path))
        _bind_job_paths(extractor, paths, source_path)

        if area is not None:
            extractor.sub_area = area

        def append_output(self: SubtitleExtractor, *args: object) -> None:
            text = " ".join(str(arg) for arg in args)
            write_log(text)

        def on_progress(ocr: float, frame_extract: float, progress_total: float, is_finished: bool, post: float) -> None:
            overall = round((ocr + frame_extract + post) / 3.0, 2)
            stage = f"ocr={ocr:.1f}, frame={frame_extract:.1f}, post={post:.1f}"
            db.update_job(job_id, progress=overall, stage=stage)
            if is_finished:
                db.update_job(job_id, progress=100, stage="finishing")

        extractor.append_output = MethodType(append_output, extractor)
        extractor.add_progress_listener(on_progress)

        write_log(f"Running extractor for: {source_path}")
        extractor.run()

        srt_path = Path(extractor.subtitle_output_path)
        txt_path = srt_path.with_suffix(".txt") if job["generate_txt"] else None

        db.update_job(
            job_id,
            status="succeeded",
            finished_at=utc_now(),
            progress=100,
            stage="completed",
            result_srt_path=str(srt_path) if srt_path.exists() else None,
            result_txt_path=str(txt_path) if txt_path and txt_path.exists() else None,
            error_message=None,
        )
        write_log("Job completed successfully.")
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        write_log(message)
        write_log(traceback.format_exc())
        db.update_job(
            job_id,
            status="failed",
            finished_at=utc_now(),
            stage="failed",
            error_message=message,
        )
    finally:
        vse_config.mode.value = original_config["mode"]
        vse_config.language.value = original_config["language"]
        vse_config.generateTxt.value = original_config["generate_txt"]
        vse_config.saveDirectory.value = original_config["save_directory"]


def _resolve_subtitle_area(job: dict, source_path: Path) -> EngineSubtitleArea | None:
    if all(job.get(key) is not None for key in ("subtitle_ymin", "subtitle_ymax", "subtitle_xmin", "subtitle_xmax")):
        return EngineSubtitleArea(
            ymin=job["subtitle_ymin"],
            ymax=job["subtitle_ymax"],
            xmin=job["subtitle_xmin"],
            xmax=job["subtitle_xmax"],
        )

    cap = cv2.VideoCapture(str(source_path))
    try:
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    finally:
        cap.release()

    if height <= 0 or width <= 0:
        raise ValueError("Could not read video dimensions to infer subtitle area.")

    return EngineSubtitleArea(
        ymin=int(height * 0.78),
        ymax=int(height * 0.99),
        xmin=int(width * 0.05),
        xmax=int(width * 0.95),
    )


def _bind_job_paths(extractor: SubtitleExtractor, paths: dict[str, Path], source_path: Path) -> None:
    stem = source_path.stem
    extractor.temp_output_dir = str(paths["work"])
    extractor.frame_output_dir = str(paths["work"] / "frames")
    extractor.subtitle_output_dir = str(paths["work"] / "subtitle")
    extractor.vsf_subtitle = str(paths["work"] / "subtitle" / "raw_vsf.srt")
    extractor.raw_subtitle_path = str(paths["work"] / "subtitle" / "raw.txt")
    extractor.subtitle_output_path = str(paths["output"] / f"{stem}.srt")
