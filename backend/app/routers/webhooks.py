"""
Webhook Endpoints Router (app/routers/webhooks.py)
Implements:
- GET /webhooks/meta (Meta Webhook Verification Challenge)
- POST /webhooks/meta (Meta Lead Ads Webhook with X-Hub-Signature-256 validation & idempotent lead processing)
- POST /webhooks/doubletick (DoubleTick Webhook for MESSAGE_RECEIVED and MESSAGE_STATUS_UPDATE)
"""
import hashlib
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import PlainTextResponse

from app.config import settings
from app.database import IntegrityError, Session, get_db
from app.models import WebhookEvent
from app.security.auth import verify_doubletick_webhook, verify_meta_webhook_signature
from app.services.ai_service import ai_service
from app.services.doubletick_service import doubletick_service
from app.services.lead_service import LeadService
from app.utils.logger import get_logger, sanitize_dict

logger = get_logger("webhooks_router")
router = APIRouter(tags=["Webhooks"])


@router.get("/webhooks/meta")
def verify_meta_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    """
    Meta Lead Ads Webhook Verification Endpoint.
    Verifies hub.mode == 'subscribe' and hub.verify_token == META_VERIFY_TOKEN.
    Returns hub.challenge in plain text as required by Meta Graph API Webhooks.
    """
    expected_token = settings.META_VERIFY_TOKEN
    if not expected_token:
        logger.error("META_VERIFY_TOKEN is not configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook verify token is not configured on the server.",
        )

    if hub_mode == "subscribe" and hub_verify_token == expected_token and hub_challenge is not None:
        logger.info("Meta webhook verification succeeded.")
        return PlainTextResponse(content=str(hub_challenge), status_code=200)

    logger.warning(f"Meta webhook verification failed (mode={hub_mode}).")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Webhook verification failed: invalid verify_token or mode.",
    )


@router.post("/webhooks/meta")
async def receive_meta_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    db: Session = Depends(get_db),
):
    """
    Meta Lead Ads Webhook Receiver.
    1. Validates X-Hub-Signature-256 HMAC-SHA256 signature using META_APP_SECRET.
    2. Rejects unverified requests with HTTP 401/403 so unverified campaign/lead data is never trusted.
    3. Logs every webhook event with idempotency key in `webhook_events`.
    4. Processes `leadgen` changes idempotently via LeadService.
    """
    raw_body = await request.body()

    if not verify_meta_webhook_signature(raw_body, x_hub_signature_256):
        logger.warning("Rejected Meta webhook with invalid X-Hub-Signature-256.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Hub-Signature-256 header.",
        )

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed JSON payload: {str(exc)}",
        ) from exc

    if payload.get("object") != "page":
        return {"status": "ignored", "reason": "unsupported_object_type"}

    entries = payload.get("entry") or []
    processed_leads = []
    duplicate_leads = []

    for entry in entries:
        changes = entry.get("changes") or []
        for change in changes:
            field = change.get("field")
            value = change.get("value") or {}
            if field != "leadgen":
                continue

            leadgen_id = str(value.get("leadgen_id") or "").strip()
            event_key = f"meta_leadgen_{leadgen_id}" if leadgen_id else (
                "meta_raw_" + hashlib.sha256(raw_body).hexdigest()[:32]
            )

            existing_event = (
                db.query(WebhookEvent)
                .filter(WebhookEvent.event_id == event_key)
                .first()
            )
            if existing_event and existing_event.processing_status == "PROCESSED":
                duplicate_leads.append(leadgen_id)
                continue

            if not existing_event:
                wh_event = WebhookEvent(
                    provider="meta",
                    event_id=event_key,
                    event_type="leadgen",
                    signature_verified=True,
                    processing_status="RECEIVED",
                    payload=sanitize_dict(value),
                )
                try:
                    db.add(wh_event)
                    db.commit()
                    db.refresh(wh_event)
                except IntegrityError:
                    db.rollback()
                    duplicate_leads.append(leadgen_id)
                    continue
            else:
                wh_event = existing_event

            result = LeadService.process_meta_lead_event(
                db=db,
                change_value=value,
            )
            if result.get("status") == "processed":
                wh_event.processing_status = "PROCESSED"
                processed_leads.append(result)
            elif result.get("status") == "duplicate":
                wh_event.processing_status = "PROCESSED"
                duplicate_leads.append(leadgen_id)
            else:
                wh_event.processing_status = "FAILED"
                wh_event.error_detail = str(result.get("message") or result.get("reason"))
                processed_leads.append(result)
            db.commit()

    return {
        "status": "ok",
        "processed_count": len(processed_leads),
        "duplicate_count": len(duplicate_leads),
        "results": processed_leads,
        "duplicates": duplicate_leads,
    }


@router.post("/webhooks/doubletick")
async def receive_doubletick_webhook(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_doubletick_signature: Optional[str] = Header(None, alias="X-Doubletick-Signature"),
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
    db: Session = Depends(get_db),
):
    """
    DoubleTick Webhook Receiver (POST /webhooks/doubletick).
    Supports documented events:
    - MESSAGE_RECEIVED
    - MESSAGE_STATUS_UPDATE
    Verifies webhook authentication via configured DOUBLETICK_WEBHOOK_SECRET.
    """
    raw_body = await request.body()

    if not verify_doubletick_webhook(
        raw_body=raw_body,
        authorization_header=authorization,
        signature_header=x_doubletick_signature,
        webhook_secret_header=x_webhook_secret,
    ):
        logger.warning("Rejected DoubleTick webhook due to invalid authentication credentials.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid DoubleTick webhook authentication.",
        )

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON body: {str(exc)}",
        ) from exc

    inner = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
    event_type = str(
        payload.get("event")
        or payload.get("eventType")
        or inner.get("event")
        or inner.get("eventType")
        or ("MESSAGE_STATUS_UPDATE" if "status" in inner and "text" not in inner else "MESSAGE_RECEIVED")
    ).upper().strip()

    msg_id = str(
        inner.get("messageId")
        or (inner.get("message") or {}).get("id")
        or payload.get("messageId")
        or hashlib.sha256(raw_body).hexdigest()[:24]
    )
    status_suffix = f"_{inner.get('status')}" if event_type == "MESSAGE_STATUS_UPDATE" else ""
    event_id = f"doubletick_{event_type}_{msg_id}{status_suffix}"

    existing_ev = db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first()
    if existing_ev:
        return {
            "status": "duplicate",
            "event_type": event_type,
            "event_id": event_id,
        }

    wh_event = WebhookEvent(
        provider="doubletick",
        event_id=event_id,
        event_type=event_type,
        signature_verified=True,
        processing_status="RECEIVED",
        payload=sanitize_dict(payload),
    )
    db.add(wh_event)
    db.commit()
    db.refresh(wh_event)

    if event_type == "MESSAGE_STATUS_UPDATE":
        result = doubletick_service.handle_status_update_webhook(db=db, payload=payload)
    elif event_type == "MESSAGE_RECEIVED":
        result = doubletick_service.handle_incoming_message_webhook(
            db=db,
            payload=payload,
            ai_service=ai_service,
        )
    else:
        result = {"handled": False, "event_type": event_type}

    wh_event.processing_status = "PROCESSED"
    db.commit()

    return {
        "status": "ok",
        "event_type": event_type,
        "event_id": event_id,
        "result": result,
    }
