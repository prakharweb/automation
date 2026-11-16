"""Initial Space Consultant Meta Ads + DoubleTick Schema (17 Tables)

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-11-15 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="admin"),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("department", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])

    # 2. meta_accounts
    op.create_table(
        "meta_accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("app_id", sa.String(128), nullable=False, unique=True),
        sa.Column("app_name", sa.String(255), nullable=False),
        sa.Column("business_id", sa.String(128), nullable=True),
        sa.Column("access_token_masked", sa.String(128), nullable=True),
        sa.Column("token_status", sa.String(50), nullable=False, server_default="connected"),
        sa.Column("scopes", sa.JSON(), nullable=True),
        sa.Column("connected_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_meta_accounts_app_id", "meta_accounts", ["app_id"], unique=True)

    # 3. facebook_pages
    op.create_table(
        "facebook_pages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("meta_account_id", sa.String(36), sa.ForeignKey("meta_accounts.id"), nullable=True),
        sa.Column("page_id", sa.String(128), nullable=False, unique=True),
        sa.Column("page_name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(128), nullable=True),
        sa.Column("page_access_token_masked", sa.String(128), nullable=True),
        sa.Column("webhook_subscribed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_facebook_pages_page_id", "facebook_pages", ["page_id"], unique=True)

    # 4. ad_accounts
    op.create_table(
        "ad_accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("meta_account_id", sa.String(36), sa.ForeignKey("meta_accounts.id"), nullable=True),
        sa.Column("ad_account_id", sa.String(128), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("currency", sa.String(16), nullable=False, server_default="INR"),
        sa.Column("timezone_name", sa.String(64), nullable=False, server_default="Asia/Kolkata"),
        sa.Column("account_status", sa.String(50), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ad_accounts_ad_account_id", "ad_accounts", ["ad_account_id"], unique=True)

    # 5. campaigns
    op.create_table(
        "campaigns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("meta_campaign_id", sa.String(128), nullable=False, unique=True),
        sa.Column("ad_account_id", sa.String(128), nullable=True),
        sa.Column("page_id", sa.String(128), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("purpose", sa.String(100), nullable=False),
        sa.Column("objective", sa.String(100), nullable=False, server_default="OUTCOME_LEADS"),
        sa.Column("status", sa.String(50), nullable=False, server_default="ACTIVE"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_campaigns_meta_campaign_id", "campaigns", ["meta_campaign_id"], unique=True)
    op.create_index("ix_campaigns_purpose", "campaigns", ["purpose"])

    # 6. lead_forms
    op.create_table(
        "lead_forms",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("meta_form_id", sa.String(128), nullable=False, unique=True),
        sa.Column("page_id", sa.String(128), nullable=False),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("locale", sa.String(32), nullable=False, server_default="en_US"),
        sa.Column("status", sa.String(50), nullable=False, server_default="ACTIVE"),
        sa.Column("questions_schema", sa.JSON(), nullable=True),
        sa.Column("consent_field_name", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_lead_forms_meta_form_id", "lead_forms", ["meta_form_id"], unique=True)

    # 7. whatsapp_templates
    op.create_table(
        "whatsapp_templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("template_name", sa.String(255), nullable=False, unique=True),
        sa.Column("language", sa.String(32), nullable=False, server_default="en"),
        sa.Column("category", sa.String(64), nullable=False, server_default="UTILITY"),
        sa.Column("purpose", sa.String(100), nullable=False),
        sa.Column("header_type", sa.String(32), nullable=False, server_default="NONE"),
        sa.Column("header_text", sa.String(255), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("footer_text", sa.String(255), nullable=True),
        sa.Column("variables_schema", sa.JSON(), nullable=False),
        sa.Column("buttons_schema", sa.JSON(), nullable=True),
        sa.Column("approval_status", sa.String(50), nullable=False, server_default="APPROVED"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_whatsapp_templates_template_name", "whatsapp_templates", ["template_name"], unique=True)

    # 8. campaign_automations
    op.create_table(
        "campaign_automations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("campaign_name", sa.String(255), nullable=False),
        sa.Column("meta_campaign_id", sa.String(128), nullable=False, unique=True),
        sa.Column("facebook_page_id", sa.String(128), nullable=False),
        sa.Column("lead_form_id", sa.String(128), nullable=True),
        sa.Column("campaign_purpose", sa.String(100), nullable=False),
        sa.Column("whatsapp_template_name", sa.String(255), nullable=False),
        sa.Column("template_language", sa.String(32), nullable=False, server_default="en"),
        sa.Column("template_variables", sa.JSON(), nullable=False),
        sa.Column("auto_reply_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("pdf_brochure_url", sa.String(1024), nullable=True),
        sa.Column("pdf_filename", sa.String(255), nullable=True),
        sa.Column("image_attachment_url", sa.String(1024), nullable=True),
        sa.Column("website_url", sa.String(1024), nullable=True),
        sa.Column("followup_config", sa.JSON(), nullable=False),
        sa.Column("assignment_config", sa.JSON(), nullable=False),
        sa.Column("campaign_knowledge", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_campaign_automations_meta_campaign_id", "campaign_automations", ["meta_campaign_id"], unique=True)
    op.create_index("ix_campaign_automations_lead_form_id", "campaign_automations", ["lead_form_id"])

    # 9. leads
    op.create_table(
        "leads",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("meta_lead_id", sa.String(128), nullable=False, unique=True),
        sa.Column("meta_form_id", sa.String(128), nullable=True),
        sa.Column("meta_ad_id", sa.String(128), nullable=True),
        sa.Column("meta_adgroup_id", sa.String(128), nullable=True),
        sa.Column("meta_campaign_id", sa.String(128), nullable=True),
        sa.Column("meta_page_id", sa.String(128), nullable=True),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id"), nullable=True),
        sa.Column("automation_id", sa.String(36), sa.ForeignKey("campaign_automations.id"), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("city", sa.String(128), nullable=True),
        sa.Column("lead_source", sa.String(64), nullable=False, server_default="meta_instant_form"),
        sa.Column("platform", sa.String(32), nullable=False, server_default="facebook"),
        sa.Column("campaign_name", sa.String(255), nullable=True),
        sa.Column("campaign_purpose", sa.String(100), nullable=True),
        sa.Column("lead_status", sa.String(50), nullable=False, server_default="NEW"),
        sa.Column("message_status", sa.String(50), nullable=False, server_default="PENDING"),
        sa.Column("assigned_executive_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("assigned_executive_name", sa.String(255), nullable=True),
        sa.Column("whatsapp_opt_in", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("opted_out", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("automation_paused", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("has_replied", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_inbound_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("service_window_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_field_data", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("meta_created_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_leads_meta_lead_id", "leads", ["meta_lead_id"], unique=True)
    op.create_index("ix_leads_phone", "leads", ["phone"])
    op.create_index("ix_leads_lead_status", "leads", ["lead_status"])
    op.create_index("ix_leads_message_status", "leads", ["message_status"])
    op.create_index("ix_leads_created_at", "leads", ["created_at"])

    # 10. lead_consents
    op.create_table(
        "lead_consents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("lead_id", sa.String(36), sa.ForeignKey("leads.id"), nullable=False),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("consent_status", sa.String(32), nullable=False, server_default="OPTED_IN"),
        sa.Column("consent_source", sa.String(100), nullable=False),
        sa.Column("consent_text", sa.Text(), nullable=True),
        sa.Column("ip_or_platform", sa.String(100), nullable=True),
        sa.Column("opted_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opted_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_lead_consents_lead_id", "lead_consents", ["lead_id"])
    op.create_index("ix_lead_consents_phone", "lead_consents", ["phone"])

    # 11. message_logs
    op.create_table(
        "message_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("lead_id", sa.String(36), sa.ForeignKey("leads.id"), nullable=True),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id"), nullable=True),
        sa.Column("doubletick_message_id", sa.String(128), nullable=False, unique=True),
        sa.Column("recipient_phone", sa.String(32), nullable=False),
        sa.Column("sender_phone", sa.String(32), nullable=True),
        sa.Column("message_type", sa.String(50), nullable=False),
        sa.Column("template_name", sa.String(255), nullable=True),
        sa.Column("template_language", sa.String(32), nullable=True),
        sa.Column("variables_payload", sa.JSON(), nullable=True),
        sa.Column("content_preview", sa.Text(), nullable=True),
        sa.Column("media_url", sa.String(1024), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_message_logs_doubletick_message_id", "message_logs", ["doubletick_message_id"], unique=True)
    op.create_index("ix_message_logs_lead_id", "message_logs", ["lead_id"])
    op.create_index("ix_message_logs_status", "message_logs", ["status"])

    # 12. incoming_messages
    op.create_table(
        "incoming_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("lead_id", sa.String(36), sa.ForeignKey("leads.id"), nullable=True),
        sa.Column("external_message_id", sa.String(128), nullable=False, unique=True),
        sa.Column("sender_phone", sa.String(32), nullable=False),
        sa.Column("sender_name", sa.String(255), nullable=True),
        sa.Column("message_type", sa.String(50), nullable=False),
        sa.Column("message_text", sa.Text(), nullable=True),
        sa.Column("media_url", sa.String(1024), nullable=True),
        sa.Column("is_opt_out_command", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("ai_reply_generated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("ai_reply_text", sa.Text(), nullable=True),
        sa.Column("escalated_to_human", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_incoming_messages_external_message_id", "incoming_messages", ["external_message_id"], unique=True)

    # 13. webhook_events
    op.create_table(
        "webhook_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("event_id", sa.String(255), nullable=False, unique=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("signature_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("processing_status", sa.String(50), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_webhook_events_event_id", "webhook_events", ["event_id"], unique=True)

    # 14. followup_jobs
    op.create_table(
        "followup_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("lead_id", sa.String(36), sa.ForeignKey("leads.id"), nullable=False),
        sa.Column("automation_id", sa.String(36), sa.ForeignKey("campaign_automations.id"), nullable=True),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("template_name", sa.String(255), nullable=False),
        sa.Column("template_language", sa.String(32), nullable=False, server_default="en"),
        sa.Column("template_variables", sa.JSON(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="SCHEDULED"),
        sa.Column("cancellation_reason", sa.String(255), nullable=True),
        sa.Column("message_log_id", sa.String(36), sa.ForeignKey("message_logs.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_followup_jobs_lead_id", "followup_jobs", ["lead_id"])
    op.create_index("ix_followup_jobs_status", "followup_jobs", ["status"])
    op.create_index("ix_followup_jobs_scheduled_at", "followup_jobs", ["scheduled_at"])

    # 15. lead_assignments
    op.create_table(
        "lead_assignments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("lead_id", sa.String(36), sa.ForeignKey("leads.id"), nullable=False),
        sa.Column("executive_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("executive_name", sa.String(255), nullable=False),
        sa.Column("assigned_by", sa.String(255), nullable=False),
        sa.Column("assignment_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_lead_assignments_lead_id", "lead_assignments", ["lead_id"])

    # 16. system_settings
    op.create_table(
        "system_settings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("setting_key", sa.String(128), nullable=False, unique=True),
        sa.Column("setting_value", sa.JSON(), nullable=False),
        sa.Column("description", sa.String(512), nullable=True),
        sa.Column("updated_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_system_settings_setting_key", "system_settings", ["setting_key"], unique=True)

    # 17. audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("actor_email", sa.String(255), nullable=True),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(128), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    for table in [
        "audit_logs",
        "system_settings",
        "lead_assignments",
        "followup_jobs",
        "webhook_events",
        "incoming_messages",
        "message_logs",
        "lead_consents",
        "leads",
        "campaign_automations",
        "whatsapp_templates",
        "lead_forms",
        "campaigns",
        "ad_accounts",
        "facebook_pages",
        "meta_accounts",
        "users",
    ]:
        op.drop_table(table)
