"""
Campaign-Wise Automation Engine (app/services/campaign_service.py)
Automatically identifies which campaign generated each Meta Instant Form lead
and selects the corresponding WhatsApp template, variables, brochure PDF,
follow-up schedule, and executive assignment.
"""
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.database import Session
from app.models import (
    Campaign,
    CampaignAutomation,
    FollowupJob,
    Lead,
    LeadAssignment,
    LeadForm,
    WhatsAppTemplate,
    utc_now,
)
from app.services.doubletick_service import DoubleTickService
from app.utils.logger import get_logger

logger = get_logger("campaign_service")


class CampaignService:
    @staticmethod
    def identify_campaign_automation(
        db: Session,
        meta_campaign_id: Optional[str] = None,
        meta_form_id: Optional[str] = None,
        meta_page_id: Optional[str] = None,
    ) -> Tuple[Optional[Campaign], Optional[CampaignAutomation], str]:
        """
        Identifies the campaign and automation configuration for an incoming lead.
        Resolution order (never guesses or falls back to an unrelated campaign):
        1. Exact match on CampaignAutomation.meta_campaign_id
        2. Exact match on CampaignAutomation.lead_form_id
        3. Match via LeadForm.meta_form_id -> Campaign.id -> CampaignAutomation
        4. Exact match on Campaign.meta_campaign_id -> CampaignAutomation
        If no deterministic match is found, returns (None, None, "unmatched") so the lead
        is placed into the MANUAL_REVIEW queue without sending an unrelated message.
        """
        if meta_campaign_id:
            auto = (
                db.query(CampaignAutomation)
                .filter(CampaignAutomation.meta_campaign_id == str(meta_campaign_id))
                .first()
            )
            if auto:
                camp = db.query(Campaign).filter(Campaign.id == auto.campaign_id).first()
                return camp, auto, "matched_by_meta_campaign_id"

        if meta_form_id:
            auto = (
                db.query(CampaignAutomation)
                .filter(CampaignAutomation.lead_form_id == str(meta_form_id))
                .first()
            )
            if auto:
                camp = db.query(Campaign).filter(Campaign.id == auto.campaign_id).first()
                return camp, auto, "matched_by_lead_form_id"

            form_rec = (
                db.query(LeadForm)
                .filter(LeadForm.meta_form_id == str(meta_form_id))
                .first()
            )
            if form_rec and form_rec.campaign_id:
                camp = db.query(Campaign).filter(Campaign.id == form_rec.campaign_id).first()
                auto = (
                    db.query(CampaignAutomation)
                    .filter(CampaignAutomation.campaign_id == form_rec.campaign_id)
                    .first()
                )
                if auto:
                    return camp, auto, "matched_by_form_campaign_relation"

        if meta_campaign_id:
            camp = (
                db.query(Campaign)
                .filter(Campaign.meta_campaign_id == str(meta_campaign_id))
                .first()
            )
            if camp:
                auto = (
                    db.query(CampaignAutomation)
                    .filter(CampaignAutomation.campaign_id == camp.id)
                    .first()
                )
                if auto:
                    return camp, auto, "matched_by_campaign_record"

        return None, None, "unmatched"

    @staticmethod
    def render_template_placeholders(
        lead: Lead,
        automation: CampaignAutomation,
    ) -> List[str]:
        """
        Interpolates dynamic lead & campaign variables into the WhatsApp template placeholders.
        """
        vars_cfg = automation.template_variables or {}
        raw_placeholders = vars_cfg.get("placeholders") or []
        details = vars_cfg.get("details") or {}

        context = {
            "full_name": lead.full_name or "Valued Client",
            "name": lead.full_name or "Valued Client",
            "phone": lead.phone or "",
            "email": lead.email or "",
            "city": lead.city or details.get("location", "India"),
            "campaign_name": automation.campaign_name,
            "campaign_purpose": automation.campaign_purpose,
            "website_url": automation.website_url or "https://spaceconsultant.in",
            "pdf_brochure_url": automation.pdf_brochure_url or "",
            **{k: str(v) for k, v in details.items()},
        }

        if not raw_placeholders:
            return [
                context["full_name"],
                automation.campaign_name,
                details.get("summary") or details.get("information") or automation.website_url or "Space Consultant",
            ]

        rendered: List[str] = []
        for item in raw_placeholders:
            val = str(item)
            for k, v in context.items():
                val = val.replace(f"{{{k}}}", str(v)).replace(f"{{{{{k}}}}}", str(v))
            rendered.append(val)
        return rendered

    @classmethod
    def execute_campaign_automation_for_lead(
        cls,
        db: Session,
        lead: Lead,
        automation: CampaignAutomation,
        doubletick_svc: DoubleTickService,
    ) -> Dict[str, Any]:
        """
        Executes campaign-specific WhatsApp automation for an eligible lead:
        1. Assigns lead to configured executive if not already assigned
        2. Checks compliance rules (opt-in, not opted-out, valid phone, auto_reply_enabled, approved template)
        3. Sends the campaign's approved WhatsApp template message (with header document/image if configured)
        4. Sends supplementary PDF brochure as standalone document ONLY if within active 24h customer service window
        5. Schedules persistent 24-hour and 72-hour follow-up jobs
        """
        assign_cfg = automation.assignment_config or {}
        exec_name = assign_cfg.get("default_executive_name")
        exec_id = assign_cfg.get("default_executive_id")
        if exec_name and not lead.assigned_executive_name:
            lead.assigned_executive_id = exec_id
            lead.assigned_executive_name = exec_name
            db.add(
                LeadAssignment(
                    lead_id=lead.id,
                    executive_id=exec_id,
                    executive_name=exec_name,
                    assigned_by="campaign_automation",
                    assignment_notes=f"Auto-assigned via campaign '{automation.campaign_name}'",
                )
            )

        if not lead.phone:
            lead.lead_status = "INVALID_PHONE"
            lead.message_status = "FAILED"
            db.commit()
            return {"sent": False, "reason": "missing_or_invalid_phone"}

        if lead.opted_out or not lead.whatsapp_opt_in:
            lead.message_status = "SKIPPED_NO_CONSENT"
            db.commit()
            return {"sent": False, "reason": "whatsapp_opt_in_missing_or_opted_out"}

        if lead.automation_paused or not automation.auto_reply_enabled:
            lead.message_status = "PAUSED"
            db.commit()
            return {"sent": False, "reason": "automation_paused_or_disabled"}

        tpl_record = (
            db.query(WhatsAppTemplate)
            .filter(WhatsAppTemplate.template_name == automation.whatsapp_template_name)
            .first()
        )
        if tpl_record and tpl_record.approval_status != "APPROVED":
            lead.message_status = "MANUAL_REVIEW"
            db.commit()
            return {"sent": False, "reason": f"template_not_approved:{tpl_record.approval_status}"}

        placeholders = cls.render_template_placeholders(lead, automation)

        header_payload: Optional[Dict[str, Any]] = None
        header_type = tpl_record.header_type if tpl_record else "NONE"
        if header_type == "DOCUMENT" and automation.pdf_brochure_url:
            header_payload = {
                "type": "DOCUMENT",
                "mediaUrl": automation.pdf_brochure_url,
                "filename": automation.pdf_filename or "Space_Consultant_Brochure.pdf",
            }
        elif header_type == "IMAGE" and automation.image_attachment_url:
            header_payload = {
                "type": "IMAGE",
                "mediaUrl": automation.image_attachment_url,
            }

        buttons_payload: Optional[List[Dict[str, Any]]] = None
        if automation.website_url:
            buttons_payload = [{"type": "URL", "parameter": automation.website_url}]

        preview_text = (
            f"[{automation.campaign_purpose}] Template '{automation.whatsapp_template_name}' "
            f"to {lead.full_name}: {', '.join(placeholders)}"
        )

        msg_log = doubletick_svc.send_template_message(
            db=db,
            to_phone=lead.phone,
            template_name=automation.whatsapp_template_name,
            language=automation.template_language or "en",
            placeholders=placeholders,
            header=header_payload,
            buttons=buttons_payload,
            lead_id=lead.id,
            campaign_id=automation.campaign_id,
            content_preview=preview_text,
        )

        lead.message_status = msg_log.status
        if msg_log.status == "SENT" and lead.lead_status == "NEW":
            lead.lead_status = "CONTACTED"

        # Send standalone PDF brochure only if customer is inside the 24-hour service window
        supplementary_logs = []
        if (
            msg_log.status == "SENT"
            and automation.pdf_brochure_url
            and header_type != "DOCUMENT"
            and doubletick_svc.is_within_service_window(lead)
        ):
            doc_log = doubletick_svc.send_document_message(
                db=db,
                to_phone=lead.phone,
                media_url=automation.pdf_brochure_url,
                filename=automation.pdf_filename or f"{automation.campaign_name.replace(' ', '_')}.pdf",
                caption=f"Information brochure for {automation.campaign_name}",
                lead_id=lead.id,
                campaign_id=automation.campaign_id,
            )
            supplementary_logs.append(doc_log.id)

        scheduled_jobs = cls.schedule_followups_for_lead(
            db=db,
            lead=lead,
            automation=automation,
            placeholders=placeholders,
        )
        db.commit()

        return {
            "sent": msg_log.status == "SENT",
            "message_log_id": msg_log.id,
            "doubletick_message_id": msg_log.doubletick_message_id,
            "template_name": automation.whatsapp_template_name,
            "status": msg_log.status,
            "supplementary_logs": supplementary_logs,
            "scheduled_followups": len(scheduled_jobs),
        }

    @staticmethod
    def schedule_followups_for_lead(
        db: Session,
        lead: Lead,
        automation: CampaignAutomation,
        placeholders: List[str],
    ) -> List[FollowupJob]:
        followup_cfg = automation.followup_config or {}
        if not followup_cfg.get("enabled", True):
            return []

        now = utc_now()
        created_jobs: List[FollowupJob] = []

        steps = [
            {
                "step_number": 2,
                "delay_hours": int(followup_cfg.get("step_2_delay_hours", 24)),
                "template_name": followup_cfg.get(
                    "step_2_template", f"{automation.whatsapp_template_name}_followup_24h"
                ),
            },
            {
                "step_number": 3,
                "delay_hours": int(followup_cfg.get("step_3_delay_hours", 72)),
                "template_name": followup_cfg.get(
                    "step_3_template", f"{automation.whatsapp_template_name}_followup_72h"
                ),
            },
        ]

        for step in steps:
            if step["delay_hours"] <= 0:
                continue
            existing = (
                db.query(FollowupJob)
                .filter(
                    FollowupJob.lead_id == lead.id,
                    FollowupJob.step_number == step["step_number"],
                )
                .first()
            )
            if existing:
                continue

            job = FollowupJob(
                lead_id=lead.id,
                automation_id=automation.id,
                step_number=step["step_number"],
                template_name=step["template_name"],
                template_language=automation.template_language or "en",
                template_variables={"placeholders": placeholders},
                scheduled_at=now + timedelta(hours=step["delay_hours"]),
                status="SCHEDULED",
            )
            db.add(job)
            created_jobs.append(job)

        return created_jobs


campaign_service = CampaignService()
