"""
Templates, Messages & Follow-ups Router (app/routers/messages.py)
Endpoints:
Templates:
- GET /api/templates
- POST /api/templates
- PUT /api/templates/{id}
Messages:
- GET /api/messages
- GET /api/messages/{id}
Follow-ups:
- GET /api/followups
- POST /api/followups
- PUT /api/followups/{id}
- POST /api/followups/process-due
"""
from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database import Session, get_db
from app.models import (
    FollowupJob,
    IncomingMessage,
    Lead,
    MessageLog,
    User,
    WhatsAppTemplate,
    utc_now,
)
from app.schemas.api_schemas import (
    FollowupCreateRequest,
    FollowupUpdateRequest,
    TemplateCreateRequest,
    TemplateUpdateRequest,
)
from app.security.auth import record_audit_log, require_admin, require_staff
from app.workers.followup_worker import process_due_followups

router = APIRouter(tags=["Templates, Messages & Follow-ups"])


# --- WHATSAPP TEMPLATES ---
@router.get("/api/templates")
def list_templates(
    purpose: Optional[str] = None,
    approval_status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    q = db.query(WhatsAppTemplate)
    if purpose:
        q = q.filter(WhatsAppTemplate.purpose == purpose)
    if approval_status:
        q = q.filter(WhatsAppTemplate.approval_status == approval_status)
    templates = q.order_by(WhatsAppTemplate.created_at.desc()).all()
    return {
        "status": "success",
        "total": len(templates),
        "data": [t.to_dict() for t in templates],
    }


@router.post("/api/templates", status_code=status.HTTP_201_CREATED)
def create_template(
    req: TemplateCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    existing = (
        db.query(WhatsAppTemplate)
        .filter(WhatsAppTemplate.template_name == req.template_name)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Template '{req.template_name}' already exists.",
        )

    tpl = WhatsAppTemplate(
        template_name=req.template_name,
        language=req.language,
        category=req.category,
        purpose=req.purpose,
        header_type=req.header_type,
        header_text=req.header_text,
        body_text=req.body_text,
        footer_text=req.footer_text,
        variables_schema=req.variables_schema,
        buttons_schema=req.buttons_schema,
        approval_status=req.approval_status,
        is_active=req.is_active,
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)

    record_audit_log(
        db=db,
        action="WHATSAPP_TEMPLATE_CREATED",
        entity_type="whatsapp_template",
        entity_id=tpl.id,
        actor=current_user,
        details={"template_name": tpl.template_name, "purpose": tpl.purpose},
    )
    return {"status": "success", "data": tpl.to_dict()}


@router.put("/api/templates/{template_id}")
def update_template(
    template_id: str,
    req: TemplateUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    tpl = db.query(WhatsAppTemplate).filter(WhatsAppTemplate.id == template_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="WhatsApp template not found.")

    for field in [
        "language",
        "category",
        "purpose",
        "header_type",
        "header_text",
        "body_text",
        "footer_text",
        "variables_schema",
        "buttons_schema",
        "approval_status",
        "is_active",
    ]:
        val = getattr(req, field)
        if val is not None:
            setattr(tpl, field, val)

    db.commit()
    db.refresh(tpl)

    record_audit_log(
        db=db,
        action="WHATSAPP_TEMPLATE_UPDATED",
        entity_type="whatsapp_template",
        entity_id=tpl.id,
        actor=current_user,
        details={"template_name": tpl.template_name, "approval_status": tpl.approval_status},
    )
    return {"status": "success", "data": tpl.to_dict()}


# --- MESSAGE LOGS ---
@router.get("/api/messages")
def list_messages(
    status_filter: Optional[str] = Query(None, alias="status"),
    message_type: Optional[str] = None,
    lead_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    q = db.query(MessageLog)
    if status_filter:
        q = q.filter(MessageLog.status == status_filter)
    if message_type:
        q = q.filter(MessageLog.message_type == message_type)
    if lead_id:
        q = q.filter(MessageLog.lead_id == lead_id)

    outbound = q.order_by(MessageLog.created_at.desc()).limit(limit).all()
    inbound = db.query(IncomingMessage).order_by(IncomingMessage.received_at.desc()).limit(50).all()
    leads_by_id = {l.id: l for l in db.query(Lead).all()}

    enriched_outbound = []
    for m in outbound:
        d = m.to_dict()
        lead = leads_by_id.get(m.lead_id) if m.lead_id else None
        d["lead_name"] = lead.full_name if lead else "Unknown"
        d["campaign_name"] = lead.campaign_name if lead else "Direct"
        enriched_outbound.append(d)

    return {
        "status": "success",
        "total": len(enriched_outbound),
        "data": enriched_outbound,
        "incoming_messages": [i.to_dict() for i in inbound],
    }


@router.get("/api/messages/{message_id}")
def get_message_detail(
    message_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    msg = db.query(MessageLog).filter(MessageLog.id == message_id).first()
    if not msg:
        msg = db.query(MessageLog).filter(MessageLog.doubletick_message_id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message log not found.")
    return {"status": "success", "data": msg.to_dict()}


# --- FOLLOW-UP MANAGEMENT ---
@router.get("/api/followups")
def list_followups(
    status_filter: Optional[str] = Query(None, alias="status"),
    lead_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    q = db.query(FollowupJob)
    if status_filter:
        q = q.filter(FollowupJob.status == status_filter)
    if lead_id:
        q = q.filter(FollowupJob.lead_id == lead_id)

    jobs = q.order_by(FollowupJob.scheduled_at.desc()).all()
    leads_by_id = {l.id: l for l in db.query(Lead).all()}

    enriched = []
    for j in jobs:
        d = j.to_dict()
        lead = leads_by_id.get(j.lead_id)
        d["lead_name"] = lead.full_name if lead else "Unknown Lead"
        d["lead_phone"] = lead.phone if lead else ""
        d["campaign_name"] = lead.campaign_name if lead else ""
        d["lead_status"] = lead.lead_status if lead else ""
        enriched.append(d)

    return {
        "status": "success",
        "total": len(enriched),
        "data": enriched,
    }


@router.post("/api/followups", status_code=status.HTTP_201_CREATED)
def schedule_manual_followup(
    req: FollowupCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    lead = db.query(Lead).filter(Lead.id == req.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    if lead.opted_out or not lead.whatsapp_opt_in:
        raise HTTPException(status_code=400, detail="Cannot schedule follow-up for opted-out lead.")
    if lead.lead_status == "CONVERTED":
        raise HTTPException(status_code=400, detail="Cannot schedule follow-up for converted lead.")

    existing = (
        db.query(FollowupJob)
        .filter(
            FollowupJob.lead_id == lead.id,
            FollowupJob.step_number == req.step_number,
            FollowupJob.status == "SCHEDULED",
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"A scheduled follow-up for step #{req.step_number} already exists for this lead.",
        )

    job = FollowupJob(
        lead_id=lead.id,
        automation_id=lead.automation_id,
        step_number=req.step_number,
        template_name=req.template_name,
        template_language=req.template_language,
        template_variables=req.template_variables
        or {"placeholders": [lead.full_name, lead.campaign_name or "Space Consultant", "Follow-up"]},
        scheduled_at=utc_now() + timedelta(hours=max(1, req.delay_hours)),
        status="SCHEDULED",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return {"status": "success", "data": job.to_dict()}


@router.put("/api/followups/{job_id}")
def update_followup_job(
    job_id: str,
    req: FollowupUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    job = db.query(FollowupJob).filter(FollowupJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Follow-up job not found.")

    if req.status is not None:
        job.status = req.status
    if req.scheduled_at is not None:
        job.scheduled_at = req.scheduled_at
    if req.template_name is not None:
        job.template_name = req.template_name
    if req.cancellation_reason is not None:
        job.cancellation_reason = req.cancellation_reason

    db.commit()
    db.refresh(job)
    return {"status": "success", "data": job.to_dict()}


@router.post("/api/followups/process-due")
def trigger_due_followups_now(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    summary = process_due_followups(db=db)
    return {"status": "success", "data": summary}
