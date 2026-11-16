"""
DoubleTick Integration Router (app/routers/doubletick.py)
Endpoints:
- GET /api/doubletick/status
- POST /api/doubletick/test-message
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.database import Session, get_db
from app.models import User
from app.schemas.api_schemas import DoubleTickTestMessageRequest
from app.security.auth import record_audit_log, require_admin, require_staff
from app.services.doubletick_service import doubletick_service
from app.utils.phone import normalize_phone_number

router = APIRouter(prefix="/api/doubletick", tags=["DoubleTick WhatsApp Integration"])


@router.get("/status")
def get_doubletick_status(
    current_user: User = Depends(require_staff),
):
    return {
        "status": "success",
        "data": doubletick_service.get_status(),
    }


@router.post("/test-message")
def send_doubletick_test_message(
    req: DoubleTickTestMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    normalized_phone = normalize_phone_number(req.recipient_phone)
    if not normalized_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid recipient phone number: {req.recipient_phone}",
        )

    msg_type = req.message_type.upper().strip()
    if msg_type == "TEMPLATE":
        log_entry = doubletick_service.send_template_message(
            db=db,
            to_phone=normalized_phone,
            template_name=req.template_name or "hospital_enquiry",
            language=req.language or "en",
            placeholders=req.placeholders,
            content_preview=f"Admin Test Template: {req.template_name}",
        )
    elif msg_type == "TEXT":
        log_entry = doubletick_service.send_text_message(
            db=db,
            to_phone=normalized_phone,
            text=req.text or "Hello from Space Consultant Lead Automation Platform!",
            lead=None,
        )
    elif msg_type == "IMAGE":
        if not req.media_url:
            raise HTTPException(status_code=400, detail="media_url is required for IMAGE messages.")
        log_entry = doubletick_service.send_image_message(
            db=db,
            to_phone=normalized_phone,
            media_url=req.media_url,
            caption=req.caption,
        )
    elif msg_type == "DOCUMENT":
        if not req.media_url:
            raise HTTPException(status_code=400, detail="media_url is required for DOCUMENT messages.")
        log_entry = doubletick_service.send_document_message(
            db=db,
            to_phone=normalized_phone,
            media_url=req.media_url,
            filename=req.filename or "Space_Consultant_Brochure.pdf",
            caption=req.caption,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported message_type: {msg_type}")

    record_audit_log(
        db=db,
        action="DOUBLETICK_TEST_MESSAGE",
        entity_type="message_log",
        entity_id=log_entry.id,
        actor=current_user,
        details={"message_type": msg_type, "template_name": req.template_name, "status": log_entry.status},
    )

    return {
        "status": "success",
        "data": log_entry.to_dict(),
    }
