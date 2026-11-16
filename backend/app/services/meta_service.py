"""
Meta Marketing & Graph API Service (app/services/meta_service.py)
Implements:
- Meta Graph API lead retrieval: GET /{version}/{leadgen_id}
- Page webhook subscription: POST /{version}/{page_id}/subscribed_apps?subscribed_fields=leadgen
- Connected Facebook Pages, Ad Accounts, Active Campaigns, and Lead Forms retrieval
- Structured extraction of lead fields (full_name, phone, email, city, consent, campaign_id, form_id, ad_id)
- Retry handling for transient Graph API failures
"""
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import settings
from app.database import Session
from app.models import (
    AdAccount,
    Campaign,
    FacebookPage,
    LeadForm,
    MetaAccount,
    utc_now,
)
from app.utils.logger import get_logger, mask_secret
from app.utils.phone import normalize_phone_number

logger = get_logger("meta_service")

REQUIRED_META_PERMISSIONS = [
    "leads_retrieval",
    "pages_manage_metadata",
    "pages_show_list",
    "pages_read_engagement",
    "pages_manage_ads",
    "ads_management",
    "ads_read",
]


class MetaService:
    def __init__(
        self,
        access_token: Optional[str] = None,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        verify_token: Optional[str] = None,
        graph_version: Optional[str] = None,
    ):
        self.access_token = access_token if access_token is not None else settings.META_ACCESS_TOKEN
        self.app_id = app_id if app_id is not None else settings.META_APP_ID
        self.app_secret = app_secret if app_secret is not None else settings.META_APP_SECRET
        self.verify_token = verify_token if verify_token is not None else settings.META_VERIFY_TOKEN
        self.graph_version = graph_version or settings.META_GRAPH_API_VERSION
        self.base_url = f"{settings.META_GRAPH_BASE_URL.rstrip('/')}/{self.graph_version}"

    def get_status(self, db: Session) -> Dict[str, Any]:
        meta_acc = db.query(MetaAccount).first()
        pages_count = db.query(FacebookPage).count()
        ad_accounts_count = db.query(AdAccount).count()
        campaigns_count = db.query(Campaign).count()
        forms_count = db.query(LeadForm).count()

        env_configured = bool(self.app_id and self.app_secret and self.verify_token)
        token_configured = bool(self.access_token or (meta_acc and meta_acc.access_token_masked))

        return {
            "connected": bool(env_configured or meta_acc),
            "live_credentials_configured": bool(self.app_id and self.app_secret and self.access_token),
            "app_id": self.app_id or (meta_acc.app_id if meta_acc else None),
            "app_name": meta_acc.app_name if meta_acc else "Space Consultant Meta Lead App",
            "verify_token_configured": bool(self.verify_token),
            "app_secret_configured": bool(self.app_secret),
            "access_token_masked": (
                mask_secret(self.access_token)
                if self.access_token
                else (meta_acc.access_token_masked if meta_acc else None)
            ),
            "graph_api_version": self.graph_version,
            "required_permissions": REQUIRED_META_PERMISSIONS,
            "counts": {
                "facebook_pages": pages_count,
                "ad_accounts": ad_accounts_count,
                "campaigns": campaigns_count,
                "lead_forms": forms_count,
            },
        }

    def _graph_get_with_retry(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 2,
    ) -> Tuple[bool, int, Dict[str, Any]]:
        if not self.access_token:
            return False, 401, {"error": {"message": "META_ACCESS_TOKEN is not configured"}}

        url = f"{self.base_url}/{path.lstrip('/')}"
        query_params = dict(params or {})
        query_params["access_token"] = self.access_token

        last_err = "Unknown Graph API error"
        status_code = 500
        for attempt in range(max_retries + 1):
            try:
                with httpx.Client(timeout=15.0) as client:
                    resp = client.get(url, params=query_params)
                status_code = resp.status_code
                data = resp.json()
                if status_code == 200 and "error" not in data:
                    return True, 200, data
                err_obj = data.get("error", {})
                last_err = err_obj.get("message") or resp.text
                logger.error(f"Meta Graph API GET {path} error (HTTP {status_code}): {last_err}")
                if 400 <= status_code < 500 and status_code != 429:
                    return False, status_code, data
            except Exception as exc:
                last_err = str(exc)
                logger.error(f"Meta Graph API network exception (attempt {attempt + 1}): {last_err}")
            if attempt < max_retries:
                time.sleep(0.5 * (attempt + 1))

        return False, status_code, {"error": {"message": last_err}}

    def fetch_lead_details_from_graph(self, leadgen_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetches complete lead details from Meta Graph API using leadgen_id:
        GET https://graph.facebook.com/{version}/{leadgen_id}?fields=id,created_time,ad_id,ad_name,adset_id,adset_name,campaign_id,campaign_name,form_id,is_organic,platform,field_data,custom_disclaimer_responses
        """
        fields = (
            "id,created_time,ad_id,ad_name,adset_id,adset_name,"
            "campaign_id,campaign_name,form_id,is_organic,platform,"
            "field_data,custom_disclaimer_responses"
        )
        ok, _, data = self._graph_get_with_retry(leadgen_id, params={"fields": fields})
        if ok and isinstance(data, dict) and data.get("id"):
            return data
        return None

    @staticmethod
    def extract_lead_fields(
        graph_lead_data: Dict[str, Any],
        webhook_value: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Extracts normalized lead attributes from Meta Graph API lead response
        (with fallback metadata from verified webhook change value when needed).
        """
        wh = webhook_value or {}
        field_data_list = graph_lead_data.get("field_data") or []
        raw_map: Dict[str, Any] = {}

        for item in field_data_list:
            if not isinstance(item, dict):
                continue
            key = str(item.get("name") or "").strip().lower()
            values = item.get("values") or []
            first_val = values[0] if (isinstance(values, list) and values) else item.get("value")
            if key:
                raw_map[key] = first_val

        # Full name resolution
        full_name = (
            raw_map.get("full_name")
            or raw_map.get("name")
            or raw_map.get("your_name")
            or raw_map.get("candidate_name")
            or raw_map.get("doctor_name")
            or raw_map.get("buyer_name")
        )
        if not full_name:
            first_n = raw_map.get("first_name") or ""
            last_n = raw_map.get("last_name") or ""
            combined = f"{first_n} {last_n}".strip()
            full_name = combined if combined else "Unknown Lead"

        # Phone resolution
        raw_phone = (
            raw_map.get("phone_number")
            or raw_map.get("phone")
            or raw_map.get("mobile_number")
            or raw_map.get("whatsapp_number")
            or raw_map.get("contact_number")
        )
        normalized_phone = normalize_phone_number(str(raw_phone)) if raw_phone else None

        # Email & City resolution
        email = (
            raw_map.get("email")
            or raw_map.get("email_address")
            or raw_map.get("work_email")
        )
        city = (
            raw_map.get("city")
            or raw_map.get("location")
            or raw_map.get("preferred_location")
        )

        # WhatsApp opt-in consent extraction (checks custom_disclaimer_responses and field_data)
        explicit_opt_in = None
        consent_source = "meta_instant_form_submission"
        consent_text = "Submitted Meta Instant Form inquiry"

        disclaimers = graph_lead_data.get("custom_disclaimer_responses") or []
        for d in disclaimers:
            if isinstance(d, dict):
                checkbox_key = str(d.get("checkbox_key") or "").lower()
                is_checked = str(d.get("is_checked", "")).lower() in ("true", "1", "yes")
                if "whatsapp" in checkbox_key or "opt" in checkbox_key or "consent" in checkbox_key:
                    explicit_opt_in = is_checked
                    consent_source = "meta_custom_disclaimer_checkbox"
                    consent_text = f"Checkbox {checkbox_key}: {is_checked}"

        for consent_key in ("whatsapp_opt_in", "whatsapp_consent", "opt_in", "marketing_consent"):
            if consent_key in raw_map:
                val_str = str(raw_map[consent_key]).strip().lower()
                explicit_opt_in = val_str in ("true", "yes", "1", "agreed", "opt_in", "y")
                consent_source = f"form_field:{consent_key}"
                consent_text = f"Form field {consent_key}={raw_map[consent_key]}"

        if explicit_opt_in is None:
            # Respect WHATSAPP_REQUIRE_EXPLICIT_CONSENT setting
            whatsapp_opt_in = not settings.WHATSAPP_REQUIRE_EXPLICIT_CONSENT
            consent_Status = "INFERRED_INQUIRY" if whatsapp_opt_in else "MISSING_EXPLICIT_OPT_IN"
        else:
            whatsapp_opt_in = bool(explicit_opt_in)
            consent_Status = "OPTED_IN" if whatsapp_opt_in else "OPTED_OUT"

        # Created timestamp parsing
        raw_created = graph_lead_data.get("created_time") or wh.get("created_time")
        created_dt = utc_now()
        if isinstance(raw_created, (int, float)):
            created_dt = datetime.fromtimestamp(float(raw_created), tz=timezone.utc)
        elif isinstance(raw_created, str):
            try:
                if raw_created.isdigit():
                    created_dt = datetime.fromtimestamp(float(raw_created), tz=timezone.utc)
                else:
                    # Handle +0000 suffix from Meta Graph API
                    iso_str = raw_created.replace("+0000", "+00:00")
                    created_dt = datetime.fromisoformat(iso_str)
            except Exception:
                created_dt = utc_now()

        lead_id = str(graph_lead_data.get("id") or wh.get("leadgen_id") or "").strip()
        form_id = str(graph_lead_data.get("form_id") or wh.get("form_id") or "").strip() or None
        ad_id = str(graph_lead_data.get("ad_id") or wh.get("ad_id") or "").strip() or None
        adgroup_id = str(graph_lead_data.get("adset_id") or wh.get("adgroup_id") or "").strip() or None
        campaign_id = str(graph_lead_data.get("campaign_id") or wh.get("campaign_id") or "").strip() or None
        page_id = str(wh.get("page_id") or graph_lead_data.get("page_id") or "").strip() or None
        platform = str(graph_lead_data.get("platform") or wh.get("platform") or "facebook").lower()

        return {
            "meta_lead_id": lead_id,
            "meta_form_id": form_id,
            "meta_ad_id": ad_id,
            "meta_adgroup_id": adgroup_id,
            "meta_campaign_id": campaign_id,
            "meta_page_id": page_id,
            "full_name": str(full_name).strip(),
            "phone": normalized_phone,
            "raw_phone": str(raw_phone) if raw_phone else None,
            "email": str(email).strip() if email else None,
            "city": str(city).strip() if city else None,
            "platform": "instagram" if "ig" in platform or "instagram" in platform else "facebook",
            "whatsapp_opt_in": whatsapp_opt_in,
            "consent_status": consent_Status,
            "consent_source": consent_source,
            "consent_text": consent_text,
            "meta_created_time": created_dt,
            "raw_field_data": raw_map,
        }


meta_service = MetaService()
