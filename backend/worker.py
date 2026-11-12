"""
AEGISSTOR Standalone Background Worker
Runs as a dedicated process (e.g. Render Background Worker) to execute queued ML
training jobs, recover stale/crashed jobs safely, and emit worker heartbeats.
"""
import json
import logging
import os
import signal
import socket
import time
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.database import SessionLocal
from app.models.entities import ApplicationSetting, BackgroundJob

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aegisstor.worker")

_RUNNING = True


def _handle_signal(signum, _frame):
    global _RUNNING
    logger.info("Worker received signal %s; shutting down gracefully after current job...", signum)
    _RUNNING = False


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def write_worker_heartbeat(worker_id: str, status: str = "healthy", current_job_id: str | None = None) -> None:
    db = SessionLocal()
    try:
        payload = json.dumps({
            "worker_id": worker_id,
            "status": status,
            "current_job_id": current_job_id,
            "pid": os.getpid(),
            "hostname": socket.gethostname(),
            "last_seen_utc": _utc_now().isoformat(),
        })
        row = db.query(ApplicationSetting).filter(ApplicationSetting.key == "worker_heartbeat").first()
        if row:
            row.value_json = payload
            row.updated_at = _utc_now()
        else:
            db.add(ApplicationSetting(key="worker_heartbeat", value_json=payload, category="worker", updated_at=_utc_now()))
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("Failed to persist worker heartbeat: %s", exc)
    finally:
        db.close()


def recover_stale_jobs(stale_seconds: int | None = None) -> int:
    """
    Marks crashed/abandoned RUNNING jobs as FAILED (never falsely COMPLETED) so partial
    artifacts are not promoted and operators can safely inspect/re-trigger.
    """
    timeout_sec = stale_seconds if stale_seconds is not None else settings.WORKER_STALE_JOB_TIMEOUT_SEC
    cutoff = _utc_now() - timedelta(seconds=timeout_sec)
    db = SessionLocal()
    recovered = 0
    try:
        stale_jobs = (
            db.query(BackgroundJob)
            .filter(BackgroundJob.status == "RUNNING")
            .filter((BackgroundJob.updated_at == None) | (BackgroundJob.updated_at < cutoff))
            .all()
        )
        for job in stale_jobs:
            job.status = "FAILED"
            job.stage = "FAILED"
            job.error_message = (
                f"Worker crash/timeout recovery after {timeout_sec}s inactivity; "
                "partial artifacts discarded and previous champion retained."
            )
            job.completed_at = _utc_now()
            job.updated_at = _utc_now()
            recovered += 1
        if recovered:
            db.commit()
            logger.warning("Recovered %d stale RUNNING background jobs -> FAILED", recovered)
        return recovered
    except Exception as exc:
        db.rollback()
        logger.error("Failed stale job recovery: %s", exc)
        return 0
    finally:
        db.close()


def process_next_queued_job(worker_id: str) -> bool:
    """Claim and execute the oldest QUEUED job. Returns True if a job was processed."""
    db = SessionLocal()
    job_id = None
    job_type = None
    storage_id = None
    try:
        job = (
            db.query(BackgroundJob)
            .filter(BackgroundJob.status == "QUEUED")
            .order_by(BackgroundJob.created_at.asc())
            .first()
        )
        if not job:
            return False
        job_id = job.id
        job_type = job.job_type
        storage_id = job.storage_id
        # Atomically claim job
        updated = (
            db.query(BackgroundJob)
            .filter(BackgroundJob.id == job_id, BackgroundJob.status == "QUEUED")
            .update({"status": "RUNNING", "stage": "VALIDATING_DATA", "updated_at": _utc_now()})
        )
        db.commit()
        if not updated:
            return False
    finally:
        db.close()

    write_worker_heartbeat(worker_id, status="busy", current_job_id=job_id)
    logger.info("Worker %s claimed job %s (type=%s, storage=%s)", worker_id, job_id, job_type, storage_id)
    try:
        if job_type in ("ML_TRAINING", "MODEL_TRAIN") and storage_id:
            from app.api.v1.endpoints_intelligence import _run_async_training_job
            _run_async_training_job(job_id=job_id, storage_id=storage_id, days=365, actor="worker")
        else:
            db2 = SessionLocal()
            try:
                j = db2.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
                if j:
                    j.status = "FAILED"
                    j.stage = "FAILED"
                    j.error_message = f"Unsupported worker job_type: {job_type}"
                    j.completed_at = _utc_now()
                    j.updated_at = _utc_now()
                    db2.commit()
            finally:
                db2.close()
    except Exception as exc:
        logger.error("Worker job %s failed: %s", job_id, exc, exc_info=True)
    finally:
        write_worker_heartbeat(worker_id, status="healthy", current_job_id=None)
    return True


def main() -> None:
    settings.validate_production_safety()
    worker_id = f"worker-{socket.gethostname()}-{os.getpid()}"
    logger.info("Starting AEGISSTOR Background Worker (%s)...", worker_id)
    recover_stale_jobs()
    last_hb = 0.0
    while _RUNNING:
        now = time.time()
        if now - last_hb >= settings.WORKER_HEARTBEAT_INTERVAL_SEC:
            write_worker_heartbeat(worker_id, status="healthy")
            last_hb = now
        did_work = process_next_queued_job(worker_id)
        if not did_work:
            time.sleep(settings.WORKER_POLL_INTERVAL_SEC)
    write_worker_heartbeat(worker_id, status="stopped")
    logger.info("Worker %s stopped cleanly.", worker_id)


if __name__ == "__main__":
    main()
