"""
Comprehensive Automated Test Suite (tests/test_platform.py)
Tests all 16 required platform specifications using mocked external API responses
(never sends real WhatsApp messages or hits external live endpoints):
1. Meta webhook verification (GET /webhooks/meta)
2. Invalid signature rejection (POST /webhooks/meta)
3. Valid Meta lead event processing (POST /webhooks/meta)
4. Lead extraction & phone normalization
5. Missing phone number handling
6. Campaign identification (all 5 campaign types + unmapped manual review queue)
7. Duplicate lead prevention (idempotency)
8. DoubleTick API authentication headers
9. Template message payload structure (aligned with official DoubleTick docs)
10. DoubleTick webhook verification (POST /webhooks/doubletick)
11. Incoming message handling (MESSAGE_RECEIVED + 24h service window + follow-up cancellation)
12. Message status updates (MESSAGE_STATUS_UPDATE -> DELIVERED / READ / FAILED)
13. Follow-up scheduling & execution worker
14. Customer opt-out (STOP handling & consent update)
15. Database operations across all 17 normalized tables
16. Admin permissions & role-based access control (RBAC)
"""
import hashlib
import hmac
import json
import os
import unittest
from datetime import timedelta
from unittest.mock import patch

# Configure test environment before importing app modules
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["META_APP_ID"] = "test_meta_app_123"
os.environ["META_APP_SECRET"] = "test_meta_app_secret_key_999"
os.environ["META_VERIFY_TOKEN"] = "space_consultant_verify_token_2026"
os.environ["META_ACCESS_TOKEN"] = "EAAB_mock_page_token_123456"
os.environ["DOUBLETICK_API_KEY"] = "dt_mock_api_key_abcdef123456"
os.environ["DOUBLETICK_SENDER"] = "+919810000000"
os.environ["DOUBLETICK_WEBHOOK_SECRET"] = "dt_webhook_secret_2026"
os.environ["FOLLOWUP_WORKER_ENABLED"] = "false"

from fastapi.testclient import TestClient

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import (
    AdAccount,
    AuditLog,
    Campaign,
    CampaignAutomation,
    FacebookPage,
    FollowupJob,
    IncomingMessage,
    Lead,
    LeadAssignment,
    LeadConsent,
    LeadForm,
    MessageLog,
    MetaAccount,
    SystemSetting,
    User,
    WebhookEvent,
    WhatsAppTemplate,
    utc_now,
)
from app.security.auth import create_access_token
from app.services.campaign_service import CampaignService
from app.services.doubletick_service import DoubleTickService
from app.services.meta_service import MetaService
from app.utils.seed_data import init_and_seed_db
from app.workers.followup_worker import process_due_followups


