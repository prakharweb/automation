"""
Meta Integration Router (app/routers/meta.py)
Endpoints:
- GET /api/meta/status
- GET /api/meta/pages
- GET /api/meta/campaigns
- GET /api/meta/forms
- POST /api/meta/connect
- POST /api/meta/simulate-lead (for Setup Wizard Step 6 / end-to-end lead routing test)
"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.database import Session, get_db
from app.models import (
    AdAccount,
    Campaign,
    FacebookPage,
    LeadForm,
    MetaAccount,
    User,
    utc_now,
)
from app.schemas.api_schemas import MetaConnectRequest
from app.security.auth import record_audit_log, require_admin, require_staff
from app.services.lead_service import LeadService
from app.services.meta_service import meta_service
from app.utils.logger import mask_secret

router = APIRouter(prefix="/api/meta", tags=["Meta Integration"])


@router.get("/status")
def get_meta_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    return {
        "status": "success",
        "data": meta_service.get_status(db),
    }


@router.get("/pages")
def get_meta_pages(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    pages = db.query(FacebookPage).order_by(FacebookPage.created_at.desc()).all()
    ad_accounts = db.query(AdAccount).order_by(AdAccount.created_at.desc()).all()
    return {
        "status": "success",
        "data": {
            "pages": [p.to_dict() for p in pages],
            "ad_accounts": [a.to_dict() for a in ad_accounts],
        },
    }


@router.get("/campaigns")
def get_meta_campaigns(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
    return {
        "status": "success",
        "data": [c.to_dict() for c in campaigns],
    }


@router.get("/forms")
def get_meta_forms(
    page_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    q = db.query(LeadForm)
    if page_id:
        q = q.filter(LeadForm.page_id == page_id)
    forms = q.order_by(LeadForm.created_at.desc()).all()
    return {
        "status": "success",
        "data": [f.to_dict() for f in forms],
    }


@router.post("/connect", status_code=status.HTTP_200_OK)
def connect_meta_app(
    req: MetaConnectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    meta_acc = db.query(MetaAccount).filter(MetaAccount.app_id == req.app_id).first()
    masked_token = mask_secret(req.access_token) if req.access_token else "EAAB...connected"

    if not meta_acc:
        meta_acc = MetaAccount(
            app_id=req.app_id,
            app_name=req.app_name or "Space Consultant Meta App",
            business_id=req.business_id,
            access_token_masked=masked_token,
            token_status="connected",
            scopes=meta_service.get_status(db)["required_permissions"],
            connected_by=current_user.id,
            last_synced_at=utc_now(),
        )
        db.add(meta_acc)
        db.commit()
        db.refresh(meta_acc)
    else:
        meta_acc.app_name = req.app_name or meta_acc.app_name
        meta_acc.business_id = req.business_id or meta_acc.business_id
        if req.access_token:
            meta_acc.access_token_masked = masked_token
        meta_acc.token_status = "connected"
        meta_acc.last_synced_at = utc_now()
        db.commit()

    if req.page_id and req.page_name:
        existing_page = db.query(FacebookPage).filter(FacebookPage.page_id == req.page_id).first()
        if not existing_page:
            db.add(
                FacebookPage(
                    meta_account_id=meta_acc.id,
                    page_id=req.page_id,
                    page_name=req.page_name,
                    page_access_token_masked=masked_token,
                    webhook_subscribed=True,
                    is_active=True,
                )
            )
            db.commit()

    if req.ad_account_id:
        existing_ad = db.query(AdAccount).filter(AdAccount.ad_account_id == req.ad_account_id).first()
        if not existing_ad:
            db.add(
                AdAccount(
                    meta_account_id=meta_acc.id,
                    ad_account_id=req.ad_account_id,
                    name=req.ad_account_name or f"Ad Account {req.ad_account_id}",
                    currency="INR",
                    timezone_name="Asia/Kolkata",
                    account_status="ACTIVE",
                )
            )
            db.commit()

    record_audit_log(
        db=db,
        action="META_APP_CONNECTED",
        entity_type="meta_account",
        entity_id=meta_acc.id,
        actor=current_user,
        details={"app_id": req.app_id, "page_id": req.page_id},
    )

    return {
        "status": "success",
        "message": "Meta Developer App and Page configuration saved.",
        "data": meta_acc.to_dict(),
    }


@router.post("/simulate-lead")
def simulate_meta_lead_capture(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Allows administrators to test the full Meta Lead -> Campaign Identification -> PostgreSQL
    -> DoubleTick Template Routing pipeline from the Setup Wizard (Step 6).
    """
    leadgen_id = payload.get("leadgen_id") or f"sim_lead_{uuid.uuid4().hex[:10]}"
    meta_campaign_id = payload.get("meta_campaign_id")
    meta_form_id = payload.get("meta_form_id")
    full_name = payload.get("full_name") or "Dr. Test Applicant"
    phone = payload.get("phone") or "+919876543210"
    email = payload.get("email") or "test.lead@spaceconsultant.in"
    city = payload.get("city") or "Delhi NCR"

    mock_graph = {
        "id": leadgen_id,
        "campaign_id": meta_campaign_id,
        "form_id": meta_form_id,
        "ad_id": payload.get("meta_ad_id") or "ad_sim_1001",
        "platform": payload.get("platform") or "facebook",
        "created_time": utc_now().isoformat(),
        "field_data": [
            {"name": "full_name", "values": [full_name]},
            {"name": "phone_number", "values": [phone]},
            {"name": "email", "values": [email]},
            {"name": "city", "values": [city]},
            {"name": "whatsapp_opt_in", "values": [str(payload.get("whatsapp_opt_in", "true"))]},
        ],
    }

    res = LeadService.process_meta_lead_event(
        db=db,
        change_value={
            "leadgen_id": leadgen_id,
            "campaign_id": meta_campaign_id,
            "form_id": meta_form_id,
            "page_id": payload.get("page_id") or "104928374650192",
        },
        mock_graph_lead=mock_graph,
    )
    return {"status": "success", "data": res}
