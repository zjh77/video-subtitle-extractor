from __future__ import annotations

import queue
import threading

from .runner import run_job


class JobQueue:
    def __init__(self) -> None:
        self._queue: queue.Queue[str] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._stop_event.clear()
        self._worker = threading.Thread(target=self._loop, name="vse-api-worker", daemon=True)
        self._worker.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._queue.put("")
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=2)

    def submit(self, job_id: str) -> None:
        self._queue.put(job_id)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            job_id = self._queue.get()
            if not job_id:
                continue
            try:
                run_job(job_id)
            finally:
                self._queue.task_done()
job_queue = JobQueue()
