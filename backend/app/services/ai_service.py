"""
Optional Gemini AI-Based Reply Service (app/services/ai_service.py)
Provides compliant, context-grounded bilingual (English & Hindi) replies within the
24-hour WhatsApp customer service window using configured campaign facts.
Strictly avoids inventing prices, salaries, or availability and escalates uncertain
or negotiation queries to a human executive.
"""
import re
from typing import Any, Dict, Optional

import httpx

from app.config import settings
from app.database import Session
from app.models import CampaignAutomation, IncomingMessage, Lead, SystemSetting
from app.utils.logger import get_logger

logger = get_logger("ai_service")

HINDI_MARKERS = {
    "kya",
    "hai",
    "kahan",
    "kitna",
    "kitne",
    "batao",
    "bataiye",
    "chahiye",
    "naukri",
    "salary",
    "hospital",
    "details",
    "jankari",
    "sampark",
    "namaste",
    "ji",
}

ESCALATION_KEYWORDS = {
    "discount",
    "negotiate",
    "final price",
    "exact price",
    "owner number",
    "commission",
    "legal",
    "valuation",
    "visit tomorrow",
    "site visit",
    "interview schedule",
    "offer letter",
    "call me",
    "talk to human",
    "agent",
    "executive",
}


class AIService:
    def __init__(self):
        self.enabled = settings.AI_REPLY_ENABLED
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL

    def is_enabled(self, db: Session) -> bool:
        setting_rec = (
            db.query(SystemSetting)
            .filter(SystemSetting.setting_key == "ai_reply_config")
            .first()
        )
        if setting_rec and isinstance(setting_rec.setting_value, dict):
            return bool(setting_rec.setting_value.get("enabled", self.enabled))
        return self.enabled

    @staticmethod
    def detect_language(text: str) -> str:
        # Check for Devanagari Unicode range
        if re.search(r"[\u0900-\u097F]", text):
            return "hi"
        words = set(re.findall(r"[a-zA-Z]+", text.lower()))
        if len(words.intersection(HINDI_MARKERS)) >= 2:
            return "hi"
        return "en"

    @staticmethod
    def needs_human_escalation(text: str) -> bool:
        lower = text.lower()
        for kw in ESCALATION_KEYWORDS:
            if kw in lower:
                return True
        return False

    def generate_grounded_reply(
        self,
        lead: Lead,
        automation: Optional[CampaignAutomation],
        question_text: str,
    ) -> Dict[str, Any]:
        lang = self.detect_language(question_text)
        escalate = self.needs_human_escalation(question_text)
        exec_name = lead.assigned_executive_name or "our Senior Space Consultant Advisor"

        if not automation:
            if lang == "hi":
                reply = (
                    f"नमस्ते {lead.full_name}, आपके संदेश के लिए धन्यवाद। "
                    f"हमारे सलाहकार ({exec_name}) आपकी आवश्यकता की समीक्षा कर रहे हैं और शीघ्र ही आपसे संपर्क करेंगे।"
                )
            else:
                reply = (
                    f"Hello {lead.full_name}, thank you for reaching out to Space Consultant. "
                    f"{exec_name} is reviewing your enquiry and will connect with you shortly."
                )
            return {"reply_text": reply, "escalated": True, "language": lang}

        knowledge = automation.campaign_knowledge or {}
        vars_details = (automation.template_variables or {}).get("details") or {}
        merged_facts = {**vars_details, **knowledge}
        brochure = automation.pdf_brochure_url
        website = automation.website_url or "https://spaceconsultant.in"

        if escalate:
            if lang == "hi":
                reply = (
                    f"नमस्ते {lead.full_name}, '{automation.campaign_name}' के संबंध में आपके प्रश्न के लिए धन्यवाद। "
                    f"सटीक विवरण और आगे की चर्चा के लिए हमारे वरिष्ठ सलाहकार {exec_name} को आपका संदेश भेज दिया गया है। "
                    f"अधिक जानकारी: {website}"
                )
            else:
                reply = (
                    f"Hello {lead.full_name}, thank you for your specific query regarding '{automation.campaign_name}'. "
                    f"To give you accurate verified details, I have escalated your request to {exec_name}, who will contact you shortly. "
                    f"You can also review official details at {website}"
                )
            if brochure:
                reply += f"\nBrochure: {brochure}"
            return {"reply_text": reply, "escalated": True, "language": lang}

        # Build strictly grounded response from configured campaign facts
        summary_parts = []
        for label, key in [
            ("Location", "location"),
            ("Summary", "summary"),
            ("Facilities", "facilities"),
            ("Specialities", "specialities"),
            ("Role", "job_title"),
            ("Department", "department"),
            ("Eligibility", "eligibility"),
            ("Compensation Band", "salary_band"),
            ("Property Specs", "property_specs"),
        ]:
            if merged_facts.get(key):
                summary_parts.append(f"• {label}: {merged_facts[key]}")

        facts_block = "\n".join(summary_parts) if summary_parts else f"• Campaign: {automation.campaign_name}"

        # Optional live Gemini call if GEMINI_API_KEY is configured
        if self.api_key:
            try:
                prompt = (
                    "You are Space Consultant's official WhatsApp assistant. "
                    "Answer the customer's question ONLY using the verified campaign facts below. "
                    "Do NOT invent any prices, salaries, availability, or property details. "
                    f"Respond concisely in {'Hindi' if lang == 'hi' else 'English'}.\n\n"
                    f"Campaign: {automation.campaign_name} ({automation.campaign_purpose})\n"
                    f"Verified Facts:\n{facts_block}\n"
                    f"Brochure URL: {brochure or 'N/A'}\n"
                    f"Website URL: {website}\n"
                    f"Customer Name: {lead.full_name}\n"
                    f"Customer Question: {question_text}"
                )
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{self.model}:generateContent?key={self.api_key}"
                )
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(
                        url,
                        json={"contents": [{"parts": [{"text": prompt}]}]},
                    )
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates") or []
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and parts[0].get("text"):
                            return {
                                "reply_text": parts[0]["text"].strip(),
                                "escalated": False,
                                "language": lang,
                            }
            except Exception as exc:
                logger.warning(f"Gemini API call fallback triggered: {exc}")

        if lang == "hi":
            reply = (
                f"नमस्ते {lead.full_name}, '{automation.campaign_name}' से संबंधित आधिकारिक जानकारी नीचे दी गई है:\n"
                f"{facts_block}\n"
            )
            if brochure:
                reply += f"ब्रोशर लिंक: {brochure}\n"
            reply += f"वेबसाइट: {website}\nयदि आप हमारे सलाहकार ({exec_name}) से बात करना चाहते हैं, तो कृपया 'CALL ME' लिखें।"
        else:
            reply = (
                f"Hello {lead.full_name}, here are the verified details for *{automation.campaign_name}*:\n"
                f"{facts_block}\n"
            )
            if brochure:
                reply += f"Brochure: {brochure}\n"
            reply += f"More info: {website}\nReply 'CALL ME' anytime to speak directly with {exec_name}."

        return {"reply_text": reply, "escalated": False, "language": lang}

    def process_incoming_question(
        self,
        db: Session,
        lead: Lead,
        incoming_message: IncomingMessage,
        doubletick_service: Any,
    ) -> Optional[Dict[str, Any]]:
        if not self.is_enabled(db):
            return None
        if not doubletick_service.is_within_service_window(lead):
            logger.info(f"Skipping AI free-form reply for lead {lead.id}: outside 24h service window.")
            return None

        automation = None
        if lead.automation_id:
            automation = (
                db.query(CampaignAutomation)
                .filter(CampaignAutomation.id == lead.automation_id)
                .first()
            )

        result = self.generate_grounded_reply(
            lead=lead,
            automation=automation,
            question_text=incoming_message.message_text or "",
        )
        reply_text = result["reply_text"]
        escalated = result["escalated"]

        msg_log = doubletick_service.send_text_message(
            db=db,
            to_phone=lead.phone,
            text=reply_text,
            lead=lead,
            campaign_id=lead.campaign_id,
            is_ai_reply=True,
        )

        incoming_message.ai_reply_generated = msg_log.status == "SENT"
        incoming_message.ai_reply_text = reply_text
        incoming_message.escalated_to_human = escalated
        db.commit()

        return {
            "sent": msg_log.status == "SENT",
            "message_log_id": msg_log.id,
            "escalated_to_human": escalated,
            "language": result["language"],
        }


ai_service = AIService()
