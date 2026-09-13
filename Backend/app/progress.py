import threading

_lock = threading.Lock()
_progress = {}


def init_progress(job_id: str, total: int):
    with _lock:
        _progress[job_id] = {"total": total, "completed": 0, "current": None}


def increment_progress(job_id: str, current_filename: str | None = None):
    with _lock:
        if job_id in _progress:
            _progress[job_id]["completed"] += 1
            _progress[job_id]["current"] = current_filename


def get_progress(job_id: str):
    with _lock:
        return _progress.get(job_id)


def clear_progress(job_id: str):
    with _lock:
        _progress.pop(job_id, None)