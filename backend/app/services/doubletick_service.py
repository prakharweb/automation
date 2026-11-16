"""
DoubleTick WhatsApp Business API Service (app/services/doubletick_service.py)
Official Endpoints Implemented:
- POST https://public.doubletick.io/whatsapp/message/template
- POST https://public.doubletick.io/whatsapp/message/text
- POST https://public.doubletick.io/whatsapp/message/image
- POST https://public.doubletick.io/whatsapp/message/document
Reference: https://docs.doubletick.io/docs/template-messages
"""
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import settings
from app.database import Session
from app.models import (
    FollowupJob,
    IncomingMessage,
    Lead,
    LeadConsent,
    MessageLog,
    utc_now,
)
from app.utils.logger import get_logger, mask_secret, sanitize_dict
from app.utils.phone import normalize_phone_number

logger = get_logger("doubletick_service")

OPT_OUT_KEYWORDS = {"stop", "unsubscribe", "optout", "opt-out", "cancel", "quit", "band karo"}


class DoubleTickService:
    def __init__(
        self,
        api_key: Optional[str] = None,
        sender_number: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key if api_key is not None else settings.DOUBLETICK_API_KEY
        self.sender_number = sender_number if sender_number is not None else settings.DOUBLETICK_SENDER
        self.base_url = (base_url or settings.DOUBLETICK_BASE_URL).rstrip("/")

    def get_headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise ValueError("DOUBLETICK_API_KEY is not configured.")
        return {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def get_status(self) -> Dict[str, Any]:
        configured = bool(self.api_key and self.sender_number)
        return {
            "configured": configured,
            "api_key_masked": mask_secret(self.api_key) if self.api_key else None,
            "sender_number": self.sender_number or None,
            "webhook_secret_configured": bool(settings.DOUBLETICK_WEBHOOK_SECRET),
            "base_url": self.base_url,
            "endpoints": {
                "template": f"{self.base_url}/whatsapp/message/template",
                "text": f"{self.base_url}/whatsapp/message/text",
                "image": f"{self.base_url}/whatsapp/message/image",
                "document": f"{self.base_url}/whatsapp/message/document",
            },
        }

    @staticmethod
    def _resolve_unique_message_id(db: Session, candidate_id: str, fallback_uuid: str) -> str:
        existing = (
            db.query(MessageLog)
            .filter(MessageLog.doubletick_message_id == candidate_id)
            .first()
        )
        if existing:
            return fallback_uuid
        return candidate_id

    def build_template_payload(
        self,
        to_phone: str,
        template_name: str,
        language: str = "en",
        placeholders: Optional[List[str]] = None,
        header: Optional[Dict[str, Any]] = None,
        buttons: Optional[List[Dict[str, Any]]] = None,
        message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_to = normalize_phone_number(to_phone)
        if not normalized_to:
            raise ValueError(f"Invalid recipient phone number: {to_phone}")

        msg_uuid = message_id if (message_id and len(message_id) == 36) else str(uuid.uuid4())
        template_data: Dict[str, Any] = {
            "body": {
                "placeholders": [str(p) for p in (placeholders or [])],
            }
        }
        if header:
            template_data["header"] = header
        if buttons:
            template_data["buttons"] = buttons

        return {
            "messages": [
                {
                    "to": normalized_to,
                    "from": self.sender_number,
                    "messageId": msg_uuid,
                    "content": {
                        "templateName": template_name,
                        "language": language,
                        "templateData": template_data,
                    },
                }
            ]
        }

    def build_text_payload(
        self,
        to_phone: str,
        text: str,
        message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_to = normalize_phone_number(to_phone)
        if not normalized_to:
            raise ValueError(f"Invalid recipient phone number: {to_phone}")
        msg_uuid = message_id if (message_id and len(message_id) == 36) else str(uuid.uuid4())
        return {
            "to": normalized_to,
            "from": self.sender_number,
            "messageId": msg_uuid,
            "content": {
                "text": text,
            },
        }

    def build_image_payload(
        self,
        to_phone: str,
        media_url: str,
        caption: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_to = normalize_phone_number(to_phone)
        if not normalized_to:
            raise ValueError(f"Invalid recipient phone number: {to_phone}")
        msg_uuid = message_id if (message_id and len(message_id) == 36) else str(uuid.uuid4())
        content: Dict[str, Any] = {"mediaUrl": media_url}
        if caption:
            content["caption"] = caption[:3000]
        return {
            "to": normalized_to,
            "from": self.sender_number,
            "messageId": msg_uuid,
            "content": content,
        }

    def build_document_payload(
        self,
        to_phone: str,
        media_url: str,
        filename: Optional[str] = None,
        caption: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_to = normalize_phone_number(to_phone)
        if not normalized_to:
            raise ValueError(f"Invalid recipient phone number: {to_phone}")
        msg_uuid = message_id if (message_id and len(message_id) == 36) else str(uuid.uuid4())
        content: Dict[str, Any] = {"mediaUrl": media_url}
        if caption:
            content["caption"] = caption[:3000]
        if filename:
            content["filename"] = filename[:240]
        return {
            "to": normalized_to,
            "from": self.sender_number,
            "messageId": msg_uuid,
            "content": content,
        }

    def _post_with_retry(
        self,
        endpoint_path: str,
        payload: Dict[str, Any],
        max_retries: int = 2,
    ) -> Tuple[bool, int, Dict[str, Any]]:
        url = f"{self.base_url}{endpoint_path}"
        headers = self.get_headers()
        last_error = "Unknown error"
        status_code = 500

        for attempt in range(max_retries + 1):
            try:
                with httpx.Client(timeout=15.0) as client:
                    resp = client.post(url, json=payload, headers=headers)
                status_code = resp.status_code
                try:
                    data = resp.json()
                except Exception:
                    data = {"raw": resp.text}

                if status_code in (200, 201, 202):
                    return True, status_code, data

                last_error = data.get("message") or data.get("error") or resp.text
                logger.error(
                    f"DoubleTick API error on {endpoint_path} (HTTP {status_code}): {last_error}"
                )
                if 400 <= status_code < 500 and status_code != 429:
                    return False, status_code, data
            except Exception as exc:
                last_error = str(exc)
                logger.error(f"DoubleTick API network exception (attempt {attempt + 1}): {last_error}")

            if attempt < max_retries:
                time.sleep(0.5 * (attempt + 1))

        return False, status_code, {"message": last_error, "statusCode": status_code}

    def send_template_message(
        self,
        db: Session,
        to_phone: str,
        template_name: str,
        language: str = "en",
        placeholders: Optional[List[str]] = None,
        header: Optional[Dict[str, Any]] = None,
        buttons: Optional[List[Dict[str, Any]]] = None,
        lead_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        content_preview: Optional[str] = None,
    ) -> MessageLog:
        msg_uuid = str(uuid.uuid4())
        payload = self.build_template_payload(
            to_phone=to_phone,
            template_name=template_name,
            language=language,
            placeholders=placeholders,
            header=header,
            buttons=buttons,
            message_id=msg_uuid,
        )
        ok, status_code, resp_data = self._post_with_retry("/whatsapp/message/template", payload)
        raw_returned_id = str(resp_data.get("messageId") or msg_uuid)
        returned_msg_id = self._resolve_unique_message_id(db, raw_returned_id, msg_uuid)
        msg_status = "SENT" if ok else "FAILED"
        err_msg = None if ok else str(resp_data.get("message") or resp_data.get("error") or f"HTTP {status_code}")

        log_entry = MessageLog(
            lead_id=lead_id,
            campaign_id=campaign_id,
            doubletick_message_id=returned_msg_id,
            recipient_phone=normalize_phone_number(to_phone) or to_phone,
            sender_phone=self.sender_number,
            message_type="TEMPLATE",
            template_name=template_name,
            template_language=language,
            variables_payload={
                "placeholders": placeholders or [],
                "header": header,
                "buttons": buttons,
            },
            content_preview=content_preview or f"Template: {template_name} ({language})",
            media_url=(header or {}).get("mediaUrl"),
            status=msg_status,
            error_message=err_msg,
            sent_at=utc_now() if ok else None,
            failed_at=None if ok else utc_now(),
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    def send_text_message(
        self,
        db: Session,
        to_phone: str,
        text: str,
        lead: Optional[Lead] = None,
        campaign_id: Optional[str] = None,
        is_ai_reply: bool = False,
    ) -> MessageLog:
        if lead is not None and not self.is_within_service_window(lead):
            raise PermissionError(
                "Cannot send free-form text message outside the 24-hour customer service window. "
                "Use an approved WhatsApp template message instead."
            )

        msg_uuid = str(uuid.uuid4())
        payload = self.build_text_payload(to_phone=to_phone, text=text, message_id=msg_uuid)
        ok, status_code, resp_data = self._post_with_retry("/whatsapp/message/text", payload)
        raw_returned_id = str(resp_data.get("messageId") or msg_uuid)
        returned_msg_id = self._resolve_unique_message_id(db, raw_returned_id, msg_uuid)

        log_entry = MessageLog(
            lead_id=lead.id if lead else None,
            campaign_id=campaign_id or (lead.campaign_id if lead else None),
            doubletick_message_id=returned_msg_id,
            recipient_phone=normalize_phone_number(to_phone) or to_phone,
            sender_phone=self.sender_number,
            message_type="AI_REPLY" if is_ai_reply else "TEXT",
            content_preview=text[:500],
            status="SENT" if ok else "FAILED",
            error_message=None if ok else str(resp_data.get("message") or f"HTTP {status_code}"),
            sent_at=utc_now() if ok else None,
            failed_at=None if ok else utc_now(),
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    def send_document_message(
        self,
        db: Session,
        to_phone: str,
        media_url: str,
        filename: Optional[str] = None,
        caption: Optional[str] = None,
        lead_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
    ) -> MessageLog:
        msg_uuid = str(uuid.uuid4())
        payload = self.build_document_payload(
            to_phone=to_phone,
            media_url=media_url,
            filename=filename,
            caption=caption,
            message_id=msg_uuid,
        )
        ok, status_code, resp_data = self._post_with_retry("/whatsapp/message/document", payload)
        raw_returned_id = str(resp_data.get("messageId") or msg_uuid)
        returned_msg_id = self._resolve_unique_message_id(db, raw_returned_id, msg_uuid)

        log_entry = MessageLog(
            lead_id=lead_id,
            campaign_id=campaign_id,
            doubletick_message_id=returned_msg_id,
            recipient_phone=normalize_phone_number(to_phone) or to_phone,
            sender_phone=self.sender_number,
            message_type="DOCUMENT",
            content_preview=caption or f"Document: {filename or media_url}",
            media_url=media_url,
            status="SENT" if ok else "FAILED",
            error_message=None if ok else str(resp_data.get("message") or f"HTTP {status_code}"),
            sent_at=utc_now() if ok else None,
            failed_at=None if ok else utc_now(),
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    def send_image_message(
        self,
        db: Session,
        to_phone: str,
        media_url: str,
        caption: Optional[str] = None,
        lead_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
    ) -> MessageLog:
        msg_uuid = str(uuid.uuid4())
        payload = self.build_image_payload(
            to_phone=to_phone,
            media_url=media_url,
            caption=caption,
            message_id=msg_uuid,
        )
        ok, status_code, resp_data = self._post_with_retry("/whatsapp/message/image", payload)
        raw_returned_id = str(resp_data.get("messageId") or msg_uuid)
        returned_msg_id = self._resolve_unique_message_id(db, raw_returned_id, msg_uuid)

        log_entry = MessageLog(
            lead_id=lead_id,
            campaign_id=campaign_id,
            doubletick_message_id=returned_msg_id,
            recipient_phone=normalize_phone_number(to_phone) or to_phone,
            sender_phone=self.sender_number,
            message_type="IMAGE",
            content_preview=caption or f"Image: {media_url}",
            media_url=media_url,
            status="SENT" if ok else "FAILED",
            error_message=None if ok else str(resp_data.get("message") or f"HTTP {status_code}"),
            sent_at=utc_now() if ok else None,
            failed_at=None if ok else utc_now(),
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    @staticmethod
    def is_within_service_window(lead: Lead) -> bool:
        if not lead.service_window_expires_at:
            return False
        exp = lead.service_window_expires_at
        if isinstance(exp, str):
            exp = datetime.fromisoformat(exp)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return exp > utc_now()

    def handle_status_update_webhook(
        self,
        db: Session,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        inner = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
        message_id = str(
            inner.get("messageId")
            or inner.get("id")
            or payload.get("messageId")
            or ""
        ).strip()
        raw_status = str(
            inner.get("status")
            or payload.get("status")
            or "SENT"
        ).upper().strip()

        status_map = {
            "SENT": "SENT",
            "DELIVERED": "DELIVERED",
            "READ": "READ",
            "SEEN": "READ",
            "FAILED": "FAILED",
            "UNDELIVERED": "FAILED",
        }
        normalized_status = status_map.get(raw_status, raw_status)
        error_detail = inner.get("error") or inner.get("errorMessage") or payload.get("error")

        msg_log = (
            db.query(MessageLog)
            .filter(MessageLog.doubletick_message_id == message_id)
            .first()
        )
        if not msg_log:
            return {
                "updated": False,
                "reason": "message_log_not_found",
                "message_id": message_id,
                "status": normalized_status,
            }

        now = utc_now()
        msg_log.status = normalized_status
        if normalized_status == "DELIVERED":
            msg_log.delivered_at = now
        elif normalized_status == "READ":
            if not msg_log.delivered_at:
                msg_log.delivered_at = now
            msg_log.read_at = now
        elif normalized_status == "FAILED":
            msg_log.failed_at = now
            if error_detail:
                msg_log.error_message = str(error_detail)

        if msg_log.lead_id:
            lead = db.query(Lead).filter(Lead.id == msg_log.lead_id).first()
            if lead:
                lead.message_status = normalized_status
                if normalized_status in ("DELIVERED", "READ") and lead.lead_status == "NEW":
                    lead.lead_status = "CONTACTED"

        db.commit()
        return {
            "updated": True,
            "message_id": message_id,
            "status": normalized_status,
            "lead_id": msg_log.lead_id,
        }

    def handle_incoming_message_webhook(
        self,
        db: Session,
        payload: Dict[str, Any],
        ai_service: Optional[Any] = None,
    ) -> Dict[str, Any]:
        inner = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
        msg_obj = inner.get("message") if isinstance(inner.get("message"), dict) else inner

        external_id = str(
            inner.get("messageId")
            or msg_obj.get("id")
            or payload.get("messageId")
            or str(uuid.uuid4())
        ).strip()

        existing_inc = (
            db.query(IncomingMessage)
            .filter(IncomingMessage.external_message_id == external_id)
            .first()
        )
        if existing_inc:
            return {
                "processed": False,
                "reason": "duplicate_incoming_message",
                "external_message_id": external_id,
            }

        raw_sender = (
            inner.get("from")
            or inner.get("customerPhone")
            or inner.get("sender")
            or payload.get("from")
            or ""
        )
        sender_phone = normalize_phone_number(str(raw_sender)) or str(raw_sender)
        sender_name = (
            inner.get("customerName")
            or inner.get("senderName")
            or payload.get("customerName")
        )
        msg_type = str(msg_obj.get("type") or inner.get("type") or "TEXT").upper()
        text_body = str(
            msg_obj.get("text")
            or inner.get("text")
            or payload.get("text")
            or ""
        ).strip()
        media_url = msg_obj.get("url") or msg_obj.get("mediaUrl") or inner.get("mediaUrl")

        lead = (
            db.query(Lead)
            .filter(Lead.phone == sender_phone)
            .order_by(Lead.created_at.desc())
            .first()
        )

        cleaned_lower = text_body.lower().strip().rstrip(".!")
        is_opt_out = cleaned_lower in OPT_OUT_KEYWORDS

        now = utc_now()
        cancelled_followups = 0

        if lead:
            lead.has_replied = True
            lead.last_inbound_at = now
            lead.service_window_expires_at = now + timedelta(hours=24)

            if is_opt_out:
                lead.opted_out = True
                lead.whatsapp_opt_in = False
                lead.lead_status = "OPTED_OUT"
                lead.automation_paused = True

                consent = (
                    db.query(LeadConsent)
                    .filter(LeadConsent.lead_id == lead.id)
                    .first()
                )
                if consent:
                    consent.consent_status = "OPTED_OUT"
                    consent.opted_out_at = now
                else:
                    db.add(
                        LeadConsent(
                            lead_id=lead.id,
                            phone=sender_phone,
                            consent_status="OPTED_OUT",
                            consent_source="whatsapp_stop_keyword",
                            consent_text=text_body,
                            opted_out_at=now,
                        )
                    )
            else:
                if lead.lead_status in ("NEW", "CONTACTED"):
                    lead.lead_status = "INTERESTED"

            pending_jobs = (
                db.query(FollowupJob)
                .filter(
                    FollowupJob.lead_id == lead.id,
                    FollowupJob.status == "SCHEDULED",
                )
                .all()
            )
            cancel_status = "CANCELLED_OPT_OUT" if is_opt_out else "CANCELLED_REPLIED"
            cancel_reason = (
                "Customer sent STOP/opt-out keyword"
                if is_opt_out
                else "Customer replied to WhatsApp thread"
            )
            for job in pending_jobs:
                job.status = cancel_status
                job.cancellation_reason = cancel_reason
                cancelled_followups += 1

        inc_record = IncomingMessage(
            lead_id=lead.id if lead else None,
            external_message_id=external_id,
            sender_phone=sender_phone,
            sender_name=sender_name or (lead.full_name if lead else None),
            message_type=msg_type,
            message_text=text_body,
            media_url=media_url,
            is_opt_out_command=is_opt_out,
            raw_payload=sanitize_dict(payload),
            received_at=now,
        )
        db.add(inc_record)
        db.commit()
        db.refresh(inc_record)

        ai_result = None
        if (
            ai_service is not None
            and lead is not None
            and not is_opt_out
            and not lead.opted_out
            and not lead.automation_paused
            and text_body
        ):
            ai_result = ai_service.process_incoming_question(
                db=db,
                lead=lead,
                incoming_message=inc_record,
                doubletick_service=self,
            )

        return {
            "processed": True,
            "incoming_message_id": inc_record.id,
            "lead_id": lead.id if lead else None,
            "is_opt_out": is_opt_out,
            "cancelled_followups": cancelled_followups,
            "ai_reply": ai_result,
        }


doubletick_service = DoubleTickService()
