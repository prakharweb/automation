# Space Consultant – Meta Ads + DoubleTick Lead Automation Platform

A complete, production-ready full-stack lead automation platform for **Space Consultant** that captures leads in real time from **Facebook & Instagram Meta Instant Lead Forms**, deterministically identifies the originating advertisement campaign, stores normalized records in **Neon PostgreSQL**, and automatically sends campaign-specific **WhatsApp Business template messages and PDF brochures** via the **DoubleTick REST API**.

---

## 1. Key Capabilities & Campaign Routing Matrix

| Campaign Example | Purpose Key | Default Approved Template | Automated WhatsApp Payload & Attachments |
| :--- | :--- | :--- | :--- |
| **Campaign A: Hospital for Sale** | `hospital_for_sale` | `hospital_enquiry` | Location, operational beds, facilities, specialities & confidential Hospital Information Memorandum PDF |
| **Campaign B: Doctor Recruitment** | `doctor_recruitment` | `doctor_recruitment` | Job title, department, hospital location, compensation band & MCI/NMC eligibility criteria |
| **Campaign C: Healthcare Recruitment** | `healthcare_recruitment` | `healthcare_job_information` | ICU Nursing / Hospital Ops role summary, eligibility & online application link |
| **Campaign D: Hospital Property** | `hospital_property` | `hospital_property_info` | Institutional hospital plot / built-to-suit medical building specifications & floor-plan PDF |
| **Campaign E: Real Estate** | `real_estate` | `real_estate_brochure` | Commercial medical plaza & diagnostic suite brochure + site visit booking prompt |
| **Unmapped / Unknown Campaign** | `unmapped` | *None (Safety Guardrail)* | Placed in `MANUAL_REVIEW` queue — **never** sends an unrelated WhatsApp message |

---

## 2. Official API Grounding & Documentation Links

