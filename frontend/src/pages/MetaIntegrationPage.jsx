import React, { useEffect, useState } from 'react';
import { apiClient } from '../services/api';

export default function MetaIntegrationPage() {
  const [statusData, setStatusData] = useState(null);
  const [pagesData, setPagesData] = useState({ pages: [], ad_accounts: [] });
  const [forms, setForms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState('');

  const [formState, setFormState] = useState({
    app_id: '148920384756102',
    app_name: 'Space Consultant Meta Lead Automation App',
    business_id: '892019283746501',
    page_id: '',
    page_name: '',
    ad_account_id: '',
  });

  const loadAll = async () => {
    setLoading(true);
    try {
      const [sRes, pRes, fRes] = await Promise.all([
        apiClient.getMetaStatus(),
        apiClient.getMetaPages(),
        apiClient.getMetaForms(),
      ]);
      setStatusData(sRes.data);
      setPagesData(pRes.data);
      setForms(fRes.data || []);
    } catch (err) {
      setMsg(`Error loading Meta integration: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const handleConnect = async (e) => {
    e.preventDefault();
    setMsg('');
    try {
      await apiClient.connectMeta(formState);
      setMsg('Meta App & Page connection saved.');
      await loadAll();
    } catch (err) {
      setMsg(`Error: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Meta Marketing API &amp; Instant Lead Ads Webhook Integration
            </h2>
            <p className="text-xs text-slate-500">
              Graph API Version: {statusData?.graph_api_version || 'v21.0'} • Verifies X-Hub-Signature-256 on every webhook event
            </p>
          </div>
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
            {statusData?.connected ? '● Meta App Connected' : '○ Disconnected'}
          </span>
        </div>

        {msg && (
          <div className="p-3 rounded-lg bg-sky-50 border border-sky-200 text-sky-900 text-xs font-medium">
            {msg}
          </div>
        )}

        {/* Webhook Configuration Reference */}
        <div className="p-4 rounded-xl bg-slate-900 text-slate-100 text-xs font-mono space-y-1.5">
          <div className="text-sky-400 font-sans font-semibold">
            Meta Developer Console → Webhooks → Page Object (`leadgen` field):
          </div>
          <div>Callback URL (GET &amp; POST): https://YOUR-RENDER-BACKEND.onrender.com/webhooks/meta</div>
          <div>Verify Token Env Var: META_VERIFY_TOKEN</div>
          <div>HMAC Signature Header: X-Hub-Signature-256 (validated with META_APP_SECRET)</div>
        </div>

        {/* Connect Form */}
        <form onSubmit={handleConnect} className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Meta App ID</label>
            <input
              type="text"
              value={formState.app_id}
              onChange={(e) => setFormState({ ...formState, app_id: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Add Facebook Page ID (Optional)
            </label>
            <input
              type="text"
              value={formState.page_id}
              onChange={(e) => setFormState({ ...formState, page_id: e.target.value })}
              placeholder="e.g. 104928374650205"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Facebook Page Name (Optional)
            </label>
            <input
              type="text"
              value={formState.page_name}
              onChange={(e) => setFormState({ ...formState, page_name: e.target.value })}
              placeholder="Space Consultant Regional Page"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
            />
          </div>
          <div className="sm:col-span-3">
            <button
              type="submit"
              className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold"
            >
              Save Meta Integration Settings
            </button>
          </div>
        </form>
      </div>

      {/* Connected Pages & Ad Accounts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <h3 className="text-sm font-bold text-slate-900 mb-3">
            Connected Facebook Pages ({pagesData.pages?.length || 0})
          </h3>
          <div className="space-y-2.5 text-xs">
            {(pagesData.pages || []).map((p) => (
              <div key={p.id} className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex justify-between items-center">
                <div>
                  <p className="font-semibold text-slate-900">{p.page_name}</p>
                  <p className="font-mono text-slate-500">Page ID: {p.page_id}</p>
                </div>
                <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-semibold">
                  leadgen Subscribed
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <h3 className="text-sm font-bold text-slate-900 mb-3">
            Synchronized Meta Instant Lead Forms ({forms.length})
          </h3>
          <div className="space-y-2.5 text-xs max-h-64 overflow-y-auto">
            {forms.map((f) => (
              <div key={f.id} className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex justify-between items-center">
                <div>
                  <p className="font-semibold text-slate-900">{f.name}</p>
                  <p className="font-mono text-slate-500">
                    Form ID: {f.meta_form_id} • Page: {f.page_id}
                  </p>
                </div>
                <span className="px-2 py-0.5 rounded bg-sky-100 text-sky-800 font-semibold">
                  {f.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
