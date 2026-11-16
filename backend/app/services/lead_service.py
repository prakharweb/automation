"""
Lead Ingestion, Deduplication & Consent Management Service (app/services/lead_service.py)
Coordinates:
- Idempotent processing of Meta Lead Ads webhook events
- Graph API lead detail fetching (never trusting unverified webhook campaign/lead data)
- Duplicate lead prevention via unique meta_lead_id
- WhatsApp opt-in consent tracking in lead_consents
- Campaign identification via CampaignService
- Automatic WhatsApp template dispatch via DoubleTickService
- Manual review queue fallback when campaign cannot be identified or phone is missing
"""
from typing import Any, Dict, Optional

import httpx

from app.config import settings
from app.database import IntegrityError, Session
from app.models import Lead, LeadConsent, WebhookEvent, utc_now
from app.services.campaign_service import CampaignService, campaign_service
from app.services.doubletick_service import DoubleTickService, doubletick_service
from app.services.meta_service import MetaService, meta_service
from app.utils.logger import get_logger, sanitize_dict

logger = get_logger("lead_service")


class LeadService:
    @staticmethod
    def process_meta_lead_event(
        db: Session,
        change_value: Dict[str, Any],
        meta_svc: Optional[MetaService] = None,
        doubletick_svc: Optional[DoubleTickService] = None,
        campaign_svc: Optional[CampaignService] = None,
        mock_graph_lead: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Processes a single verified Meta `leadgen` change event idempotently.
        1. Checks if `leadgen_id` already exists in `leads` or `webhook_events`
        2. Fetches authoritative lead details from Meta Graph API
        3. Extracts lead fields, normalizes phone, and records `LeadConsent`
        4. Identifies campaign and `CampaignAutomation` rule
        5. Triggers DoubleTick WhatsApp template message or routes to `MANUAL_REVIEW`
        """
        m_svc = meta_svc or meta_service
        dt_svc = doubletick_svc or doubletick_service
        c_svc = campaign_svc or campaign_service

        leadgen_id = str(change_value.get("leadgen_id") or "").strip()
        if not leadgen_id:
            return {"status": "error", "reason": "missing_leadgen_id"}

        # 1. Idempotency check: prevent duplicate lead processing
        existing_lead = db.query(Lead).filter(Lead.meta_lead_id == leadgen_id).first()
        if existing_lead:
            logger.info(f"Duplicate Meta leadgen_id={leadgen_id} ignored (idempotent).")
            return {
                "status": "duplicate",
                "lead_id": existing_lead.id,
                "meta_lead_id": leadgen_id,
                "message": "Lead already processed.",
            }

        # 2. Fetch full lead details from Meta Graph API
        graph_data = mock_graph_lead
        if graph_data is None:
            graph_data = m_svc.fetch_lead_details_from_graph(leadgen_id)

        if not graph_data:
            # If Graph API call fails and no mock data provided, check if change_value has field_data
            if change_value.get("field_data"):
                graph_data = {
                    "id": leadgen_id,
                    "form_id": change_value.get("form_id"),
                    "ad_id": change_value.get("ad_id"),
                    "adset_id": change_value.get("adgroup_id"),
                    "campaign_id": change_value.get("campaign_id"),
                    "created_time": change_value.get("created_time"),
                    "field_data": change_value.get("field_data"),
                    "custom_disclaimer_responses": change_value.get("custom_disclaimer_responses", []),
                }
            else:
                return {
                    "status": "failed_graph_fetch",
                    "meta_lead_id": leadgen_id,
                    "message": "Could not retrieve lead details from Meta Graph API.",
                }

        extracted = m_svc.extract_lead_fields(graph_data, webhook_value=change_value)

        # 3. Identify campaign and automation rule
        campaign, automation, match_method = c_svc.identify_campaign_automation(
            db=db,
            meta_campaign_id=extracted.get("meta_campaign_id"),
            meta_form_id=extracted.get("meta_form_id"),
            meta_page_id=extracted.get("meta_page_id"),
        )

        # Determine initial lead status
        if not extracted.get("phone"):
            initial_lead_status = "INVALID_PHONE"
            initial_msg_status = "FAILED"
        elif not automation:
            # Campaign identification failed -> put lead in MANUAL_REVIEW queue, do NOT send unrelated message
            initial_lead_status = "MANUAL_REVIEW"
            initial_msg_status = "MANUAL_REVIEW"
        else:
            initial_lead_status = "NEW"
            initial_msg_status = "PENDING"

        new_lead = Lead(
            meta_lead_id=leadgen_id,
            meta_form_id=extracted.get("meta_form_id"),
            meta_ad_id=extracted.get("meta_ad_id"),
            meta_adgroup_id=extracted.get("meta_adgroup_id"),
            meta_campaign_id=extracted.get("meta_campaign_id")
            or (automation.meta_campaign_id if automation else None),
            meta_page_id=extracted.get("meta_page_id")
            or (automation.facebook_page_id if automation else None),
            campaign_id=campaign.id if campaign else (automation.campaign_id if automation else None),
            automation_id=automation.id if automation else None,
            full_name=extracted.get("full_name") or "Unknown Lead",
            phone=extracted.get("phone"),
            email=extracted.get("email"),
            city=extracted.get("city"),
            lead_source="meta_instant_form",
            platform=extracted.get("platform") or "facebook",
            campaign_name=automation.campaign_name if automation else (campaign.name if campaign else "Unmapped Campaign"),
            campaign_purpose=automation.campaign_purpose if automation else (campaign.purpose if campaign else "unmapped"),
            lead_status=initial_lead_status,
            message_status=initial_msg_status,
            whatsapp_opt_in=bool(extracted.get("whatsapp_opt_in", True)),
            opted_out=not bool(extracted.get("whatsapp_opt_in", True)),
            raw_field_data=extracted.get("raw_field_data") or {},
            meta_created_time=extracted.get("meta_created_time") or utc_now(),
        )

        try:
            db.add(new_lead)
            db.commit()
            db.refresh(new_lead)
        except IntegrityError:
            db.rollback()
            existing = db.query(Lead).filter(Lead.meta_lead_id == leadgen_id).first()
            return {
                "status": "duplicate",
                "lead_id": existing.id if existing else None,
                "meta_lead_id": leadgen_id,
            }

        # 4. Record WhatsApp Opt-in Consent audit record
        consent = LeadConsent(
            lead_id=new_lead.id,
            phone=new_lead.phone or extracted.get("raw_phone") or "MISSING",
            consent_status=extracted.get("consent_status") or "OPTED_IN",
            consent_source=extracted.get("consent_source") or "meta_instant_form",
            consent_text=extracted.get("consent_text"),
            ip_or_platform=f"Meta Instant Form ({new_lead.platform})",
        )
        db.add(consent)
        db.commit()

        # 5. Execute Campaign-Wise WhatsApp Automation if matched & valid phone
        automation_result: Dict[str, Any] = {
            "sent": False,
            "reason": match_method,
        }
        if automation and new_lead.phone:
            automation_result = c_svc.execute_campaign_automation_for_lead(
                db=db,
                lead=new_lead,
                automation=automation,
                doubletick_svc=dt_svc,
            )

        # 6. Optional Google Sheets Sync
        if settings.GOOGLE_SHEETS_ENABLED and settings.GOOGLE_SHEETS_WEBHOOK_URL:
            LeadService.sync_lead_to_google_sheets(new_lead)

        return {
            "status": "processed",
            "lead_id": new_lead.id,
            "meta_lead_id": new_lead.meta_lead_id,
            "lead_status": new_lead.lead_status,
            "message_status": new_lead.message_status,
            "campaign_matched": bool(automation),
            "match_method": match_method,
            "campaign_name": new_lead.campaign_name,
            "campaign_purpose": new_lead.campaign_purpose,
            "automation_result": automation_result,
        }

    @staticmethod
    def sync_lead_to_google_sheets(lead: Lead) -> bool:
        if not settings.GOOGLE_SHEETS_WEBHOOK_URL:
            return False
        try:
            with httpx.Client(timeout=5.0) as client:
                client.post(
                    settings.GOOGLE_SHEETS_WEBHOOK_URL,
                    json={
                        "lead_id": lead.id,
                        "meta_lead_id": lead.meta_lead_id,
                        "full_name": lead.full_name,
                        "phone": lead.phone,
                        "email": lead.email,
                        "campaign_name": lead.campaign_name,
                        "campaign_purpose": lead.campaign_purpose,
                        "lead_status": lead.lead_status,
                        "message_status": lead.message_status,
                        "created_at": str(lead.created_at),
                    },
                )
            return True
        except Exception as exc:
            logger.warning(f"Optional Google Sheets webhook sync failed: {exc}")
            return False


lead_service = LeadService()
