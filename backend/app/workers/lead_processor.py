"""
Lead Processor Worker (app/workers/lead_processor.py)
Provides retry/reprocessing for any webhook events that failed transient Graph API fetches
and supports manual resend of eligible leads.
"""
from typing import Any, Dict
from app.database import Session
from app.models import WebhookEvent
from app.services.lead_service import LeadService
from app.utils.logger import get_logger

logger = get_logger("lead_processor")


def retry_failed_webhook_events(db: Session) -> Dict[str, Any]:
    failed_events = (
        db.query(WebhookEvent)
        .filter(
            WebhookEvent.provider == "meta",
            WebhookEvent.processing_status == "FAILED",
        )
        .all()
    )
    retried = 0
    recovered = 0
    for ev in failed_events:
        retried += 1
        payload = ev.payload or {}
        entries = payload.get("entry") or []
        for entry in entries:
            for change in entry.get("changes") or []:
                if change.get("field") == "leadgen":
                    res = LeadService.process_meta_lead_event(db, change.get("value") or {})
                    if res.get("status") in ("processed", "duplicate"):
                        ev.processing_status = "PROCESSED"
                        recovered += 1
    db.commit()
    return {"retried": retried, "recovered": recovered}
