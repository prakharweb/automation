"""
Lead Management Router (app/routers/leads.py)
Endpoints:
- GET /api/leads (supports search, campaign filter, date range filter, status filter, and CSV export)
- GET /api/leads/{id}
- PUT /api/leads/{id}
- POST /api/leads/{id}/assign
- POST /api/leads/{id}/resend
"""
import csv
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.database import Session, get_db, or_
from app.models import (
    CampaignAutomation,
    FollowupJob,
    IncomingMessage,
    Lead,
    LeadAssignment,
    LeadConsent,
    MessageLog,
    User,
    utc_now,
)
from app.schemas.api_schemas import (
    LeadAssignRequest,
    LeadResendRequest,
    LeadUpdateRequest,
)
from app.security.auth import record_audit_log, require_staff
from app.services.campaign_service import campaign_service
from app.services.doubletick_service import doubletick_service
from app.utils.phone import normalize_phone_number

router = APIRouter(prefix="/api/leads", tags=["Lead Management"])


@router.get("")
def list_leads(
    search: Optional[str] = Query(None, description="Search by name, phone, email, or city"),
    campaign_id: Optional[str] = Query(None, description="Filter by campaign_id or meta_campaign_id"),
    campaign_purpose: Optional[str] = Query(None, description="Filter by campaign purpose"),
    lead_status: Optional[str] = Query(None, description="Filter by lead_status"),
    message_status: Optional[str] = Query(None, description="Filter by message_status"),
    date_from: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    export: Optional[str] = Query(None, description="Set to 'csv' to download CSV"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    q = db.query(Lead)

    if search:
        pattern = f"%{search.strip()}%"
        q = q.filter(
            or_(
                Lead.full_name.ilike(pattern),
                Lead.phone.ilike(pattern),
                Lead.email.ilike(pattern),
                Lead.campaign_name.ilike(pattern),
            )
        )

    if campaign_id:
        q = q.filter(
            or_(
                Lead.campaign_id == campaign_id,
                Lead.meta_campaign_id == campaign_id,
                Lead.automation_id == campaign_id,
            )
        )

    if campaign_purpose:
        q = q.filter(Lead.campaign_purpose == campaign_purpose)

    if lead_status:
        q = q.filter(Lead.lead_status == lead_status)

    if message_status:
        q = q.filter(Lead.message_status == message_status)

    leads_all = q.order_by(Lead.created_at.desc()).all()

    # Date filtering
    filtered = []
    for l in leads_all:
        created_str = str(l.created_at)[:10] if l.created_at else ""
        if date_from and created_str < date_from[:10]:
            continue
        if date_to and created_str > date_to[:10]:
            continue
        filtered.append(l)

    if export and export.lower() == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Lead ID",
                "Meta Lead ID",
                "Full Name",
                "Phone",
                "Email",
                "City",
                "Campaign Name",
                "Campaign Purpose",
                "Lead Source",
                "Platform",
                "Message Status",
                "Lead Status",
                "Assigned Executive",
                "WhatsApp Opt-In",
                "Opted Out",
                "Created At",
            ]
        )
        for l in filtered:
            writer.writerow(
                [
                    l.id,
                    l.meta_lead_id,
                    l.full_name,
                    l.phone or "",
                    l.email or "",
                    l.city or "",
                    l.campaign_name or "",
                    l.campaign_purpose or "",
                    l.lead_source,
                    l.platform,
                    l.message_status,
                    l.lead_status,
                    l.assigned_executive_name or "Unassigned",
                    "Yes" if l.whatsapp_opt_in else "No",
                    "Yes" if l.opted_out else "No",
                    str(l.created_at),
                ]
            )
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=space_consultant_leads.csv"},
        )

    paginated = filtered[offset : offset + limit]
    return {
        "status": "success",
        "total": len(filtered),
        "data": [l.to_dict() for l in paginated],
    }


