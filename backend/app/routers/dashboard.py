"""
Dashboard, Health, Authentication, Settings & Admin Users Router (app/routers/dashboard.py)
Endpoints:
- GET /api/health
- GET /api/dashboard/stats
- POST /api/auth/login
- GET /api/auth/me
- GET /api/users
- POST /api/users
- PUT /api/users/{id}
- GET /api/settings
- PUT /api/settings
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status

from app.config import settings
from app.database import Session, get_db
from app.models import (
    AuditLog,
    CampaignAutomation,
    FollowupJob,
    IncomingMessage,
    Lead,
    MessageLog,
    SystemSetting,
    User,
    WebhookEvent,
    utc_now,
)
from app.schemas.api_schemas import (
    LoginRequest,
    SystemSettingUpdateRequest,
    UserCreateRequest,
    UserUpdateRequest,
)
from app.security.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    record_audit_log,
    require_admin,
    require_staff,
    verify_password,
)
from app.services.doubletick_service import doubletick_service
from app.services.meta_service import meta_service

router = APIRouter(tags=["Dashboard, Auth & Admin"])


@router.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    try:
        user_count = db.query(User).count()
        db_ok = True
    except Exception:
        user_count = 0
        db_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "database_connected": db_ok,
        "registered_users": user_count,
        "timestamp": utc_now().isoformat(),
    }


@router.post("/api/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.strip().lower()).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled.",
        )

    token = create_access_token(user_id=user.id, email=user.email, role=user.role)
    record_audit_log(
        db=db,
        action="USER_LOGIN",
        entity_type="user",
        entity_id=user.id,
        actor=user,
        details={"role": user.role},
    )

    user_dict = user.to_dict()
    user_dict.pop("hashed_password", None)
    return {
        "status": "success",
        "access_token": token,
        "token_type": "bearer",
        "user": user_dict,
    }


@router.get("/api/auth/me")
def get_me(current_user: User = Depends(get_current_user)):
    u = current_user.to_dict()
    u.pop("hashed_password", None)
    return {"status": "success", "data": u}


@router.get("/api/dashboard/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    all_leads = db.query(Lead).all()
    all_messages = db.query(MessageLog).all()
    today_prefix = utc_now().strftime("%Y-%m-%d")

    total_leads = len(all_leads)
    todays_leads = sum(
        1 for l in all_leads if l.created_at and str(l.created_at).startswith(today_prefix)
    )

    messages_sent = len(all_messages)
    messages_delivered = sum(1 for m in all_messages if m.status in ("DELIVERED", "READ"))
    messages_read = sum(1 for m in all_messages if m.status == "READ")
    failed_messages = sum(1 for m in all_messages if m.status == "FAILED")

    interested_leads = sum(1 for l in all_leads if l.lead_status in ("INTERESTED", "QUALIFIED"))
    converted_leads = sum(1 for l in all_leads if l.lead_status == "CONVERTED")
    manual_review_leads = sum(1 for l in all_leads if l.lead_status == "MANUAL_REVIEW")
    opted_out_leads = sum(1 for l in all_leads if l.opted_out or l.lead_status == "OPTED_OUT")

    # Campaign-wise breakdown
    automations = db.query(CampaignAutomation).all()
    campaign_breakdown = []
    for auto in automations:
        c_leads = [l for l in all_leads if l.automation_id == auto.id or l.meta_campaign_id == auto.meta_campaign_id]
        campaign_breakdown.append(
            {
                "id": auto.id,
                "campaign_name": auto.campaign_name,
                "meta_campaign_id": auto.meta_campaign_id,
                "purpose": auto.campaign_purpose,
                "template_name": auto.whatsapp_template_name,
                "auto_reply_enabled": auto.auto_reply_enabled,
                "total_leads": len(c_leads),
                "interested_leads": sum(1 for l in c_leads if l.lead_status == "INTERESTED"),
                "converted_leads": sum(1 for l in c_leads if l.lead_status == "CONVERTED"),
            }
        )

    recent_leads = [
        l.to_dict()
        for l in sorted(
            all_leads,
            key=lambda x: str(x.created_at or ""),
            reverse=True,
        )[:8]
    ]

    scheduled_followups = db.query(FollowupJob).filter(FollowupJob.status == "SCHEDULED").count()
    inbound_count = db.query(IncomingMessage).count()

    return {
        "status": "success",
        "data": {
            "overview": {
                "total_leads": total_leads,
                "todays_leads": todays_leads,
                "messages_sent": messages_sent,
                "messages_delivered": messages_delivered,
                "messages_read": messages_read,
                "failed_messages": failed_messages,
                "interested_leads": interested_leads,
                "converted_leads": converted_leads,
                "manual_review_leads": manual_review_leads,
                "opted_out_leads": opted_out_leads,
                "scheduled_followups": scheduled_followups,
                "incoming_replies": inbound_count,
            },
            "campaign_breakdown": campaign_breakdown,
            "recent_leads": recent_leads,
            "integrations": {
                "meta": meta_service.get_status(db),
                "doubletick": doubletick_service.get_status(),
            },
        },
    }


# --- ADMIN USERS MANAGEMENT ---
@router.get("/api/users")
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    users = db.query(User).order_by(User.created_at.asc()).all()
    sanitized = []
    for u in users:
        d = u.to_dict()
        d.pop("hashed_password", None)
        sanitized.append(d)
    return {"status": "success", "data": sanitized}


@router.post("/api/users", status_code=status.HTTP_201_CREATED)
def create_user(
    req: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    email_clean = req.email.strip().lower()
    existing = db.query(User).filter(User.email == email_clean).first()
    if existing:
        raise HTTPException(status_code=409, detail="A user with this email already exists.")

    new_user = User(
        email=email_clean,
        full_name=req.full_name,
        hashed_password=hash_password(req.password),
        role=req.role if req.role in ("admin", "manager", "executive") else "executive",
        phone=req.phone,
        department=req.department,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    record_audit_log(
        db=db,
        action="USER_CREATED",
        entity_type="user",
        entity_id=new_user.id,
        actor=current_user,
        details={"email": new_user.email, "role": new_user.role},
    )

    d = new_user.to_dict()
    d.pop("hashed_password", None)
    return {"status": "success", "data": d}


@router.put("/api/users/{user_id}")
def update_user(
    user_id: str,
    req: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if req.full_name is not None:
        user.full_name = req.full_name
    if req.role is not None and req.role in ("admin", "manager", "executive"):
        user.role = req.role
    if req.phone is not None:
        user.phone = req.phone
    if req.department is not None:
        user.department = req.department
    if req.is_active is not None:
        user.is_active = req.is_active

    db.commit()
    db.refresh(user)
    d = user.to_dict()
    d.pop("hashed_password", None)
    return {"status": "success", "data": d}


# --- SYSTEM SETTINGS & AUDIT LOGS ---
@router.get("/api/settings")
def get_system_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    settings_rows = db.query(SystemSetting).all()
    audit_rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(30).all()
    webhook_rows = db.query(WebhookEvent).order_by(WebhookEvent.created_at.desc()).limit(30).all()

    settings_map = {r.setting_key: r.setting_value for r in settings_rows}
    return {
        "status": "success",
        "data": {
            "settings": settings_map,
            "audit_logs": [a.to_dict() for a in audit_rows],
            "recent_webhooks": [w.to_dict() for w in webhook_rows],
        },
    }


@router.put("/api/settings")
def update_system_settings(
    req: SystemSettingUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    for key, val in req.settings.items():
        row = db.query(SystemSetting).filter(SystemSetting.setting_key == key).first()
        if row:
            row.setting_value = val
            row.updated_by = current_user.email
        else:
            db.add(
                SystemSetting(
                    setting_key=key,
                    setting_value=val,
                    updated_by=current_user.email,
                )
            )
    db.commit()

    record_audit_log(
        db=db,
        action="SYSTEM_SETTINGS_UPDATED",
        entity_type="system_setting",
        actor=current_user,
        details={"keys": list(req.settings.keys())},
    )
    return {"status": "success", "message": "System settings updated."}
