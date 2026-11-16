"""
Campaigns & Campaign-Wise Automation Router (app/routers/campaigns.py)
Endpoints:
- GET /api/campaigns
- POST /api/campaigns
- PUT /api/campaigns/{id}
- DELETE /api/campaigns/{id}
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.database import IntegrityError, Session, get_db
from app.models import (
    Campaign,
    CampaignAutomation,
    Lead,
    LeadForm,
    User,
    utc_now,
)
from app.schemas.api_schemas import CampaignCreateRequest, CampaignUpdateRequest
from app.security.auth import record_audit_log, require_admin, require_staff

router = APIRouter(prefix="/api/campaigns", tags=["Campaign Automation"])


@router.get("")
def list_campaigns(
    purpose: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    automations = db.query(CampaignAutomation).order_by(CampaignAutomation.created_at.desc()).all()
    campaigns_by_id = {c.id: c for c in db.query(Campaign).all()}

    results = []
    for auto in automations:
        if purpose and auto.campaign_purpose != purpose:
            continue
        camp = campaigns_by_id.get(auto.campaign_id)
        camp_status = camp.status if camp else "ACTIVE"
        if status_filter and camp_status != status_filter:
            continue

        lead_count = db.query(Lead).filter(Lead.automation_id == auto.id).count()
        item = auto.to_dict()
        item["status"] = camp_status
        item["description"] = camp.description if camp else ""
        item["leads_count"] = lead_count
        results.append(item)

    return {
        "status": "success",
        "total": len(results),
        "data": results,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_campaign_automation(
    req: CampaignCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    existing = (
        db.query(CampaignAutomation)
        .filter(CampaignAutomation.meta_campaign_id == req.meta_campaign_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Campaign automation with meta_campaign_id '{req.meta_campaign_id}' already exists.",
        )

    camp = Campaign(
        meta_campaign_id=req.meta_campaign_id,
        ad_account_id=req.ad_account_id or "act_1029384756",
        page_id=req.facebook_page_id,
        name=req.name,
        purpose=req.purpose,
        objective="OUTCOME_LEADS",
        status=req.status or "ACTIVE",
        description=req.description or f"Automation for {req.name}",
    )
    db.add(camp)
    db.commit()
    db.refresh(camp)

    if req.lead_form_id:
        existing_form = (
            db.query(LeadForm)
            .filter(LeadForm.meta_form_id == req.lead_form_id)
            .first()
        )
        if not existing_form:
            db.add(
                LeadForm(
                    meta_form_id=req.lead_form_id,
                    page_id=req.facebook_page_id,
                    campaign_id=camp.id,
                    name=f"{req.name} Instant Form",
                    locale="en_US",
                    status="ACTIVE",
                )
            )
            db.commit()

    auto = CampaignAutomation(
        campaign_id=camp.id,
        campaign_name=req.name,
        meta_campaign_id=req.meta_campaign_id,
        facebook_page_id=req.facebook_page_id,
        lead_form_id=req.lead_form_id,
        campaign_purpose=req.purpose,
        whatsapp_template_name=req.whatsapp_template_name,
        template_language=req.template_language or "en",
        template_variables=req.template_variables
        or {
            "placeholders": ["{full_name}", req.name, req.description or req.purpose],
            "details": {"summary": req.description or req.name},
        },
        auto_reply_enabled=req.auto_reply_enabled,
        pdf_brochure_url=req.pdf_brochure_url,
        pdf_filename=req.pdf_filename,
        image_attachment_url=req.image_attachment_url,
        website_url=req.website_url,
        followup_config=req.followup_config
        or {
            "enabled": True,
            "step_2_delay_hours": 24,
            "step_2_template": "hospital_enquiry_followup_24h",
            "step_3_delay_hours": 72,
            "step_3_template": "hospital_enquiry_followup_24h",
        },
        assignment_config=req.assignment_config
        or {"default_executive_name": "Rohit Verma (Hospital M&A Advisor)"},
        campaign_knowledge=req.campaign_knowledge or {},
    )
    db.add(auto)
    db.commit()
    db.refresh(auto)

    record_audit_log(
        db=db,
        action="CAMPAIGN_AUTOMATION_CREATED",
        entity_type="campaign_automation",
        entity_id=auto.id,
        actor=current_user,
        details={
            "campaign_name": auto.campaign_name,
            "meta_campaign_id": auto.meta_campaign_id,
            "whatsapp_template_name": auto.whatsapp_template_name,
        },
    )

    data = auto.to_dict()
    data["status"] = camp.status
    data["leads_count"] = 0
    return {"status": "success", "data": data}


@router.put("/{campaign_auto_id}")
def update_campaign_automation(
    campaign_auto_id: str,
    req: CampaignUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    auto = (
        db.query(CampaignAutomation)
        .filter(CampaignAutomation.id == campaign_auto_id)
        .first()
    )
    if not auto:
        auto = (
            db.query(CampaignAutomation)
            .filter(CampaignAutomation.campaign_id == campaign_auto_id)
            .first()
        )
    if not auto:
        raise HTTPException(status_code=404, detail="Campaign automation not found.")

    camp = db.query(Campaign).filter(Campaign.id == auto.campaign_id).first()

    if req.name is not None:
        auto.campaign_name = req.name
        if camp:
            camp.name = req.name
    if req.meta_campaign_id is not None:
        auto.meta_campaign_id = req.meta_campaign_id
        if camp:
            camp.meta_campaign_id = req.meta_campaign_id
    if req.facebook_page_id is not None:
        auto.facebook_page_id = req.facebook_page_id
        if camp:
            camp.page_id = req.facebook_page_id
    if req.lead_form_id is not None:
        auto.lead_form_id = req.lead_form_id
    if req.purpose is not None:
        auto.campaign_purpose = req.purpose
        if camp:
            camp.purpose = req.purpose
    if req.whatsapp_template_name is not None:
        auto.whatsapp_template_name = req.whatsapp_template_name
    if req.template_language is not None:
        auto.template_language = req.template_language
    if req.template_variables is not None:
        auto.template_variables = req.template_variables
    if req.auto_reply_enabled is not None:
        auto.auto_reply_enabled = req.auto_reply_enabled
    if req.pdf_brochure_url is not None:
        auto.pdf_brochure_url = req.pdf_brochure_url
    if req.pdf_filename is not None:
        auto.pdf_filename = req.pdf_filename
    if req.image_attachment_url is not None:
        auto.image_attachment_url = req.image_attachment_url
    if req.website_url is not None:
        auto.website_url = req.website_url
    if req.followup_config is not None:
        auto.followup_config = req.followup_config
    if req.assignment_config is not None:
        auto.assignment_config = req.assignment_config
    if req.campaign_knowledge is not None:
        auto.campaign_knowledge = req.campaign_knowledge
    if req.status is not None and camp:
        camp.status = req.status
    if req.description is not None and camp:
        camp.description = req.description

    db.commit()
    db.refresh(auto)

    record_audit_log(
        db=db,
        action="CAMPAIGN_AUTOMATION_UPDATED",
        entity_type="campaign_automation",
        entity_id=auto.id,
        actor=current_user,
        details={"campaign_name": auto.campaign_name},
    )

    data = auto.to_dict()
    data["status"] = camp.status if camp else "ACTIVE"
    return {"status": "success", "data": data}


@router.delete("/{campaign_auto_id}")
def delete_campaign_automation(
    campaign_auto_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    auto = (
        db.query(CampaignAutomation)
        .filter(CampaignAutomation.id == campaign_auto_id)
        .first()
    )
    if not auto:
        auto = (
            db.query(CampaignAutomation)
            .filter(CampaignAutomation.campaign_id == campaign_auto_id)
            .first()
        )
    if not auto:
        raise HTTPException(status_code=404, detail="Campaign automation not found.")

    camp_id = auto.campaign_id
    name = auto.campaign_name
    db.delete(auto)
    db.commit()

    record_audit_log(
        db=db,
        action="CAMPAIGN_AUTOMATION_DELETED",
        entity_type="campaign_automation",
        entity_id=campaign_auto_id,
        actor=current_user,
        details={"campaign_name": name, "campaign_id": camp_id},
    )
    return {"status": "success", "message": f"Campaign automation '{name}' deleted."}