@router.get("/{lead_id}")
def get_lead_detail(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    consents = (
        db.query(LeadConsent)
        .filter(LeadConsent.lead_id == lead.id)
        .order_by(LeadConsent.created_at.desc())
        .all()
    )
    outbound_messages = (
        db.query(MessageLog)
        .filter(MessageLog.lead_id == lead.id)
        .order_by(MessageLog.created_at.desc())
        .all()
    )
    inbound_messages = (
        db.query(IncomingMessage)
        .filter(IncomingMessage.lead_id == lead.id)
        .order_by(IncomingMessage.received_at.desc())
        .all()
    )
    followups = (
        db.query(FollowupJob)
        .filter(FollowupJob.lead_id == lead.id)
        .order_by(FollowupJob.step_number.asc())
        .all()
    )
    assignments = (
        db.query(LeadAssignment)
        .filter(LeadAssignment.lead_id == lead.id)
        .order_by(LeadAssignment.created_at.desc())
        .all()
    )

    detail = lead.to_dict()
    detail["consents"] = [c.to_dict() for c in consents]
    detail["outbound_messages"] = [m.to_dict() for m in outbound_messages]
    detail["inbound_messages"] = [i.to_dict() for i in inbound_messages]
    detail["followup_jobs"] = [f.to_dict() for f in followups]
    detail["assignments"] = [a.to_dict() for a in assignments]
    detail["within_24h_service_window"] = doubletick_service.is_within_service_window(lead)

    return {"status": "success", "data": detail}


@router.put("/{lead_id}")
def update_lead(
    lead_id: str,
    req: LeadUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    if req.full_name is not None:
        lead.full_name = req.full_name
    if req.phone is not None:
        lead.phone = normalize_phone_number(req.phone) or req.phone
    if req.email is not None:
        lead.email = req.email
    if req.city is not None:
        lead.city = req.city
    if req.notes is not None:
        lead.notes = req.notes
    if req.whatsapp_opt_in is not None:
        lead.whatsapp_opt_in = req.whatsapp_opt_in
    if req.opted_out is not None:
        lead.opted_out = req.opted_out
        if req.opted_out:
            lead.whatsapp_opt_in = False
            lead.lead_status = "OPTED_OUT"
    if req.automation_paused is not None:
        lead.automation_paused = req.automation_paused
    if req.lead_status is not None:
        lead.lead_status = req.lead_status

    # If lead is converted, opted out, or paused, cancel scheduled follow-up jobs
    if lead.lead_status in ("CONVERTED", "OPTED_OUT") or lead.opted_out or lead.automation_paused:
        pending_jobs = (
            db.query(FollowupJob)
            .filter(
                FollowupJob.lead_id == lead.id,
                FollowupJob.status == "SCHEDULED",
            )
            .all()
        )
        for job in pending_jobs:
            if lead.opted_out or lead.lead_status == "OPTED_OUT":
                job.status = "CANCELLED_OPT_OUT"
                job.cancellation_reason = "Lead marked opted out"
            elif lead.lead_status == "CONVERTED":
                job.status = "CANCELLED_CONVERTED"
                job.cancellation_reason = "Lead marked CONVERTED"
            elif lead.automation_paused:
                job.status = "CANCELLED_PAUSED"
                job.cancellation_reason = "Lead automation paused by staff"

    db.commit()
    db.refresh(lead)

    record_audit_log(
        db=db,
        action="LEAD_UPDATED",
        entity_type="lead",
        entity_id=lead.id,
        actor=current_user,
        details={"lead_status": lead.lead_status, "opted_out": lead.opted_out},
    )

    return {"status": "success", "data": lead.to_dict()}


@router.post("/{lead_id}/assign")
def assign_lead_to_executive(
    lead_id: str,
    req: LeadAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    lead.assigned_executive_id = req.executive_id
    lead.assigned_executive_name = req.executive_name

    assignment = LeadAssignment(
        lead_id=lead.id,
        executive_id=req.executive_id,
        executive_name=req.executive_name,
        assigned_by=current_user.email,
        assignment_notes=req.notes or f"Assigned to {req.executive_name}",
    )
    db.add(assignment)
    db.commit()
    db.refresh(lead)

    record_audit_log(
        db=db,
        action="LEAD_ASSIGNED",
        entity_type="lead",
        entity_id=lead.id,
        actor=current_user,
        details={"executive_name": req.executive_name},
    )

    return {
        "status": "success",
        "message": f"Lead assigned to {req.executive_name}.",
        "data": lead.to_dict(),
    }


@router.post("/{lead_id}/resend")
def resend_lead_whatsapp_message(
    lead_id: str,
    req: Optional[LeadResendRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    if not lead.phone:
        raise HTTPException(status_code=400, detail="Lead does not have a valid phone number.")
    if lead.opted_out or not lead.whatsapp_opt_in:
        raise HTTPException(
            status_code=403,
            detail="Cannot send WhatsApp message: Customer has opted out or lacks WhatsApp consent.",
        )

    automation = None
    if lead.automation_id:
        automation = (
            db.query(CampaignAutomation)
            .filter(CampaignAutomation.id == lead.automation_id)
            .first()
        )
    if not automation and lead.meta_campaign_id:
        automation = (
            db.query(CampaignAutomation)
            .filter(CampaignAutomation.meta_campaign_id == lead.meta_campaign_id)
            .first()
        )

    if not automation:
        raise HTTPException(
            status_code=400,
            detail="No campaign automation is mapped to this lead. Assign a campaign first before resending.",
        )

    res = campaign_service.execute_campaign_automation_for_lead(
        db=db,
        lead=lead,
        automation=automation,
        doubletick_svc=doubletick_service,
    )

    record_audit_log(
        db=db,
        action="LEAD_MESSAGE_RESENT",
        entity_type="lead",
        entity_id=lead.id,
        actor=current_user,
        details=res,
    )

    return {
        "status": "success",
        "message": "WhatsApp template message triggered.",
        "data": res,
    }
