# Space Consultant – Webhook, Deployment & Manual Testing Guide

## 1. Meta Lead Ads Webhook Configuration Guide

### Official Documentation References
- [Meta Webhooks for Leadgen Getting Started](https://developers.facebook.com/docs/graph-api/webhooks/getting-started/webhooks-for-leadgen/)
- [Retrieving Leads from Meta Marketing API](https://developers.facebook.com/docs/marketing-api/guides/lead-ads/retrieving/v2.8/)
- [Facebook Page Subscribed Apps Reference](https://developers.facebook.com/docs/graph-api/reference/page/subscribed_apps/)
- [Facebook Page Leadgen Forms Reference](https://developers.facebook.com/docs/graph-api/reference/page/leadgen_forms/)

### Required Meta App Permissions
Request and configure the following permissions in your Meta Developer App (Business type) and System User token:
1. `leads_retrieval` — Required to read submitted Instant Form lead field data via `GET /{leadgen_id}`.
2. `pages_manage_metadata` — Required to subscribe the Facebook Page to the `leadgen` webhook edge.
3. `pages_show_list` — Required to list connected Facebook Pages (`/me/accounts`).
4. `pages_read_engagement` — Required alongside `leads_retrieval` to read Page-level lead events.
5. `pages_manage_ads` — Required to access Page lead generation forms.
6. `ads_management` — Required to read `campaign_id`, `ad_id`, and `adgroup_id` on ad-generated leads.

### Step-by-Step Meta Webhook Setup
1. Open the Meta App Dashboard → **Webhooks** product.
2. Select **Page** from the object dropdown and click **Subscribe to this object**.
3. Enter your deployed Render callback URL and verify token:
   - **Callback URL**: `https://YOUR-RENDER-BACKEND.onrender.com/webhooks/meta`
   - **Verify Token**: Must match your `META_VERIFY_TOKEN` environment variable on Render.
4. Click **Verify and Save** (FastAPI handles `GET /webhooks/meta` and echoes `hub.challenge`).
5. Scroll to the `leadgen` field and click **Subscribe**.
6. Subscribe your Facebook Page to your app's webhook notifications:
   ```bash
   curl -i -X POST "https://graph.facebook.com/v21.0/{PAGE_ID}/subscribed_apps?subscribed_fields=leadgen&access_token={PAGE_ACCESS_TOKEN}"
   ```

---

## 2. DoubleTick WhatsApp Webhook & API Configuration Guide

### Official Documentation References
- [DoubleTick Getting Started](https://docs.doubletick.io/docs/getting-started)
- [DoubleTick Send WhatsApp Template Message](https://docs.doubletick.io/docs/template-messages) (`POST https://public.doubletick.io/whatsapp/message/template`)
- [DoubleTick Send WhatsApp Text Messages](https://docs.doubletick.io/docs/text-messages) (`POST https://public.doubletick.io/whatsapp/message/text`)
- [DoubleTick Send WhatsApp Image Messages](https://docs.doubletick.io/docs/image-messages) (`POST https://public.doubletick.io/whatsapp/message/image`)
- [DoubleTick Send WhatsApp Document Messages](https://docs.doubletick.io/docs/document-messages) (`POST https://public.doubletick.io/whatsapp/message/document`)
- [DoubleTick Getting Started with Webhooks](https://docs.doubletick.io/docs/getting-started-with-doubletick-webhooks)
- [DoubleTick Register New Webhook](https://docs.doubletick.io/docs/register-new-webhook)

### Step-by-Step DoubleTick Setup
1. Log into your DoubleTick account → **Settings → Developer API** and copy your Public API Key into `DOUBLETICK_API_KEY` on Render.
2. Set `DOUBLETICK_SENDER` to your registered WhatsApp Business number in international E.164 format (e.g. `+919810000000`).
3. Navigate to **Settings → Webhooks → New Webhook** in DoubleTick:
   - **Webhook URL**: `https://YOUR-RENDER-BACKEND.onrender.com/webhooks/doubletick`
   - **HTTP Method**: `POST`
   - **Authorization**: Select `BEARER` and enter the exact secret configured in `DOUBLETICK_WEBHOOK_SECRET` (or pass it in header `X-Webhook-Secret` / `X-Doubletick-Signature`).
   - **Events to Subscribe**:
     - `MESSAGE_RECEIVED`
     - `MESSAGE_STATUS_UPDATE`
4. Click **Save Webhook**.

---

## 3. Render Backend & Neon PostgreSQL Deployment Guide

1. Create a Neon PostgreSQL 16 project and copy the pooled or direct connection string (`postgresql://user:pass@ep-xyz.aws.neon.tech/space_consultant?sslmode=require`).
2. Push this repository to GitHub.
3. In Render Dashboard, click **New + → Blueprint** and select your GitHub repository (`render.yaml` will automatically configure the web service and follow-up cron job), OR create a **Web Service**:
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3` (`PYTHON_VERSION=3.12.7`)
   - **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt && alembic upgrade head`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/api/health`
4. **Render Free-Tier Limitations & Persistent Scheduling Note**:
   - Render Free Web Services spin down after 15 minutes of inactivity and use an ephemeral filesystem.
   - Because all state (`leads`, `webhook_events`, `followup_jobs`, `message_logs`) is stored in **Neon PostgreSQL**, zero data is lost across container restarts.
   - To ensure 24-hour and 72-hour follow-ups run reliably even if a free instance sleeps, use either:
     - The `space-consultant-followup-cron` service in `render.yaml` (`python -m app.workers.followup_worker --once`), OR
     - An external uptime/cron ping every 10 minutes to `GET /api/health` (to keep the instance warm so the internal `FollowupBackgroundDaemon` thread runs continuously).

---

## 4. Netlify Frontend Deployment Guide

1. Log into Netlify → **Add new site → Import an existing project** → Select your GitHub repository.
2. Configure build settings (also pre-configured in `frontend/netlify.toml`):
   - **Base directory**: `frontend`
   - **Build command**: `npm run build`
   - **Publish directory**: `frontend/dist`
3. Under **Site Configuration → Environment Variables**, add:
   - `VITE_API_URL` = `https://YOUR-RENDER-BACKEND.onrender.com`
4. Click **Deploy site**. Once live, add your Netlify domain (`https://your-site.netlify.app`) to `CORS_ORIGINS` on Render.

---

## 5. GitHub Deployment Commands

```bash
cd space-consultant-automation
git init
git branch -M main
git add .
git status # Verify .env is ignored by .gitignore
git commit -m "feat: Space Consultant Meta Lead Ads + DoubleTick WhatsApp Automation Platform"
git remote add origin https://github.com/YOUR-ORG/space-consultant-automation.git
git push -u origin main
```

---

## 6. Manual End-to-End Verification Procedure (Meta Test Lead + DoubleTick)

1. **Verify Health & Database**:
   ```bash
   curl -s https://YOUR-RENDER-BACKEND.onrender.com/api/health
   ```
2. **Test Meta Webhook Verification Handshake**:
   ```bash
   curl -s "https://YOUR-RENDER-BACKEND.onrender.com/webhooks/meta?hub.mode=subscribe&hub.verify_token=YOUR_META_VERIFY_TOKEN&hub.challenge=123456"
   # Expected output: 123456
   ```
3. **Send a Test Lead via Dashboard Setup Wizard (Step 6) or Meta Lead Ads Testing Tool**:
   - Open [Meta Lead Ads Testing Tool](https://developers.facebook.com/tools/lead-ads-testing), select your Space Consultant Page and Instant Form, and click **Create lead** (or use **Step 6: Test Lead Processing** in the dashboard).
   - Confirm in **Lead Management** that the lead is captured, mapped to the correct campaign purpose, and logged in **Message Logs** with the DoubleTick `messageId`.
4. **Verify Delivery Status & Opt-Out**:
   - Confirm that when the recipient reads the WhatsApp message, DoubleTick's `MESSAGE_STATUS_UPDATE` webhook updates the lead status to `READ`.
   - Reply `STOP` from the test WhatsApp number and confirm that `MESSAGE_RECEIVED` marks the lead `OPTED_OUT` and cancels all scheduled follow-ups in **Follow-up Management**.
