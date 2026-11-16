"""
Normalized Database Models (app/models/entities.py)
Defines all 17 required tables for Space Consultant Meta Ads + DoubleTick Automation Platform:
1. users
2. meta_accounts
3. facebook_pages
4. ad_accounts
5. campaigns
6. lead_forms
7. campaign_automations
8. leads
9. lead_consents
10. whatsapp_templates
11. message_logs
12. incoming_messages
13. webhook_events
14. followup_jobs
15. lead_assignments
16. system_settings
17. audit_logs
"""
import uuid
from datetime import datetime, timezone
from app.database import (
    Base,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="admin", index=True)  # admin, manager, executive
    phone = Column(String(30), nullable=True)
    department = Column(String(100), nullable=True, default="Consultancy")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class MetaAccount(Base):
    __tablename__ = "meta_accounts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    app_id = Column(String(128), unique=True, nullable=False, index=True)
    app_name = Column(String(255), nullable=False, default="Space Consultant Meta App")
    business_id = Column(String(128), nullable=True)
    access_token_masked = Column(String(128), nullable=True)
    token_status = Column(String(50), nullable=False, default="connected")  # connected, expired, disconnected
    scopes = Column(JSON, nullable=True, default=list)
    connected_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class FacebookPage(Base):
    __tablename__ = "facebook_pages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    meta_account_id = Column(String(36), ForeignKey("meta_accounts.id"), nullable=True, index=True)
    page_id = Column(String(128), unique=True, nullable=False, index=True)
    page_name = Column(String(255), nullable=False)
    category = Column(String(128), nullable=True, default="Medical & Health / Real Estate Consultant")
    page_access_token_masked = Column(String(128), nullable=True)
    webhook_subscribed = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class AdAccount(Base):
    __tablename__ = "ad_accounts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    meta_account_id = Column(String(36), ForeignKey("meta_accounts.id"), nullable=True, index=True)
    ad_account_id = Column(String(128), unique=True, nullable=False, index=True)  # e.g. act_1029384756
    name = Column(String(255), nullable=False)
    currency = Column(String(16), nullable=False, default="INR")
    timezone_name = Column(String(64), nullable=False, default="Asia/Kolkata")
    account_status = Column(String(50), nullable=False, default="ACTIVE")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    meta_campaign_id = Column(String(128), unique=True, nullable=False, index=True)
    ad_account_id = Column(String(128), nullable=True, index=True)
    page_id = Column(String(128), nullable=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    purpose = Column(String(100), nullable=False, index=True)
    # e.g. hospital_for_sale, doctor_recruitment, healthcare_recruitment, hospital_property, real_estate
    objective = Column(String(100), nullable=False, default="OUTCOME_LEADS")
    status = Column(String(50), nullable=False, default="ACTIVE", index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class LeadForm(Base):
    __tablename__ = "lead_forms"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    meta_form_id = Column(String(128), unique=True, nullable=False, index=True)
    page_id = Column(String(128), nullable=False, index=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    locale = Column(String(32), nullable=False, default="en_US")
    status = Column(String(50), nullable=False, default="ACTIVE")
    questions_schema = Column(JSON, nullable=True, default=list)
    consent_field_name = Column(String(128), nullable=True, default="whatsapp_opt_in")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class WhatsAppTemplate(Base):
    __tablename__ = "whatsapp_templates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    template_name = Column(String(255), unique=True, nullable=False, index=True)
    language = Column(String(32), nullable=False, default="en")
    category = Column(String(64), nullable=False, default="UTILITY")  # UTILITY, MARKETING
    purpose = Column(String(100), nullable=False, index=True)
    header_type = Column(String(32), nullable=False, default="NONE")  # NONE, TEXT, IMAGE, DOCUMENT
    header_text = Column(String(255), nullable=True)
    body_text = Column(Text, nullable=False)
    footer_text = Column(String(255), nullable=True)
    variables_schema = Column(JSON, nullable=False, default=list)  # e.g. ["full_name", "campaign_title"]
    buttons_schema = Column(JSON, nullable=True, default=list)
    approval_status = Column(String(50), nullable=False, default="APPROVED", index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class CampaignAutomation(Base):
    __tablename__ = "campaign_automations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=False, index=True)
    campaign_name = Column(String(255), nullable=False)
    meta_campaign_id = Column(String(128), unique=True, nullable=False, index=True)
    facebook_page_id = Column(String(128), nullable=False, index=True)
    lead_form_id = Column(String(128), nullable=True, index=True)
    campaign_purpose = Column(String(100), nullable=False, index=True)
    whatsapp_template_name = Column(String(255), nullable=False, index=True)
    template_language = Column(String(32), nullable=False, default="en")
    template_variables = Column(JSON, nullable=False, default=dict)
    # e.g. {"placeholders": ["{full_name}", "100-Bed Multispeciality Hospital in Delhi NCR"], "details": {...}}
    auto_reply_enabled = Column(Boolean, nullable=False, default=True, index=True)
    pdf_brochure_url = Column(String(1024), nullable=True)
    pdf_filename = Column(String(255), nullable=True)
    image_attachment_url = Column(String(1024), nullable=True)
    website_url = Column(String(1024), nullable=True)
    followup_config = Column(JSON, nullable=False, default=dict)
    # e.g. {"enabled": True, "step_2_delay_hours": 24, "step_2_template": "...", "step_3_delay_hours": 72, "step_3_template": "..."}
    assignment_config = Column(JSON, nullable=False, default=dict)
    # e.g. {"default_executive_id": "...", "default_executive_name": "Rohit Verma", "strategy": "round_robin"}
    campaign_knowledge = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class Lead(Base):
    __tablename__ = "leads"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    meta_lead_id = Column(String(128), unique=True, nullable=False, index=True)
    meta_form_id = Column(String(128), nullable=True, index=True)
    meta_ad_id = Column(String(128), nullable=True, index=True)
    meta_adgroup_id = Column(String(128), nullable=True)
    meta_campaign_id = Column(String(128), nullable=True, index=True)
    meta_page_id = Column(String(128), nullable=True, index=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=True, index=True)
    automation_id = Column(String(36), ForeignKey("campaign_automations.id"), nullable=True, index=True)

    full_name = Column(String(255), nullable=False, default="Unknown Lead", index=True)
    phone = Column(String(32), nullable=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    city = Column(String(128), nullable=True)
    lead_source = Column(String(64), nullable=False, default="meta_instant_form", index=True)
    platform = Column(String(32), nullable=False, default="facebook")  # facebook, instagram
    campaign_name = Column(String(255), nullable=True)
    campaign_purpose = Column(String(100), nullable=True, index=True)

    lead_status = Column(String(50), nullable=False, default="NEW", index=True)
    # NEW, CONTACTED, INTERESTED, QUALIFIED, MANUAL_REVIEW, CONVERTED, OPTED_OUT, INVALID_PHONE
    message_status = Column(String(50), nullable=False, default="PENDING", index=True)
    # PENDING, SENT, DELIVERED, READ, FAILED, PAUSED, SKIPPED_NO_CONSENT, MANUAL_REVIEW
    assigned_executive_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    assigned_executive_name = Column(String(255), nullable=True)

    whatsapp_opt_in = Column(Boolean, nullable=False, default=True)
    opted_out = Column(Boolean, nullable=False, default=False, index=True)
    automation_paused = Column(Boolean, nullable=False, default=False)
    has_replied = Column(Boolean, nullable=False, default=False, index=True)
    last_inbound_at = Column(DateTime(timezone=True), nullable=True)
    service_window_expires_at = Column(DateTime(timezone=True), nullable=True)

    raw_field_data = Column(JSON, nullable=True, default=dict)
    notes = Column(Text, nullable=True)
    meta_created_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class LeadConsent(Base):
    __tablename__ = "lead_consents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    lead_id = Column(String(36), ForeignKey("leads.id"), nullable=False, index=True)
    phone = Column(String(32), nullable=False, index=True)
    consent_status = Column(String(32), nullable=False, default="OPTED_IN", index=True)
    # OPTED_IN, OPTED_OUT, INFERRED_INQUIRY, REVOKED
    consent_source = Column(String(100), nullable=False, default="meta_lead_form_disclaimer")
    consent_text = Column(Text, nullable=True)
    ip_or_platform = Column(String(100), nullable=True, default="Meta Instant Form")
    opted_in_at = Column(DateTime(timezone=True), nullable=True, default=utc_now)
    opted_out_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class MessageLog(Base):
    __tablename__ = "message_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    lead_id = Column(String(36), ForeignKey("leads.id"), nullable=True, index=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id"), nullable=True, index=True)
    doubletick_message_id = Column(String(128), unique=True, nullable=False, index=True)
    recipient_phone = Column(String(32), nullable=False, index=True)
    sender_phone = Column(String(32), nullable=True)
    message_type = Column(String(50), nullable=False, default="TEMPLATE", index=True)
    # TEMPLATE, TEXT, DOCUMENT, IMAGE, AI_REPLY
    template_name = Column(String(255), nullable=True, index=True)
    template_language = Column(String(32), nullable=True, default="en")
    variables_payload = Column(JSON, nullable=True, default=dict)
    content_preview = Column(Text, nullable=True)
    media_url = Column(String(1024), nullable=True)
    status = Column(String(50), nullable=False, default="SENT", index=True)
    # QUEUED, SENT, DELIVERED, READ, FAILED
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True, default=utc_now)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class IncomingMessage(Base):
    __tablename__ = "incoming_messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    lead_id = Column(String(36), ForeignKey("leads.id"), nullable=True, index=True)
    external_message_id = Column(String(128), unique=True, nullable=False, index=True)
    sender_phone = Column(String(32), nullable=False, index=True)
    sender_name = Column(String(255), nullable=True)
    message_type = Column(String(50), nullable=False, default="TEXT")
    message_text = Column(Text, nullable=True)
    media_url = Column(String(1024), nullable=True)
    is_opt_out_command = Column(Boolean, nullable=False, default=False)
    ai_reply_generated = Column(Boolean, nullable=False, default=False)
    ai_reply_text = Column(Text, nullable=True)
    escalated_to_human = Column(Boolean, nullable=False, default=False)
    raw_payload = Column(JSON, nullable=True, default=dict)
    received_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    provider = Column(String(50), nullable=False, index=True)  # meta, doubletick
    event_id = Column(String(255), unique=True, nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    signature_verified = Column(Boolean, nullable=False, default=False)
    processing_status = Column(String(50), nullable=False, default="PROCESSED", index=True)
    # RECEIVED, PROCESSED, DUPLICATE, FAILED, REJECTED
    payload = Column(JSON, nullable=True, default=dict)
    error_detail = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class FollowupJob(Base):
    __tablename__ = "followup_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    lead_id = Column(String(36), ForeignKey("leads.id"), nullable=False, index=True)
    automation_id = Column(String(36), ForeignKey("campaign_automations.id"), nullable=True, index=True)
    step_number = Column(Integer, nullable=False, default=2, index=True)  # 2 = 24h follow-up, 3 = final follow-up
    template_name = Column(String(255), nullable=False)
    template_language = Column(String(32), nullable=False, default="en")
    template_variables = Column(JSON, nullable=True, default=dict)
    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False, default="SCHEDULED", index=True)
    # SCHEDULED, COMPLETED, CANCELLED_REPLIED, CANCELLED_CONVERTED, CANCELLED_OPT_OUT, CANCELLED_PAUSED, FAILED
    cancellation_reason = Column(String(255), nullable=True)
    message_log_id = Column(String(36), ForeignKey("message_logs.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class LeadAssignment(Base):
    __tablename__ = "lead_assignments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    lead_id = Column(String(36), ForeignKey("leads.id"), nullable=False, index=True)
    executive_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    executive_name = Column(String(255), nullable=False)
    assigned_by = Column(String(255), nullable=False, default="system_automation")
    assignment_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    setting_key = Column(String(128), unique=True, nullable=False, index=True)
    setting_value = Column(JSON, nullable=False, default=dict)
    description = Column(String(512), nullable=True)
    updated_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    actor_id = Column(String(36), nullable=True, index=True)
    actor_email = Column(String(255), nullable=True, index=True)
    action = Column(String(128), nullable=False, index=True)
    entity_type = Column(String(64), nullable=False, index=True)
    entity_id = Column(String(128), nullable=True, index=True)
    details = Column(JSON, nullable=True, default=dict)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