def compute_meta_sig(body_bytes: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


class SpaceConsultantPlatformTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        settings.META_APP_SECRET = "test_meta_app_secret_key_999"
        settings.META_VERIFY_TOKEN = "space_consultant_verify_token_2026"
        settings.META_ACCESS_TOKEN = "EAAB_mock_page_token_123456"
        settings.DOUBLETICK_API_KEY = "dt_mock_api_key_abcdef123456"
        settings.DOUBLETICK_SENDER = "+919810000000"
        settings.DOUBLETICK_WEBHOOK_SECRET = "dt_webhook_secret_2026"
        cls.client = TestClient(app)

    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        init_and_seed_db(self.db, seed_sample_leads=False)

        admin = self.db.query(User).filter(User.role == "admin").first()
        exec_user = self.db.query(User).filter(User.role == "executive").first()
        self.admin_token = create_access_token(admin.id, admin.email, admin.role)
        self.exec_token = create_access_token(exec_user.id, exec_user.email, exec_user.role)
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        self.exec_headers = {"Authorization": f"Bearer {self.exec_token}"}

    def tearDown(self):
        self.db.close()

    # 1. Meta Webhook Verification
    def test_01_meta_webhook_verification(self):
        # Valid verify_token returns challenge
        resp = self.client.get(
            "/webhooks/meta",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "space_consultant_verify_token_2026",
                "hub.challenge": "987654321",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.text, "987654321")

        # Invalid verify_token is rejected with 403
        bad_resp = self.client.get(
            "/webhooks/meta",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token",
                "hub.challenge": "987654321",
            },
        )
        self.assertEqual(bad_resp.status_code, 403)

    # 2. Invalid Signature Rejection
    def test_02_invalid_meta_signature_rejection(self):
        payload = {
            "object": "page",
            "entry": [
                {
                    "id": "104928374650192",
                    "time": 1700000000,
                    "changes": [
                        {
                            "field": "leadgen",
                            "value": {"leadgen_id": "lead_unverified_1", "campaign_id": "2385910000101"},
                        }
                    ],
                }
            ],
        }
        raw_bytes = json.dumps(payload).encode("utf-8")
        resp = self.client.post(
            "/webhooks/meta",
            content=raw_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=00000000000000000000000000000000",
            },
        )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(self.db.query(Lead).count(), 0)

    # 3. Valid Meta Lead Event End-to-End Processing
    @patch("app.services.meta_service.MetaService.fetch_lead_details_from_graph")
    @patch("app.services.doubletick_service.DoubleTickService._post_with_retry")
    def test_03_valid_meta_lead_event_hospital_for_sale(self, mock_dt_post, mock_graph_fetch):
        mock_graph_fetch.return_value = {
            "id": "lead_hosp_001",
            "created_time": "2026-11-15T10:30:00+0000",
            "ad_id": "ad_111",
            "adset_id": "adset_222",
            "campaign_id": "2385910000101",  # Campaign A: Hospital for Sale
            "form_id": "900100200301",
            "platform": "facebook",
            "field_data": [
                {"name": "full_name", "values": ["Dr. Vikramjit Arora"]},
                {"name": "phone_number", "values": ["9811223344"]},
                {"name": "email", "values": ["vikramjit@arorahospital.in"]},
                {"name": "city", "values": ["Gurugram"]},
                {"name": "whatsapp_opt_in", "values": ["true"]},
            ],
        }
        mock_dt_post.return_value = (
            True,
            201,
            {"status": "SENT", "recipient": "+919811223344", "messageId": "dt_msg_hosp_001"},
        )

        webhook_payload = {
            "object": "page",
            "entry": [
                {
                    "id": "104928374650192",
                    "time": 1700000100,
                    "changes": [
                        {
                            "field": "leadgen",
                            "value": {
                                "leadgen_id": "lead_hosp_001",
                                "page_id": "104928374650192",
                                "form_id": "900100200301",
                                "ad_id": "ad_111",
                                "campaign_id": "2385910000101",
                                "created_time": 1700000100,
                            },
                        }
                    ],
                }
            ],
        }
        raw_bytes = json.dumps(webhook_payload).encode("utf-8")
        sig = compute_meta_sig(raw_bytes, settings.META_APP_SECRET)

        resp = self.client.post(
            "/webhooks/meta",
            content=raw_bytes,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["processed_count"], 1)

        lead = self.db.query(Lead).filter(Lead.meta_lead_id == "lead_hosp_001").first()
        self.assertIsNotNone(lead)
        self.assertEqual(lead.full_name, "Dr. Vikramjit Arora")
        self.assertEqual(lead.phone, "+919811223344")
        self.assertEqual(lead.campaign_purpose, "hospital_for_sale")
        self.assertEqual(lead.message_status, "SENT")
        self.assertEqual(lead.lead_status, "CONTACTED")

        # Verify correct WhatsApp template was used
        msg_log = self.db.query(MessageLog).filter(MessageLog.lead_id == lead.id).first()
        self.assertIsNotNone(msg_log)
        self.assertEqual(msg_log.template_name, "hospital_enquiry")

    # 4. Lead Extraction & Phone Normalization
    def test_04_lead_extraction(self):
        graph_sample = {
            "id": "lead_extract_99",
            "created_time": "2026-11-15T11:00:00+0000",
            "campaign_id": "2385910000102",
            "form_id": "900100200302",
            "ad_id": "ad_999",
            "platform": "ig",
            "field_data": [
                {"name": "first_name", "values": ["Dr. Meera"]},
                {"name": "last_name", "values": ["Krishnan"]},
                {"name": "mobile_number", "values": ["098765 43210"]},
                {"name": "email_address", "values": ["meera.k@med.in"]},
                {"name": "preferred_location", "values": ["Jaipur"]},
            ],
            "custom_disclaimer_responses": [
                {"checkbox_key": "whatsapp_opt_in_consent", "is_checked": "true"}
            ],
        }
        extracted = MetaService.extract_lead_fields(graph_sample)
        self.assertEqual(extracted["full_name"], "Dr. Meera Krishnan")
        self.assertEqual(extracted["phone"], "+919876543210")
        self.assertEqual(extracted["email"], "meera.k@med.in")
        self.assertEqual(extracted["city"], "Jaipur")
        self.assertEqual(extracted["platform"], "instagram")
        self.assertTrue(extracted["whatsapp_opt_in"])
        self.assertEqual(extracted["consent_status"], "OPTED_IN")

    # 5. Missing Phone Number Handling
    @patch("app.services.meta_service.MetaService.fetch_lead_details_from_graph")
    @patch("app.services.doubletick_service.DoubleTickService._post_with_retry")
    def test_05_missing_phone_number(self, mock_dt_post, mock_graph_fetch):
        mock_graph_fetch.return_value = {
            "id": "lead_no_phone_01",
            "campaign_id": "2385910000101",
            "form_id": "900100200301",
            "field_data": [
                {"name": "full_name", "values": ["No Phone Applicant"]},
                {"name": "email", "values": ["nophone@example.com"]},
            ],
        }
        webhook_payload = {
            "object": "page",
            "entry": [
                {
                    "id": "104928374650192",
                    "changes": [{"field": "leadgen", "value": {"leadgen_id": "lead_no_phone_01"}}],
                }
            ],
        }
        raw_bytes = json.dumps(webhook_payload).encode("utf-8")
        sig = compute_meta_sig(raw_bytes, settings.META_APP_SECRET)

        resp = self.client.post(
            "/webhooks/meta",
            content=raw_bytes,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
        )
        self.assertEqual(resp.status_code, 200)
        lead = self.db.query(Lead).filter(Lead.meta_lead_id == "lead_no_phone_01").first()
        self.assertIsNotNone(lead)
        self.assertEqual(lead.lead_status, "INVALID_PHONE")
        self.assertEqual(lead.message_status, "FAILED")
        mock_dt_post.assert_not_called()

    # 6. Campaign Identification Across All 5 Purposes & Unmapped Manual Review Fallback
    @patch("app.services.doubletick_service.DoubleTickService._post_with_retry")
    def test_06_campaign_identification_and_manual_review_queue(self, mock_dt_post):
        mock_dt_post.return_value = (True, 201, {"status": "SENT", "messageId": "dt_test_1"})

        expected_mappings = [
            ("2385910000101", "900100200301", "hospital_for_sale", "hospital_enquiry"),
            ("2385910000102", "900100200302", "doctor_recruitment", "doctor_recruitment"),
            ("2385910000103", "900100200303", "healthcare_recruitment", "healthcare_job_information"),
            ("2385910000104", "900100200304", "hospital_property", "hospital_property_info"),
            ("2385910000105", "900100200305", "real_estate", "real_estate_brochure"),
        ]
        for meta_camp_id, form_id, expected_purpose, expected_tpl in expected_mappings:
            camp, auto, method = CampaignService.identify_campaign_automation(
                self.db, meta_campaign_id=meta_camp_id, meta_form_id=form_id
            )
            self.assertIsNotNone(camp)
            self.assertIsNotNone(auto)
            self.assertEqual(auto.campaign_purpose, expected_purpose)
            self.assertEqual(auto.whatsapp_template_name, expected_tpl)

        # Test Unmapped Campaign -> Must go to MANUAL_REVIEW and NEVER send an unrelated template
        sim_resp = self.client.post(
            "/api/meta/simulate-lead",
            json={
                "leadgen_id": "lead_unknown_camp_777",
                "meta_campaign_id": "9999999999999",
                "meta_form_id": "8888888888888",
                "full_name": "Mystery Buyer",
                "phone": "+919899887766",
            },
            headers=self.admin_headers,
        )
        self.assertEqual(sim_resp.status_code, 200)
        sim_data = sim_resp.json()["data"]
        self.assertFalse(sim_data["campaign_matched"])
        self.assertEqual(sim_data["lead_status"], "MANUAL_REVIEW")
        self.assertEqual(sim_data["message_status"], "MANUAL_REVIEW")
        mock_dt_post.assert_not_called()

    # 7. Duplicate Lead Prevention (Idempotency)
    @patch("app.services.meta_service.MetaService.fetch_lead_details_from_graph")
    @patch("app.services.doubletick_service.DoubleTickService._post_with_retry")
    def test_07_duplicate_lead_prevention(self, mock_dt_post, mock_graph_fetch):
        mock_graph_fetch.return_value = {
            "id": "lead_dup_555",
            "campaign_id": "2385910000102",
            "form_id": "900100200302",
            "field_data": [
                {"name": "full_name", "values": ["Dr. Sameer Joshi"]},
                {"name": "phone_number", "values": ["+919812345678"]},
            ],
        }
        mock_dt_post.return_value = (True, 201, {"status": "SENT", "messageId": "dt_dup_1"})

        webhook_payload = {
            "object": "page",
            "entry": [
                {
                    "id": "104928374650199",
                    "changes": [
                        {
                            "field": "leadgen",
                            "value": {"leadgen_id": "lead_dup_555", "campaign_id": "2385910000102"},
                        }
                    ],
                }
            ],
        }
        raw_bytes = json.dumps(webhook_payload).encode("utf-8")
        sig = compute_meta_sig(raw_bytes, settings.META_APP_SECRET)

        # First delivery
        r1 = self.client.post(
            "/webhooks/meta",
            content=raw_bytes,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
        )
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()["processed_count"], 1)

        # Second duplicate delivery
        r2 = self.client.post(
            "/webhooks/meta",
            content=raw_bytes,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
        )
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["duplicate_count"], 1)
        self.assertEqual(self.db.query(Lead).filter(Lead.meta_lead_id == "lead_dup_555").count(), 1)

    # 8. DoubleTick API Authentication
    def test_08_doubletick_api_authentication(self):
        svc = DoubleTickService(api_key="dt_live_test_key_123", sender_number="+919810000000")
        headers = svc.get_headers()
        self.assertEqual(headers["Authorization"], "dt_live_test_key_123")
        self.assertEqual(headers["Content-Type"], "application/json")

        empty_svc = DoubleTickService(api_key="", sender_number="+919810000000")
        with self.assertRaises(ValueError):
            empty_svc.get_headers()

    # 9. DoubleTick Template Message Payload Structure
    def test_09_doubletick_template_message_payload(self):
        svc = DoubleTickService(api_key="dt_key", sender_number="+919810000000")
        payload = svc.build_template_payload(
            to_phone="9876543210",
            template_name="doctor_recruitment",
            language="en",
            placeholders=["Dr. Neha", "Senior Cardiologist", "MD/DM Cardiology"],
            header={"type": "DOCUMENT", "mediaUrl": "https://spaceconsultant.in/jd.pdf", "filename": "JD.pdf"},
            buttons=[{"type": "URL", "parameter": "https://spaceconsultant.in/apply"}],
        )
        self.assertIn("messages", payload)
        self.assertEqual(len(payload["messages"]), 1)
        msg = payload["messages"][0]
        self.assertEqual(msg["to"], "+919876543210")
        self.assertEqual(msg["from"], "+919810000000")
        self.assertEqual(len(msg["messageId"]), 36)
        self.assertEqual(msg["content"]["templateName"], "doctor_recruitment")
        self.assertEqual(msg["content"]["language"], "en")
        self.assertEqual(
            msg["content"]["templateData"]["body"]["placeholders"],
            ["Dr. Neha", "Senior Cardiologist", "MD/DM Cardiology"],
        )
        self.assertEqual(msg["content"]["templateData"]["header"]["type"], "DOCUMENT")

    # 10. DoubleTick Webhook Verification
    def test_10_doubletick_webhook_verification(self):
        # Reject unauthorized webhook call
        unauth_resp = self.client.post(
            "/webhooks/doubletick",
            json={"event": "MESSAGE_STATUS_UPDATE", "messageId": "m1", "status": "DELIVERED"},
            headers={"Authorization": "Bearer wrong_secret"},
        )
        self.assertEqual(unauth_resp.status_code, 401)

        # Accept valid Bearer secret
        auth_resp = self.client.post(
            "/webhooks/doubletick",
            json={"event": "MESSAGE_STATUS_UPDATE", "messageId": "m1", "status": "DELIVERED"},
            headers={"Authorization": f"Bearer {settings.DOUBLETICK_WEBHOOK_SECRET}"},
        )
        self.assertEqual(auth_resp.status_code, 200)

    # 11. Incoming WhatsApp Message Handling
    @patch("app.services.doubletick_service.DoubleTickService._post_with_retry")
    def test_11_incoming_message_handling(self, mock_dt_post):
        mock_dt_post.return_value = (True, 201, {"status": "SENT", "messageId": "dt_msg_init_11"})
        sim_resp = self.client.post(
            "/api/meta/simulate-lead",
            json={
                "leadgen_id": "lead_inbound_test_11",
                "meta_campaign_id": "2385910000101",
                "full_name": "Dr. Amitabh Sen",
                "phone": "+919811009988",
            },
            headers=self.admin_headers,
        )
        lead_id = sim_resp.json()["data"]["lead_id"]

        # Verify follow-ups were scheduled
        scheduled_before = (
            self.db.query(FollowupJob)
            .filter(FollowupJob.lead_id == lead_id, FollowupJob.status == "SCHEDULED")
            .count()
        )
        self.assertGreater(scheduled_before, 0)

        # Send MESSAGE_RECEIVED webhook from customer
        inbound_payload = {
            "event": "MESSAGE_RECEIVED",
            "payload": {
                "messageId": "wamid.inbound.001",
                "from": "+919811009988",
                "customerName": "Dr. Amitabh Sen",
                "message": {"type": "TEXT", "text": "Please share the hospital valuation details."},
            },
        }
        inc_resp = self.client.post(
            "/webhooks/doubletick",
            json=inbound_payload,
            headers={"Authorization": f"Bearer {settings.DOUBLETICK_WEBHOOK_SECRET}"},
        )
        self.assertEqual(inc_resp.status_code, 200)

        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        self.assertTrue(lead.has_replied)
        self.assertEqual(lead.lead_status, "INTERESTED")
        self.assertIsNotNone(lead.service_window_expires_at)

        # Verify scheduled follow-ups were automatically cancelled on reply
        scheduled_after = (
            self.db.query(FollowupJob)
            .filter(FollowupJob.lead_id == lead_id, FollowupJob.status == "SCHEDULED")
            .count()
        )
        self.assertEqual(scheduled_after, 0)

    # 12. Message Status Updates (DELIVERED -> READ)
    @patch("app.services.doubletick_service.DoubleTickService._post_with_retry")
    def test_12_message_status_updates(self, mock_dt_post):
        mock_dt_post.return_value = (True, 201, {"status": "SENT", "messageId": "dt_track_msg_12"})
        sim_resp = self.client.post(
            "/api/meta/simulate-lead",
            json={
                "leadgen_id": "lead_status_test_12",
                "meta_campaign_id": "2385910000103",
                "full_name": "Nurse Kavita",
                "phone": "+919822001122",
            },
            headers=self.admin_headers,
        )
        lead_id = sim_resp.json()["data"]["lead_id"]

        # Update status to DELIVERED
        r_deliv = self.client.post(
            "/webhooks/doubletick",
            json={
                "event": "MESSAGE_STATUS_UPDATE",
                "payload": {"messageId": "dt_track_msg_12", "status": "DELIVERED"},
            },
            headers={"Authorization": f"Bearer {settings.DOUBLETICK_WEBHOOK_SECRET}"},
        )
        self.assertEqual(r_deliv.status_code, 200)
        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        self.assertEqual(lead.message_status, "DELIVERED")

        # Update status to READ
        r_read = self.client.post(
            "/webhooks/doubletick",
            json={
                "event": "MESSAGE_STATUS_UPDATE",
                "payload": {"messageId": "dt_track_msg_12", "status": "READ"},
            },
            headers={"Authorization": f"Bearer {settings.DOUBLETICK_WEBHOOK_SECRET}"},
        )
        self.assertEqual(r_read.status_code, 200)
        self.db.refresh(lead)
        self.assertEqual(lead.message_status, "READ")

    # 13. Follow-up Scheduling & Persistent Worker Execution
    @patch("app.services.doubletick_service.DoubleTickService._post_with_retry")
    def test_13_followup_scheduling_and_worker(self, mock_dt_post):
        mock_dt_post.return_value = (True, 201, {"status": "SENT", "messageId": "dt_followup_13"})
        sim_resp = self.client.post(
            "/api/meta/simulate-lead",
            json={
                "leadgen_id": "lead_followup_13",
                "meta_campaign_id": "2385910000104",
                "full_name": "Mr. Rakesh Malhotra",
                "phone": "+919833112233",
            },
            headers=self.admin_headers,
        )
        lead_id = sim_resp.json()["data"]["lead_id"]
        jobs = self.db.query(FollowupJob).filter(FollowupJob.lead_id == lead_id).all()
        self.assertEqual(len(jobs), 2)

        # Advance time by 25 hours and run persistent follow-up worker
        future_time = utc_now() + timedelta(hours=25)
        worker_summary = process_due_followups(self.db, now_override=future_time)
        self.assertEqual(worker_summary["sent"], 1)

        step2_job = (
            self.db.query(FollowupJob)
            .filter(FollowupJob.lead_id == lead_id, FollowupJob.step_number == 2)
            .first()
        )
        self.assertEqual(step2_job.status, "COMPLETED")

    # 14. Customer Opt-Out (STOP Keyword)
    @patch("app.services.doubletick_service.DoubleTickService._post_with_retry")
    def test_14_customer_opt_out_stop_handling(self, mock_dt_post):
        mock_dt_post.return_value = (True, 201, {"status": "SENT", "messageId": "dt_optout_14"})
        sim_resp = self.client.post(
            "/api/meta/simulate-lead",
            json={
                "leadgen_id": "lead_optout_14",
                "meta_campaign_id": "2385910000105",
                "full_name": "Mr. OptOut User",
                "phone": "+919844009900",
            },
            headers=self.admin_headers,
        )
        lead_id = sim_resp.json()["data"]["lead_id"]

        # Customer sends "STOP"
        stop_resp = self.client.post(
            "/webhooks/doubletick",
            json={
                "event": "MESSAGE_RECEIVED",
                "payload": {
                    "messageId": "wamid.stop.14",
                    "from": "+919844009900",
                    "message": {"type": "TEXT", "text": "STOP"},
                },
            },
            headers={"Authorization": f"Bearer {settings.DOUBLETICK_WEBHOOK_SECRET}"},
        )
        self.assertEqual(stop_resp.status_code, 200)
        self.assertTrue(stop_resp.json()["result"]["is_opt_out"])

        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        self.assertTrue(lead.opted_out)
        self.assertFalse(lead.whatsapp_opt_in)
        self.assertEqual(lead.lead_status, "OPTED_OUT")

        # Verify manual resend is blocked with HTTP 403 for opted-out lead
        resend_resp = self.client.post(f"/api/leads/{lead_id}/resend", headers=self.admin_headers)
        self.assertEqual(resend_resp.status_code, 403)

    # 15. Database Operations Across All 17 Tables
    def test_15_database_operations_all_17_tables(self):
        models_to_verify = [
            User,
            MetaAccount,
            FacebookPage,
            AdAccount,
            Campaign,
            LeadForm,
            WhatsAppTemplate,
            CampaignAutomation,
            Lead,
            LeadConsent,
            MessageLog,
            IncomingMessage,
            WebhookEvent,
            FollowupJob,
            LeadAssignment,
            SystemSetting,
            AuditLog,
        ]
        for model_cls in models_to_verify:
            cnt = self.db.query(model_cls).count()
            self.assertGreaterEqual(cnt, 0, f"Table {model_cls.__tablename__} query failed")

        self.assertGreaterEqual(self.db.query(Campaign).count(), 5)
        self.assertGreaterEqual(self.db.query(CampaignAutomation).count(), 5)
        self.assertGreaterEqual(self.db.query(WhatsAppTemplate).count(), 5)

    # 16. Admin Permissions & Role-Based Access Control (RBAC)
    def test_16_admin_permissions_rbac(self):
        # Unauthenticated request to protected endpoint returns 401
        unauth = self.client.get("/api/dashboard/stats")
        self.assertEqual(unauth.status_code, 401)

        # Executive can view dashboard stats and leads (200)
        exec_stats = self.client.get("/api/dashboard/stats", headers=self.exec_headers)
        self.assertEqual(exec_stats.status_code, 200)

        # Executive CANNOT create a new campaign automation (403 Forbidden)
        exec_create_camp = self.client.post(
            "/api/campaigns",
            json={
                "name": "Unauthorized Campaign",
                "meta_campaign_id": "777000111",
                "facebook_page_id": "104928374650192",
                "purpose": "real_estate",
                "whatsapp_template_name": "real_estate_brochure",
            },
            headers=self.exec_headers,
        )
        self.assertEqual(exec_create_camp.status_code, 403)

        # Admin CAN create a new campaign automation (201 Created)
        admin_create_camp = self.client.post(
            "/api/campaigns",
            json={
                "name": "Authorized New Diagnostic Center Campaign",
                "meta_campaign_id": "777000222",
                "facebook_page_id": "104928374650192",
                "purpose": "real_estate",
                "whatsapp_template_name": "real_estate_brochure",
            },
            headers=self.admin_headers,
        )
        self.assertEqual(admin_create_camp.status_code, 201)


if __name__ == "__main__":
    unittest.main(verbosity=2)