- **Meta Marketing & Graph API**:
  - [Meta Webhooks for Leadgen (`GET` & `POST /webhooks/meta`)](https://developers.facebook.com/docs/graph-api/webhooks/getting-started/webhooks-for-leadgen/)
  - [Retrieving Lead Details from Graph API (`GET /{leadgen_id}`)](https://developers.facebook.com/docs/marketing-api/guides/lead-ads/retrieving/v2.8/)
  - [Page Leadgen Forms Edge (`GET /{page_id}/leadgen_forms`)](https://developers.facebook.com/docs/graph-api/reference/page/leadgen_forms/)
  - [Page Subscribed Apps Edge (`POST /{page_id}/subscribed_apps`)](https://developers.facebook.com/docs/graph-api/reference/page/subscribed_apps/)
- **DoubleTick WhatsApp Business API**:
  - [Getting Started with DoubleTick API](https://docs.doubletick.io/docs/getting-started)
  - [Send WhatsApp Template Message (`POST https://public.doubletick.io/whatsapp/message/template`)](https://docs.doubletick.io/docs/template-messages)
  - [Send WhatsApp Text Messages (`POST https://public.doubletick.io/whatsapp/message/text`)](https://docs.doubletick.io/docs/text-messages)
  - [Send WhatsApp Image Messages (`POST https://public.doubletick.io/whatsapp/message/image`)](https://docs.doubletick.io/docs/image-messages)
  - [Send WhatsApp Document Messages (`POST https://public.doubletick.io/whatsapp/message/document`)](https://docs.doubletick.io/docs/document-messages)
  - [Getting Started with DoubleTick Webhooks (`MESSAGE_RECEIVED`, `MESSAGE_STATUS_UPDATE`)](https://docs.doubletick.io/docs/getting-started-with-doubletick-webhooks)
  - [Register New Webhook in DoubleTick](https://docs.doubletick.io/docs/register-new-webhook)

---

## 3. Repository Architecture

```text
space-consultant-automation/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point, CORS, rate limiter, startup seeding
│   │   ├── config.py                # Environment configuration & Neon PostgreSQL SSL normalization
│   │   ├── database.py              # SQLAlchemy engine/session + automatic SQLite test fallback
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── entities.py          # All 17 normalized PostgreSQL tables
│   │   ├── schemas/
│   │   │   └── api_schemas.py       # Pydantic request/response models
│   │   ├── routers/
│   │   │   ├── meta.py              # /api/meta/* endpoints
│   │   │   ├── doubletick.py        # /api/doubletick/* endpoints
│   │   │   ├── campaigns.py         # /api/campaigns/* CRUD endpoints
│   │   │   ├── leads.py             # /api/leads/* search, filter, CSV export, assign, resend
│   │   │   ├── messages.py          # /api/templates, /api/messages, /api/followups
│   │   │   ├── dashboard.py         # /api/health, /api/dashboard/stats, /api/auth, /api/users, /api/settings
│   │   │   └── webhooks.py          # GET/POST /webhooks/meta & POST /webhooks/doubletick
│   │   ├── services/
│   │   │   ├── meta_service.py      # Meta Graph API lead retrieval & field extraction
│   │   │   ├── doubletick_service.py# Official DoubleTick template/text/image/document & webhook service
│   │   │   ├── campaign_service.py  # Deterministic Campaign-Wise Automation Engine
│   │   │   ├── lead_service.py      # Idempotent lead ingestion & consent tracking
│   │   │   └── ai_service.py        # Optional bilingual (EN/HI) Gemini AI reply service
│   │   ├── workers/
│   │   │   ├── followup_worker.py   # Persistent 24h/72h follow-up scheduler & CLI worker
│   │   │   └── lead_processor.py    # Webhook retry processor
│   │   ├── security/
│   │   │   └── auth.py              # PBKDF2 hashing, JWT tokens, RBAC, HMAC webhook verification
│   │   └── utils/
│   │       ├── logger.py            # Sensitive credential & phone masking logger
│   │       ├── phone.py             # E.164 phone number normalization
│   │       ├── orm_compat.py        # Lightweight SQLite ORM compatibility shim for offline testing
│   │       └── seed_data.py         # Non-destructive initial data seeding
│   ├── migrations/
│   │   ├── env.py
│   │   ├── schema.sql               # Full PostgreSQL DDL for all 17 tables
│   │   └── versions/
│   │       └── 0001_initial_space_consultant_schema.py
│   ├── tests/
│   │   └── test_platform.py         # 16 automated unit & integration tests (mocked external APIs)
│   ├── alembic.ini
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/              # SetupWizardModal.jsx (7 steps), LeadDetailModal.jsx
│   │   ├── context/                 # AuthContext.jsx
│   │   ├── layouts/                 # DashboardLayout.jsx (9 navigation modules)
│   │   ├── pages/                   # Dashboard, Meta, Campaigns, Leads, Templates, Messages, Followups, Settings, Users, Login
│   │   ├── services/                # api.js
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── index.html
│   ├── netlify.toml
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── .env.example
├── docs/
│   └── WEBHOOK_AND_DEPLOYMENT_GUIDE.md
├── render.yaml
├── .env.example
├── .gitignore
└── README.md
```

---

## 4. Quick Start & Local Development

### A. Backend Setup
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your DATABASE_URL, META_*, and DOUBLETICK_* secrets

# Run database migrations (for PostgreSQL)
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### B. Run Automated Test Suite (16 Test Cases)
```bash
cd backend
PYTHONPATH=. python3 -m unittest discover -s tests -p "test_*.py" -v
```

### C. Frontend Setup
```bash
cd frontend
cp .env.example .env
# Set VITE_API_URL=http://localhost:8000 for local development
npm install
npm run dev
```

See [`docs/WEBHOOK_AND_DEPLOYMENT_GUIDE.md`](docs/WEBHOOK_AND_DEPLOYMENT_GUIDE.md) for complete Render, Neon PostgreSQL, Netlify, Meta Webhook, and DoubleTick Webhook setup instructions.
