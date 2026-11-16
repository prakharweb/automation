"""
Persistent Database-Backed Follow-up Worker (app/workers/followup_worker.py)
Designed for Render Background Worker / Cron Job (`python -m app.workers.followup_worker --once`)
or continuous daemon mode (`python -m app.workers.followup_worker`), plus on-demand trigger
from the API so it does not rely exclusively on ephemeral in-memory FastAPI tasks.

Enforces all WhatsApp & Business rules:
- Never sends duplicate follow-ups
- Stops follow-ups when customer replies (has_replied == True)
- Stops follow-ups when lead is converted (lead_status == "CONVERTED")
- Stops follow-ups when customer opts out (opted_out == True or whatsapp_opt_in == False)
- Stops follow-ups when automation is paused (automation_paused == True)
- Always uses approved WhatsApp templates for business-initiated follow-ups
"""
import argparse
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import settings
from app.database import Session, SessionLocal
from app.models import FollowupJob, Lead, SystemSetting, utc_now
from app.services.doubletick_service import DoubleTickService, doubletick_service
from app.utils.logger import get_logger

logger = get_logger("followup_worker")


def process_due_followups(
    db: Session,
    dt_service: Optional[DoubleTickService] = None,
    now_override: Optional[datetime] = None,
) -> Dict[str, Any]:
    svc = dt_service or doubletick_service
    now = now_override or utc_now()

    # Check global follow-up engine setting
    engine_setting = (
        db.query(SystemSetting)
        .filter(SystemSetting.setting_key == "followup_engine_config")
        .first()
    )
    if engine_setting and isinstance(engine_setting.setting_value, dict):
        if not engine_setting.setting_value.get("enabled", True):
            return {"processed": 0, "sent": 0, "cancelled": 0, "reason": "followup_engine_disabled"}

    scheduled_jobs: List[FollowupJob] = (
        db.query(FollowupJob)
        .filter(FollowupJob.status == "SCHEDULED")
        .order_by(FollowupJob.scheduled_at.asc())
        .all()
    )

    due_jobs: List[FollowupJob] = []
    for job in scheduled_jobs:
        sched = job.scheduled_at
        if isinstance(sched, str):
            sched = datetime.fromisoformat(sched)
        if sched.tzinfo is None:
            sched = sched.replace(tzinfo=timezone.utc)
        if sched <= now:
            due_jobs.append(job)

    sent_count = 0
    cancelled_count = 0
    failed_count = 0
    results = []

    for job in due_jobs:
        lead = db.query(Lead).filter(Lead.id == job.lead_id).first()
        if not lead:
            job.status = "CANCELLED_NO_LEAD"
            job.cancellation_reason = "Associated lead record not found"
            cancelled_count += 1
            continue

        # Rule 1: Stop if customer replied
        if lead.has_replied:
            job.status = "CANCELLED_REPLIED"
            job.cancellation_reason = "Customer already replied to WhatsApp conversation"
            cancelled_count += 1
            continue

        # Rule 2: Stop if lead is converted
        if lead.lead_status == "CONVERTED":
            job.status = "CANCELLED_CONVERTED"
            job.cancellation_reason = "Lead is already marked CONVERTED"
            cancelled_count += 1
            continue

        # Rule 3: Stop if customer opted out or lacks WhatsApp consent
        if lead.opted_out or not lead.whatsapp_opt_in or lead.lead_status == "OPTED_OUT":
            job.status = "CANCELLED_OPT_OUT"
            job.cancellation_reason = "Customer opted out or lacks WhatsApp opt-in"
            cancelled_count += 1
            continue

        # Rule 4: Stop if manual pause is active
        if lead.automation_paused:
            job.status = "CANCELLED_PAUSED"
            job.cancellation_reason = "Lead automation is manually paused"
            cancelled_count += 1
            continue

        # Rule 5: Prevent duplicate execution for same lead & step_number
        already_completed = (
            db.query(FollowupJob)
            .filter(
                FollowupJob.lead_id == lead.id,
                FollowupJob.step_number == job.step_number,
                FollowupJob.status == "COMPLETED",
            )
            .first()
        )
        if already_completed and already_completed.id != job.id:
            job.status = "CANCELLED_DUPLICATE"
            job.cancellation_reason = f"Follow-up step {job.step_number} already completed"
            cancelled_count += 1
            continue

        placeholders = (job.template_variables or {}).get("placeholders") or [
            lead.full_name,
            lead.campaign_name or "Space Consultant",
            "Follow-up Check-in",
        ]

        msg_log = svc.send_template_message(
            db=db,
            to_phone=lead.phone,
            template_name=job.template_name,
            language=job.template_language or "en",
            placeholders=placeholders,
            lead_id=lead.id,
            campaign_id=lead.campaign_id,
            content_preview=f"Automated Follow-up Step #{job.step_number}: {job.template_name}",
        )

        job.executed_at = now
        job.message_log_id = msg_log.id
        if msg_log.status == "SENT":
            job.status = "COMPLETED"
            sent_count += 1
        else:
            job.status = "FAILED"
            job.cancellation_reason = msg_log.error_message or "DoubleTick template send failed"
            failed_count += 1

        results.append(
            {
                "job_id": job.id,
                "lead_id": lead.id,
                "step_number": job.step_number,
                "status": job.status,
                "message_log_id": msg_log.id,
            }
        )

    db.commit()
    return {
        "processed": len(due_jobs),
        "sent": sent_count,
        "cancelled": cancelled_count,
        "failed": failed_count,
        "jobs": results,
    }


class FollowupBackgroundDaemon:
    def __init__(self, interval_seconds: int = 60):
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="FollowupWorkerThread")
        self._thread.start()
        logger.info(f"Persistent Follow-up Worker started (poll interval={self.interval_seconds}s).")

    def stop(self):
        self._stop_event.set()

    def _run_loop(self):
        while not self._stop_event.is_set():
            db = SessionLocal()
            try:
                res = process_due_followups(db)
                if res.get("processed", 0) > 0:
                    logger.info(f"Follow-up worker cycle completed: {res}")
            except Exception as exc:
                logger.error(f"Follow-up worker cycle error: {exc}")
            finally:
                db.close()
            self._stop_event.wait(self.interval_seconds)


followup_daemon = FollowupBackgroundDaemon(interval_seconds=settings.FOLLOWUP_POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Space Consultant Persistent Follow-up Worker")
    parser.add_argument("--once", action="store_true", help="Run a single poll cycle and exit (for Render Cron)")
    args = parser.parse_args()

    if args.once:
        session = SessionLocal()
        try:
            summary = process_due_followups(session)
            logger.info(f"Single follow-up worker execution finished: {summary}")
        finally:
            session.close()
    else:
        logger.info("Starting continuous follow-up worker process...")
        while True:
            session = SessionLocal()
            try:
                process_due_followups(session)
            except Exception as err:
                logger.error(f"Worker error: {err}")
            finally:
                session.close()
            time.sleep(settings.FOLLOWUP_POLL_INTERVAL_SECONDS)
