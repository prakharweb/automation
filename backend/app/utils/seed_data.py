"""
Non-Destructive Database Initializer & Seed Data (app/utils/seed_data.py)
Preserves all existing production database data and only seeds default admin/staff users,
Meta pages/forms, approved WhatsApp templates, and the 5 Space Consultant campaign automations
when tables are empty.
"""
from datetime import timedelta
from app.config import settings
from app.database import Base, Session, engine
from app.models import (
    AdAccount,
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
    WhatsAppTemplate,
    utc_now,
)
from app.security.auth import hash_password
from app.utils.logger import get_logger

logger = get_logger("seed_data")


def init_and_seed_db(db: Session, seed_sample_leads: bool = True) -> None:
    Base.metadata.create_all(bind=engine)

    # 1. Seed Users (if none exist)
    existing_admin = db.query(User).filter(User.email == settings.INITIAL_ADMIN_EMAIL).first()
    if not existing_admin:
        admin_user = User(
            email=settings.INITIAL_ADMIN_EMAIL,
            full_name=settings.INITIAL_ADMIN_NAME,
            hashed_password=hash_password(settings.INITIAL_ADMIN_PASSWORD),
            role="admin",
            phone="+919810000001",
            department="Executive Management",
            is_active=True,
        )
        exec_1 = User(
            email="rohit.verma@spaceconsultant.in",
            full_name="Rohit Verma (Hospital M&A Advisor)",
            hashed_password=hash_password("SpaceExec@2026!"),
            role="executive",
            phone="+919810000002",
            department="Hospital Mergers & Property Advisory",
            is_active=True,
        )
        exec_2 = User(
            email="dr.neha.kapoor@spaceconsultant.in",
            full_name="Dr. Neha Kapoor (Medical Recruitment Head)",
            hashed_password=hash_password("SpaceExec@2026!"),
            role="manager",
            phone="+919810000003",
            department="Doctor & Healthcare Recruitment",
            is_active=True,
        )
        exec_3 = User(
            email="ankit.mehta@spaceconsultant.in",
            full_name="Ankit Mehta (Commercial Real Estate Lead)",
            hashed_password=hash_password("SpaceExec@2026!"),
            role="executive",
            phone="+919810000004",
            department="Commercial & Healthcare Real Estate",
            is_active=True,
        )
        db.add_all([admin_user, exec_1, exec_2, exec_3])
        db.commit()
        db.refresh(admin_user)
        db.refresh(exec_1)
        db.refresh(exec_2)
        db.refresh(exec_3)

    # 2. Seed Meta Account, Facebook Pages & Ad Accounts
    if db.query(MetaAccount).count() == 0:
        meta_acc = MetaAccount(
            app_id=settings.META_APP_ID or "148920384756102",
            app_name="Space Consultant Meta Lead Automation App",
            business_id="892019283746501",
            access_token_masked="EAAB...9xQ",
            token_status="connected",
            scopes=[
                "leads_retrieval",
                "pages_manage_metadata",
                "pages_show_list",
                "pages_read_engagement",
                "pages_manage_ads",
                "ads_management",
            ],
            last_synced_at=utc_now(),
        )
        db.add(meta_acc)
        db.commit()
        db.refresh(meta_acc)

        page_1 = FacebookPage(
            meta_account_id=meta_acc.id,
            page_id="104928374650192",
            page_name="Space Consultant - Hospital M&A & Healthcare Advisory",
            category="Medical & Health Consultant",
            page_access_token_masked="EAAB...p1A",
            webhook_subscribed=True,
            is_active=True,
        )
        page_2 = FacebookPage(
            meta_account_id=meta_acc.id,
            page_id="104928374650199",
            page_name="Space Consultant - Doctor & Healthcare Careers",
            category="Recruiter / Medical Staffing",
            page_access_token_masked="EAAB...p2B",
            webhook_subscribed=True,
            is_active=True,
        )
        ad_acc = AdAccount(
            meta_account_id=meta_acc.id,
            ad_account_id="act_1029384756",
            name="Space Consultant Primary Ad Account (INR)",
            currency="INR",
            timezone_name="Asia/Kolkata",
            account_status="ACTIVE",
        )
        db.add_all([page_1, page_2, ad_acc])
        db.commit()

    # 3. Seed Approved WhatsApp Templates (5 core + follow-up templates)
    if db.query(WhatsAppTemplate).count() == 0:
        templates_data = [
            WhatsAppTemplate(
                template_name="hospital_enquiry",
                language="en",
                category="UTILITY",
                purpose="hospital_for_sale",
                header_type="DOCUMENT",
                header_text="Hospital Information Memorandum",
                body_text=(
                    "Hello {{1}}, thank you for your enquiry with *Space Consultant* regarding *{{2}}*. "
                    "Key Highlights: {{3}}. We have attached the confidential Hospital Profile PDF. "
                    "Reply with your preferred call time or type STOP to opt out."
                ),
                footer_text="Space Consultant • Healthcare M&A Advisory",
                variables_schema=["full_name", "campaign_name", "facility_summary"],
                buttons_schema=[{"type": "URL", "parameter": "https://spaceconsultant.in/hospitals-for-sale"}],
                approval_status="APPROVED",
                is_active=True,
            ),
            WhatsAppTemplate(
                template_name="doctor_recruitment",
                language="en",
                category="UTILITY",
                purpose="doctor_recruitment",
                header_type="NONE",
                body_text=(
                    "Dear Dr. {{1}}, thank you for applying via *Space Consultant* for *{{2}}*. "
                    "Role & Eligibility Summary: {{3}}. Please share your updated CV here on WhatsApp "
                    "or schedule a confidential briefing with our Medical Recruitment Desk."
                ),
                footer_text="Space Consultant • Medical Careers Division",
                variables_schema=["full_name", "campaign_name", "role_summary"],
                buttons_schema=[{"type": "URL", "parameter": "https://spaceconsultant.in/doctor-careers"}],
                approval_status="APPROVED",
                is_active=True,
            ),
            WhatsAppTemplate(
                template_name="healthcare_job_information",
                language="en",
                category="UTILITY",
                purpose="healthcare_recruitment",
                header_type="NONE",
                body_text=(
                    "Hello {{1}}, thank you for your interest in *{{2}}* through *Space Consultant*. "
                    "Position & Application Details: {{3}}. Click below to complete your application "
                    "or reply with your qualification details."
                ),
                footer_text="Space Consultant • Healthcare Staffing",
                variables_schema=["full_name", "campaign_name", "job_details"],
                buttons_schema=[{"type": "URL", "parameter": "https://spaceconsultant.in/healthcare-jobs"}],
                approval_status="APPROVED",
                is_active=True,
            ),
            WhatsAppTemplate(
                template_name="hospital_property_info",
                language="en",
                category="UTILITY",
                purpose="hospital_property",
                header_type="DOCUMENT",
                header_text="Hospital Plot & Building Dossier",
                body_text=(
                    "Hello {{1}}, thank you for contacting *Space Consultant* regarding *{{2}}*. "
                    "Property Specifications: {{3}}. Please find the attached Zoning & Floor Plan brochure."
                ),
                footer_text="Space Consultant • Healthcare Infrastructure",
                variables_schema=["full_name", "campaign_name", "property_specs"],
                buttons_schema=[{"type": "URL", "parameter": "https://spaceconsultant.in/hospital-properties"}],
                approval_status="APPROVED",
                is_active=True,
            ),
            WhatsAppTemplate(
                template_name="real_estate_brochure",
                language="en",
                category="UTILITY",
                purpose="real_estate",
                header_type="DOCUMENT",
                header_text="Commercial Property Brochure",
                body_text=(
                    "Hello {{1}}, thank you for your enquiry on *{{2}}* with *Space Consultant*. "
                    "Project Overview: {{3}}. Review the attached brochure and reply 'VISIT' to book a site tour."
                ),
                footer_text="Space Consultant • Commercial Real Estate",
                variables_schema=["full_name", "campaign_name", "project_overview"],
                buttons_schema=[{"type": "URL", "parameter": "https://spaceconsultant.in/real-estate"}],
                approval_status="APPROVED",
                is_active=True,
            ),
            WhatsAppTemplate(
                template_name="hospital_enquiry_followup_24h",
                language="en",
                category="UTILITY",
                purpose="followup",
                header_type="NONE",
                body_text=(
                    "Hello {{1}}, following up from *Space Consultant* on your enquiry for *{{2}}*. "
                    "Would you like to schedule a brief 10-minute call with our Healthcare M&A Advisor today? "
                    "Reply YES or STOP to opt out."
                ),
                footer_text="Space Consultant • Reply STOP to opt out",
                variables_schema=["full_name", "campaign_name", "summary"],
                buttons_schema=[],
                approval_status="APPROVED",
                is_active=True,
            ),
        ]
        db.add_all(templates_data)
        db.commit()

    # 4. Seed the 5 Core Space Consultant Campaigns, Lead Forms & CampaignAutomations
    if db.query(Campaign).count() == 0:
        campaigns_spec = [
            {
                "meta_campaign_id": "2385910000101",
                "page_id": "104928374650192",
                "meta_form_id": "900100200301",
                "form_name": "Hospital for Sale - Investor & Doctor Buyer Instant Form",
                "name": "Campaign A - 100 Bed Multispeciality Hospital for Sale (Delhi NCR)",
                "purpose": "hospital_for_sale",
                "template_name": "hospital_enquiry",
                "pdf_url": "https://spaceconsultant.in/assets/brochures/100_bed_hospital_delhi_ncr.pdf",
                "pdf_filename": "100_Bed_Hospital_Information_Memorandum.pdf",
                "website_url": "https://spaceconsultant.in/hospitals-for-sale/delhi-ncr-100-bed",
                "executive_name": "Rohit Verma (Hospital M&A Advisor)",
                "details": {
                    "location": "Sector 44, Gurugram / Delhi NCR",
                    "facilities": "100 Operational Beds, 4 Modular OTs, 22 ICU Beds, Cath Lab, CT/MRI, NABH Accredited",
                    "specialities": "Cardiology, Orthopedics, Laparoscopic Surgery, Mother & Child, Nephrology",
                    "summary": "100-Bed NABH Multispeciality Hospital in Gurugram (4 Modular OTs, 22 ICU Beds, Cath Lab)",
                },
            },
            {
                "meta_campaign_id": "2385910000102",
                "page_id": "104928374650199",
                "meta_form_id": "900100200302",
                "form_name": "Doctor Recruitment - Consultant & Super Specialist Form",
                "name": "Campaign B - Senior Consultant Doctor Recruitment (Cardiology & Ortho)",
                "purpose": "doctor_recruitment",
                "template_name": "doctor_recruitment",
                "pdf_url": "https://spaceconsultant.in/assets/brochures/doctor_recruitment_dossier.pdf",
                "pdf_filename": "Senior_Consultant_Doctor_JD_Eligibility.pdf",
                "website_url": "https://spaceconsultant.in/doctor-careers/senior-consultant",
                "executive_name": "Dr. Neha Kapoor (Medical Recruitment Head)",
                "details": {
                    "job_title": "Senior Consultant - Interventional Cardiology & Orthopedics",
                    "department": "Cardiac Sciences & Joint Replacement",
                    "location": "Tier-1 NABH Hospitals across Delhi NCR, Jaipur & Chandigarh",
                    "salary_band": "INR 4.5L - 8.5L/month + Revenue Share (as per hospital policy)",
                    "eligibility": "MD/MS/DM/MCh/DNB with 5+ years post-PG experience & valid MCI/NMC registration",
                    "summary": "Sr. Consultant (Cardiology/Ortho) | Delhi NCR & Jaipur | MD/DM/MCh 5+ Yrs | INR 4.5L-8.5L/mo",
                },
            },
            {
                "meta_campaign_id": "2385910000103",
                "page_id": "104928374650199",
                "meta_form_id": "900100200303",
                "form_name": "Healthcare Recruitment - Nursing & Hospital Operations Form",
                "name": "Campaign C - Healthcare & ICU Nursing Recruitment Drive",
                "purpose": "healthcare_recruitment",
                "template_name": "healthcare_job_information",
                "pdf_url": "https://spaceconsultant.in/assets/brochures/healthcare_nursing_jobs.pdf",
                "pdf_filename": "Healthcare_Staffing_Job_Details.pdf",
                "website_url": "https://spaceconsultant.in/healthcare-jobs/apply",
                "executive_name": "Dr. Neha Kapoor (Medical Recruitment Head)",
                "details": {
                    "job_title": "ICU Nursing Officer, Hospital Administrator & NABH Quality Manager",
                    "department": "Critical Care Nursing & Hospital Operations",
                    "location": "Noida, Faridabad & Lucknow Multispeciality Hospitals",
                    "eligibility": "B.Sc Nursing / GNM / MHA with 2+ years hospital experience",
                    "application_link": "https://spaceconsultant.in/healthcare-jobs/apply",
                    "summary": "ICU Nursing Officers & Hospital Managers (Noida/Lucknow) | B.Sc/GNM/MHA 2+ Yrs | Apply Online",
                },
            },
            {
                "meta_campaign_id": "2385910000104",
                "page_id": "104928374650192",
                "meta_form_id": "900100200304",
                "form_name": "Hospital Property - Institutional Plot & Built-to-Suit Form",
                "name": "Campaign D - Institutional Hospital Plot & Lease Building (Noida Expressway)",
                "purpose": "hospital_property",
                "template_name": "hospital_property_info",
                "pdf_url": "https://spaceconsultant.in/assets/brochures/hospital_property_noida.pdf",
                "pdf_filename": "Hospital_Plot_Building_Specifications.pdf",
                "website_url": "https://spaceconsultant.in/hospital-properties/noida-expressway",
                "executive_name": "Rohit Verma (Hospital M&A Advisor)",
                "details": {
                    "location": "Noida-Greater Noida Expressway, Institutional Sector",
                    "property_specs": "2.5 Acre CLU-Approved Hospital Plot / 85,000 sq.ft. Warm-Shell Medical Building",
                    "summary": "2.5 Acre Institutional Hospital Plot & 85,000 sq.ft. Medical Building on Noida Expressway",
                },
            },
            {
                "meta_campaign_id": "2385910000105",
                "page_id": "104928374650192",
                "meta_form_id": "900100200305",
                "form_name": "Real Estate - Commercial Medical Suites & Diagnostic Hub Form",
                "name": "Campaign E - Commercial Medical Plaza & Polyclinic Suites (South Delhi)",
                "purpose": "real_estate",
                "template_name": "real_estate_brochure",
                "pdf_url": "https://spaceconsultant.in/assets/brochures/south_delhi_medical_plaza.pdf",
                "pdf_filename": "South_Delhi_Medical_Plaza_Brochure.pdf",
                "website_url": "https://spaceconsultant.in/real-estate/south-delhi-medical-plaza",
                "executive_name": "Ankit Mehta (Commercial Real Estate Lead)",
                "details": {
                    "location": "Greater Kailash / Ring Road Corridor, South Delhi",
                    "property_specs": "Freehold Commercial Diagnostic & Polyclinic Suites (1,800 - 12,000 sq.ft.) with Lift & Power Backup",
                    "summary": "Freehold Commercial Diagnostic & Polyclinic Suites (1,800-12,000 sq.ft.) in South Delhi",
                },
            },
        ]

        for item in campaigns_spec:
            camp = Campaign(
                meta_campaign_id=item["meta_campaign_id"],
                ad_account_id="act_1029384756",
                page_id=item["page_id"],
                name=item["name"],
                purpose=item["purpose"],
                objective="OUTCOME_LEADS",
                status="ACTIVE",
                description=item["details"]["summary"],
            )
            db.add(camp)
            db.commit()
            db.refresh(camp)

            form = LeadForm(
                meta_form_id=item["meta_form_id"],
                page_id=item["page_id"],
                campaign_id=camp.id,
                name=item["form_name"],
                locale="en_US",
                status="ACTIVE",
                questions_schema=[
                    {"key": "full_name", "label": "Full Name"},
                    {"key": "phone_number", "label": "WhatsApp / Mobile Number"},
                    {"key": "email", "label": "Email Address"},
                    {"key": "city", "label": "City / Location"},
                    {"key": "whatsapp_opt_in", "label": "Receive brochure & details on WhatsApp"},
                ],
                consent_field_name="whatsapp_opt_in",
            )
            db.add(form)

            auto = CampaignAutomation(
                campaign_id=camp.id,
                campaign_name=item["name"],
                meta_campaign_id=item["meta_campaign_id"],
                facebook_page_id=item["page_id"],
                lead_form_id=item["meta_form_id"],
                campaign_purpose=item["purpose"],
                whatsapp_template_name=item["template_name"],
                template_language="en",
                template_variables={
                    "placeholders": [
                        "{full_name}",
                        item["name"],
                        item["details"]["summary"],
                    ],
                    "details": item["details"],
                },
                auto_reply_enabled=True,
                pdf_brochure_url=item["pdf_url"],
                pdf_filename=item["pdf_filename"],
                website_url=item["website_url"],
                followup_config={
                    "enabled": True,
                    "step_2_delay_hours": 24,
                    "step_2_template": "hospital_enquiry_followup_24h",
                    "step_3_delay_hours": 72,
                    "step_3_template": "hospital_enquiry_followup_24h",
                },
                assignment_config={
                    "default_executive_name": item["executive_name"],
                    "strategy": "campaign_specialist",
                },
                campaign_knowledge=item["details"],
            )
            db.add(auto)
            db.commit()

    # 5. Seed Default System Settings
    if db.query(SystemSetting).count() == 0:
        db.add_all(
            [
                SystemSetting(
                    setting_key="whatsapp_compliance",
                    setting_value={
                        "require_explicit_consent": settings.WHATSAPP_REQUIRE_EXPLICIT_CONSENT,
                        "enforce_24h_service_window": True,
                        "honor_stop_unsubscribe_immediately": True,
                        "global_automation_pause": False,
                    },
                    description="WhatsApp Business Platform messaging compliance controls",
                    updated_by="system",
                ),
                SystemSetting(
                    setting_key="ai_reply_config",
                    setting_value={
                        "enabled": settings.AI_REPLY_ENABLED,
                        "model": settings.GEMINI_MODEL,
                        "supported_languages": ["en", "hi"],
                        "strict_grounding_only": True,
                    },
                    description="Optional Gemini AI bilingual auto-reply settings",
                    updated_by="system",
                ),
                SystemSetting(
                    setting_key="followup_engine_config",
                    setting_value={
                        "enabled": True,
                        "step_2_hours": 24,
                        "step_3_hours": 72,
                        "stop_on_reply": True,
                        "stop_on_converted": True,
                        "stop_on_opt_out": True,
                    },
                    description="Persistent background follow-up scheduler settings",
                    updated_by="system",
                ),
            ]
        )
        db.commit()

    # 6. Seed realistic initial leads, message logs & follow-ups if empty (so dashboard is populated on first load)
    if seed_sample_leads and db.query(Lead).count() == 0:
        now = utc_now()
        autos = db.query(CampaignAutomation).all()
        auto_by_purpose = {a.campaign_purpose: a for a in autos}

        sample_leads_spec = [
            {
                "meta_lead_id": "lead_meta_8800101",
                "full_name": "Dr. Rajeshwar Singhania",
                "phone": "+919811122233",
                "email": "dr.singhania@medcaregroup.in",
                "city": "Gurugram",
                "platform": "facebook",
                "purpose": "hospital_for_sale",
                "lead_status": "INTERESTED",
                "message_status": "READ",
                "has_replied": True,
                "notes": "Interested in 100-bed Gurugram hospital acquisition; requested balance sheet & site visit.",
            },
            {
                "meta_lead_id": "lead_meta_8800102",
                "full_name": "Dr. Ananya Deshmukh",
                "phone": "+919822233344",
                "email": "ananya.cardio@aiims-alumni.org",
                "city": "New Delhi",
                "platform": "instagram",
                "purpose": "doctor_recruitment",
                "lead_status": "CONVERTED",
                "message_status": "READ",
                "has_replied": True,
                "notes": "DM Cardiology (7 yrs exp); interview scheduled with Fortis partner hospital.",
            },
            {
                "meta_lead_id": "lead_meta_8800103",
                "full_name": "Sister Priya Nair",
                "phone": "+919833344455",
                "email": "priya.nair.icu@gmail.com",
                "city": "Noida",
                "platform": "facebook",
                "purpose": "healthcare_recruitment",
                "lead_status": "CONTACTED",
                "message_status": "DELIVERED",
                "has_replied": False,
                "notes": "B.Sc Nursing with 4 years ICU ventilator experience.",
            },
            {
                "meta_lead_id": "lead_meta_8800104",
                "full_name": "Vikramaditya Malhotra",
                "phone": "+919844455566",
                "email": "v.malhotra@apexinfra.com",
                "city": "Noida",
                "platform": "facebook",
                "purpose": "hospital_property",
                "lead_status": "CONTACTED",
                "message_status": "SENT",
                "has_replied": False,
                "notes": "Evaluating 2.5 acre hospital land parcel on Noida Expressway.",
            },
            {
                "meta_lead_id": "lead_meta_8800105",
                "full_name": "Dr. Kabir Verma",
                "phone": "+919855566677",
                "email": "drkabir@diagnosticsplus.in",
                "city": "South Delhi",
                "platform": "instagram",
                "purpose": "real_estate",
                "lead_status": "INTERESTED",
                "message_status": "READ",
                "has_replied": True,
                "notes": "Looking for 4,500 sq.ft. diagnostic center space in South Delhi.",
            },
        ]

        for idx, item in enumerate(sample_leads_spec):
            auto = auto_by_purpose.get(item["purpose"])
            if not auto:
                continue
            lead = Lead(
                meta_lead_id=item["meta_lead_id"],
                meta_form_id=auto.lead_form_id,
                meta_ad_id=f"ad_{600100 + idx}",
                meta_adgroup_id=f"adset_{500100 + idx}",
                meta_campaign_id=auto.meta_campaign_id,
                meta_page_id=auto.facebook_page_id,
                campaign_id=auto.campaign_id,
                automation_id=auto.id,
                full_name=item["full_name"],
                phone=item["phone"],
                email=item["email"],
                city=item["city"],
                lead_source="meta_instant_form",
                platform=item["platform"],
                campaign_name=auto.campaign_name,
                campaign_purpose=auto.campaign_purpose,
                lead_status=item["lead_status"],
                message_status=item["message_status"],
                assigned_executive_name=(auto.assignment_config or {}).get("default_executive_name"),
                whatsapp_opt_in=True,
                opted_out=False,
                has_replied=item["has_replied"],
                last_inbound_at=now - timedelta(hours=2) if item["has_replied"] else None,
                service_window_expires_at=now + timedelta(hours=22) if item["has_replied"] else None,
                raw_field_data={
                    "full_name": item["full_name"],
                    "phone_number": item["phone"],
                    "email": item["email"],
                    "city": item["city"],
                    "whatsapp_opt_in": "true",
                },
                notes=item["notes"],
                meta_created_time=now - timedelta(hours=5 - idx),
                created_at=now - timedelta(hours=5 - idx),
            )
            db.add(lead)
            db.commit()
            db.refresh(lead)

            db.add(
                LeadConsent(
                    lead_id=lead.id,
                    phone=lead.phone,
                    consent_status="OPTED_IN",
                    consent_source="meta_custom_disclaimer_checkbox",
                    consent_text="Checked WhatsApp communication consent on Meta Instant Form",
                    ip_or_platform=f"Meta Instant Form ({lead.platform})",
                )
            )

            msg_log = MessageLog(
                lead_id=lead.id,
                campaign_id=auto.campaign_id,
                doubletick_message_id=f"dt_msg_seed_{900100 + idx}",
                recipient_phone=lead.phone,
                sender_phone=settings.DOUBLETICK_SENDER or "+919810000000",
                message_type="TEMPLATE",
                template_name=auto.whatsapp_template_name,
                template_language="en",
                variables_payload={
                    "placeholders": [
                        lead.full_name,
                        auto.campaign_name,
                        (auto.template_variables or {}).get("details", {}).get("summary", ""),
                    ]
                },
                content_preview=f"Template '{auto.whatsapp_template_name}' sent to {lead.full_name}",
                media_url=auto.pdf_brochure_url,
                status=item["message_status"],
                sent_at=now - timedelta(hours=5 - idx),
                delivered_at=now - timedelta(hours=4 - idx) if item["message_status"] in ("DELIVERED", "READ") else None,
                read_at=now - timedelta(hours=3 - idx) if item["message_status"] == "READ" else None,
            )
            db.add(msg_log)
            db.commit()

            if not item["has_replied"] and item["lead_status"] != "CONVERTED":
                db.add(
                    FollowupJob(
                        lead_id=lead.id,
                        automation_id=auto.id,
                        step_number=2,
                        template_name="hospital_enquiry_followup_24h",
                        template_language="en",
                        template_variables={"placeholders": [lead.full_name, auto.campaign_name, "Follow-up"]},
                        scheduled_at=now + timedelta(hours=20),
                        status="SCHEDULED",
                    )
                )
            else:
                db.add(
                    IncomingMessage(
                        lead_id=lead.id,
                        external_message_id=f"dt_in_seed_{700100 + idx}",
                        sender_phone=lead.phone,
                        sender_name=lead.full_name,
                        message_type="TEXT",
                        message_text="Thank you for sharing the brochure. Can we schedule a call at 4 PM today?",
                        is_opt_out_command=False,
                        received_at=now - timedelta(hours=2),
                    )
                )
            db.commit()
