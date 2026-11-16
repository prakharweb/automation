-- ============================================================================
-- Space Consultant – Meta Ads + DoubleTick Lead Automation Platform
-- Normalized PostgreSQL Schema (17 Tables) - Neon PostgreSQL Compatible
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'admin',
    phone VARCHAR(30),
    department VARCHAR(100) DEFAULT 'Consultancy',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
CREATE INDEX IF NOT EXISTS ix_users_role ON users(role);

CREATE TABLE IF NOT EXISTS meta_accounts (
    id VARCHAR(36) PRIMARY KEY,
    app_id VARCHAR(128) UNIQUE NOT NULL,
    app_name VARCHAR(255) NOT NULL,
    business_id VARCHAR(128),
    access_token_masked VARCHAR(128),
    token_status VARCHAR(50) NOT NULL DEFAULT 'connected',
    scopes JSONB DEFAULT '[]'::jsonb,
    connected_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS facebook_pages (
    id VARCHAR(36) PRIMARY KEY,
    meta_account_id VARCHAR(36) REFERENCES meta_accounts(id) ON DELETE CASCADE,
    page_id VARCHAR(128) UNIQUE NOT NULL,
    page_name VARCHAR(255) NOT NULL,
    category VARCHAR(128),
    page_access_token_masked VARCHAR(128),
    webhook_subscribed BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_facebook_pages_page_id ON facebook_pages(page_id);

CREATE TABLE IF NOT EXISTS ad_accounts (
    id VARCHAR(36) PRIMARY KEY,
    meta_account_id VARCHAR(36) REFERENCES meta_accounts(id) ON DELETE CASCADE,
    ad_account_id VARCHAR(128) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    currency VARCHAR(16) NOT NULL DEFAULT 'INR',
    timezone_name VARCHAR(64) NOT NULL DEFAULT 'Asia/Kolkata',
    account_status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS campaigns (
    id VARCHAR(36) PRIMARY KEY,
    meta_campaign_id VARCHAR(128) UNIQUE NOT NULL,
    ad_account_id VARCHAR(128),
    page_id VARCHAR(128),
    name VARCHAR(255) NOT NULL,
    purpose VARCHAR(100) NOT NULL,
    objective VARCHAR(100) NOT NULL DEFAULT 'OUTCOME_LEADS',
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_campaigns_meta_campaign_id ON campaigns(meta_campaign_id);
CREATE INDEX IF NOT EXISTS ix_campaigns_purpose ON campaigns(purpose);

CREATE TABLE IF NOT EXISTS lead_forms (
    id VARCHAR(36) PRIMARY KEY,
    meta_form_id VARCHAR(128) UNIQUE NOT NULL,
    page_id VARCHAR(128) NOT NULL,
    campaign_id VARCHAR(36) REFERENCES campaigns(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    locale VARCHAR(32) NOT NULL DEFAULT 'en_US',
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    questions_schema JSONB DEFAULT '[]'::jsonb,
    consent_field_name VARCHAR(128) DEFAULT 'whatsapp_opt_in',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_lead_forms_meta_form_id ON lead_forms(meta_form_id);

CREATE TABLE IF NOT EXISTS whatsapp_templates (
    id VARCHAR(36) PRIMARY KEY,
    template_name VARCHAR(255) UNIQUE NOT NULL,
    language VARCHAR(32) NOT NULL DEFAULT 'en',
    category VARCHAR(64) NOT NULL DEFAULT 'UTILITY',
    purpose VARCHAR(100) NOT NULL,
    header_type VARCHAR(32) NOT NULL DEFAULT 'NONE',
    header_text VARCHAR(255),
    body_text TEXT NOT NULL,
    footer_text VARCHAR(255),
    variables_schema JSONB NOT NULL DEFAULT '[]'::jsonb,
    buttons_schema JSONB DEFAULT '[]'::jsonb,
    approval_status VARCHAR(50) NOT NULL DEFAULT 'APPROVED',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_whatsapp_templates_template_name ON whatsapp_templates(template_name);

CREATE TABLE IF NOT EXISTS campaign_automations (
    id VARCHAR(36) PRIMARY KEY,
    campaign_id VARCHAR(36) NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    campaign_name VARCHAR(255) NOT NULL,
    meta_campaign_id VARCHAR(128) UNIQUE NOT NULL,
    facebook_page_id VARCHAR(128) NOT NULL,
    lead_form_id VARCHAR(128),
    campaign_purpose VARCHAR(100) NOT NULL,
    whatsapp_template_name VARCHAR(255) NOT NULL,
    template_language VARCHAR(32) NOT NULL DEFAULT 'en',
    template_variables JSONB NOT NULL DEFAULT '{}'::jsonb,
    auto_reply_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    pdf_brochure_url VARCHAR(1024),
    pdf_filename VARCHAR(255),
    image_attachment_url VARCHAR(1024),
    website_url VARCHAR(1024),
    followup_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    assignment_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    campaign_knowledge JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_campaign_automations_meta_campaign_id ON campaign_automations(meta_campaign_id);
CREATE INDEX IF NOT EXISTS ix_campaign_automations_lead_form_id ON campaign_automations(lead_form_id);

CREATE TABLE IF NOT EXISTS leads (
    id VARCHAR(36) PRIMARY KEY,
    meta_lead_id VARCHAR(128) UNIQUE NOT NULL,
    meta_form_id VARCHAR(128),
    meta_ad_id VARCHAR(128),
    meta_adgroup_id VARCHAR(128),
    meta_campaign_id VARCHAR(128),
    meta_page_id VARCHAR(128),
    campaign_id VARCHAR(36) REFERENCES campaigns(id) ON DELETE SET NULL,
    automation_id VARCHAR(36) REFERENCES campaign_automations(id) ON DELETE SET NULL,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(32),
    email VARCHAR(255),
    city VARCHAR(128),
    lead_source VARCHAR(64) NOT NULL DEFAULT 'meta_instant_form',
    platform VARCHAR(32) NOT NULL DEFAULT 'facebook',
    campaign_name VARCHAR(255),
    campaign_purpose VARCHAR(100),
    lead_status VARCHAR(50) NOT NULL DEFAULT 'NEW',
    message_status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    assigned_executive_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    assigned_executive_name VARCHAR(255),
    whatsapp_opt_in BOOLEAN NOT NULL DEFAULT TRUE,
    opted_out BOOLEAN NOT NULL DEFAULT FALSE,
    automation_paused BOOLEAN NOT NULL DEFAULT FALSE,
    has_replied BOOLEAN NOT NULL DEFAULT FALSE,
    last_inbound_at TIMESTAMPTZ,
    service_window_expires_at TIMESTAMPTZ,
    raw_field_data JSONB DEFAULT '{}'::jsonb,
    notes TEXT,
    meta_created_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_leads_meta_lead_id ON leads(meta_lead_id);
CREATE INDEX IF NOT EXISTS ix_leads_phone ON leads(phone);
CREATE INDEX IF NOT EXISTS ix_leads_lead_status ON leads(lead_status);
CREATE INDEX IF NOT EXISTS ix_leads_message_status ON leads(message_status);
CREATE INDEX IF NOT EXISTS ix_leads_created_at ON leads(created_at);

CREATE TABLE IF NOT EXISTS lead_consents (
    id VARCHAR(36) PRIMARY KEY,
    lead_id VARCHAR(36) NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    phone VARCHAR(32) NOT NULL,
    consent_status VARCHAR(32) NOT NULL DEFAULT 'OPTED_IN',
    consent_source VARCHAR(100) NOT NULL,
    consent_text TEXT,
    ip_or_platform VARCHAR(100),
    opted_in_at TIMESTAMPTZ DEFAULT NOW(),
    opted_out_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_lead_consents_lead_id ON lead_consents(lead_id);

CREATE TABLE IF NOT EXISTS message_logs (
    id VARCHAR(36) PRIMARY KEY,
    lead_id VARCHAR(36) REFERENCES leads(id) ON DELETE SET NULL,
    campaign_id VARCHAR(36) REFERENCES campaigns(id) ON DELETE SET NULL,
    doubletick_message_id VARCHAR(128) UNIQUE NOT NULL,
    recipient_phone VARCHAR(32) NOT NULL,
    sender_phone VARCHAR(32),
    message_type VARCHAR(50) NOT NULL DEFAULT 'TEMPLATE',
    template_name VARCHAR(255),
    template_language VARCHAR(32) DEFAULT 'en',
    variables_payload JSONB DEFAULT '{}'::jsonb,
    content_preview TEXT,
    media_url VARCHAR(1024),
    status VARCHAR(50) NOT NULL DEFAULT 'SENT',
    error_message TEXT,
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_message_logs_doubletick_message_id ON message_logs(doubletick_message_id);
CREATE INDEX IF NOT EXISTS ix_message_logs_lead_id ON message_logs(lead_id);
CREATE INDEX IF NOT EXISTS ix_message_logs_status ON message_logs(status);

CREATE TABLE IF NOT EXISTS incoming_messages (
    id VARCHAR(36) PRIMARY KEY,
    lead_id VARCHAR(36) REFERENCES leads(id) ON DELETE SET NULL,
    external_message_id VARCHAR(128) UNIQUE NOT NULL,
    sender_phone VARCHAR(32) NOT NULL,
    sender_name VARCHAR(255),
    message_type VARCHAR(50) NOT NULL DEFAULT 'TEXT',
    message_text TEXT,
    media_url VARCHAR(1024),
    is_opt_out_command BOOLEAN NOT NULL DEFAULT FALSE,
    ai_reply_generated BOOLEAN NOT NULL DEFAULT FALSE,
    ai_reply_text TEXT,
    escalated_to_human BOOLEAN NOT NULL DEFAULT FALSE,
    raw_payload JSONB DEFAULT '{}'::jsonb,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_incoming_messages_external_message_id ON incoming_messages(external_message_id);

CREATE TABLE IF NOT EXISTS webhook_events (
    id VARCHAR(36) PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    event_id VARCHAR(255) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    signature_verified BOOLEAN NOT NULL DEFAULT FALSE,
    processing_status VARCHAR(50) NOT NULL DEFAULT 'PROCESSED',
    payload JSONB DEFAULT '{}'::jsonb,
    error_detail TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_webhook_events_event_id ON webhook_events(event_id);

CREATE TABLE IF NOT EXISTS followup_jobs (
    id VARCHAR(36) PRIMARY KEY,
    lead_id VARCHAR(36) NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    automation_id VARCHAR(36) REFERENCES campaign_automations(id) ON DELETE SET NULL,
    step_number INTEGER NOT NULL DEFAULT 2,
    template_name VARCHAR(255) NOT NULL,
    template_language VARCHAR(32) NOT NULL DEFAULT 'en',
    template_variables JSONB DEFAULT '{}'::jsonb,
    scheduled_at TIMESTAMPTZ NOT NULL,
    executed_at TIMESTAMPTZ,
    status VARCHAR(50) NOT NULL DEFAULT 'SCHEDULED',
    cancellation_reason VARCHAR(255),
    message_log_id VARCHAR(36) REFERENCES message_logs(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_followup_jobs_lead_id ON followup_jobs(lead_id);
CREATE INDEX IF NOT EXISTS ix_followup_jobs_status ON followup_jobs(status);
CREATE INDEX IF NOT EXISTS ix_followup_jobs_scheduled_at ON followup_jobs(scheduled_at);

CREATE TABLE IF NOT EXISTS lead_assignments (
    id VARCHAR(36) PRIMARY KEY,
    lead_id VARCHAR(36) NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    executive_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    executive_name VARCHAR(255) NOT NULL,
    assigned_by VARCHAR(255) NOT NULL,
    assignment_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_lead_assignments_lead_id ON lead_assignments(lead_id);

CREATE TABLE IF NOT EXISTS system_settings (
    id VARCHAR(36) PRIMARY KEY,
    setting_key VARCHAR(128) UNIQUE NOT NULL,
    setting_value JSONB NOT NULL DEFAULT '{}'::jsonb,
    description VARCHAR(512),
    updated_by VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    actor_id VARCHAR(36),
    actor_email VARCHAR(255),
    action VARCHAR(128) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(128),
    details JSONB DEFAULT '{}'::jsonb,
    ip_address VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at);
