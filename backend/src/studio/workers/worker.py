"""Worker : dépile la file de tâches persistée en base, via le même code."""
from __future__ import annotations

import time

from ..config import settings
from ..database import SessionLocal
from ..domain.models import Task
from ..orchestration.workflow import process_task


def run_worker_once(limit: int = 10) -> int:
    db = SessionLocal()
    processed = 0
    try:
        tasks = (
            db.query(Task)
            .filter(Task.status.in_(["pending"]))
            .order_by(Task.created_at)
            .limit(limit)
            .all()
        )
        for t in tasks:
            t.status = "running"
            t.attempts += 1
            db.commit()
            try:
                process_task(db, t)
                db.commit()
                processed += 1
            except Exception as e:  # noqa: BLE001 — erreur technique, reprise bornée
                db.rollback()
                t2 = db.get(Task, t.id)
                t2.last_error = str(e)[:500]
                t2.status = "failed" if t2.attempts >= t2.max_attempts else "pending"
                db.commit()
    finally:
        db.close()
    return processed


def run_worker() -> None:
    while True:
        try:
            run_worker_once()
        except Exception:  # noqa: BLE001
            pass
        time.sleep(settings.generation_poll_interval)


if __name__ == "__main__":
    run_worker()
