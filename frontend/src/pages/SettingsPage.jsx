import React, { useEffect, useState } from 'react';
import { apiClient } from '../services/api';

export default function SettingsPage() {
  const [settingsData, setSettingsData] = useState({});
  const [auditLogs, setAuditLogs] = useState([]);
  const [webhooks, setWebhooks] = useState([]);
  const [msg, setMsg] = useState('');

  const loadSettings = async () => {
    try {
      const res = await apiClient.getSettings();
      setSettingsData(res.data.settings || {});
      setAuditLogs(res.data.audit_logs || []);
      setWebhooks(res.data.recent_webhooks || []);
    } catch (err) {
      setMsg(`Error: ${err.message}`);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const toggleSetting = async (groupKey, fieldKey) => {
    const group = settingsData[groupKey] || {};
    const updatedGroup = { ...group, [fieldKey]: !group[fieldKey] };
    try {
      await apiClient.updateSettings({ [groupKey]: updatedGroup });
      setMsg(`Updated ${groupKey}.${fieldKey}`);
      await loadSettings();
    } catch (err) {
      setMsg(`Error: ${err.message}`);
    }
  };

  const compliance = settingsData.whatsapp_compliance || {};
  const aiCfg = settingsData.ai_reply_config || {};
  const followupCfg = settingsData.followup_engine_config || {};

  return (
    <div className="space-y-6">
      {msg && (
        <div className="p-3 rounded-lg bg-sky-50 border border-sky-200 text-sky-900 text-xs font-medium">
          {msg}
        </div>
      )}

      {/* Compliance, AI & Follow-up Toggles */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3 text-xs">
          <h3 className="text-sm font-bold text-slate-900">WhatsApp Business Compliance</h3>
          <div className="flex items-center justify-between">
            <span>Enforce 24h Service Window</span>
            <input
              type="checkbox"
              checked={Boolean(compliance.enforce_24h_service_window ?? true)}
              onChange={() => toggleSetting('whatsapp_compliance', 'enforce_24h_service_window')}
            />
          </div>
          <div className="flex items-center justify-between">
            <span>Require Explicit Form Checkbox</span>
            <input
              type="checkbox"
              checked={Boolean(compliance.require_explicit_consent)}
              onChange={() => toggleSetting('whatsapp_compliance', 'require_explicit_consent')}
            />
          </div>
          <div className="flex items-center justify-between">
            <span>Honor STOP / Unsubscribe Immediately</span>
            <input
              type="checkbox"
              checked={Boolean(compliance.honor_stop_unsubscribe_immediately ?? true)}
              onChange={() => toggleSetting('whatsapp_compliance', 'honor_stop_unsubscribe_immediately')}
            />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3 text-xs">
          <h3 className="text-sm font-bold text-slate-900">Optional Gemini AI Auto-Reply</h3>
          <div className="flex items-center justify-between">
            <span>Enable Bilingual AI Reply (EN/HI)</span>
            <input
              type="checkbox"
              checked={Boolean(aiCfg.enabled)}
              onChange={() => toggleSetting('ai_reply_config', 'enabled')}
            />
          </div>
          <p className="text-slate-500">
            Responds only within the 24-hour customer service window using strictly verified campaign facts. Escalates negotiation or salary queries to a human executive.
          </p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3 text-xs">
          <h3 className="text-sm font-bold text-slate-900">Follow-Up Automation Rules</h3>
          <div className="flex items-center justify-between">
            <span>Follow-up Scheduler Enabled</span>
            <input
              type="checkbox"
              checked={Boolean(followupCfg.enabled ?? true)}
              onChange={() => toggleSetting('followup_engine_config', 'enabled')}
            />
          </div>
          <p className="text-slate-500">
            Step 2: +24 hours • Step 3: +72 hours. Automatically cancels pending jobs when a lead replies, converts, or opts out.
          </p>
        </div>
      </div>

      {/* Recent Webhook Events & Security Audit Logs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <h3 className="text-sm font-bold text-slate-900 mb-3">
            Recent Idempotent Webhook Events ({webhooks.length})
          </h3>
          <div className="space-y-2 max-h-64 overflow-y-auto text-xs">
            {webhooks.map((w) => (
              <div key={w.id} className="p-2.5 bg-slate-50 rounded border border-slate-200 flex justify-between">
                <div>
                  <span className="font-bold uppercase text-sky-700 mr-2">{w.provider}</span>
                  <span className="font-mono text-slate-700">{w.event_type}</span>
                  <p className="text-[10px] font-mono text-slate-400">{w.event_id}</p>
                </div>
                <span className="font-semibold text-emerald-700">{w.processing_status}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <h3 className="text-sm font-bold text-slate-900 mb-3">
            Security &amp; Configuration Audit Logs ({auditLogs.length})
          </h3>
          <div className="space-y-2 max-h-64 overflow-y-auto text-xs">
            {auditLogs.map((a) => (
              <div key={a.id} className="p-2.5 bg-slate-50 rounded border border-slate-200">
                <div className="flex justify-between font-semibold">
                  <span>{a.action}</span>
                  <span className="text-slate-500">{a.actor_email}</span>
                </div>
                <p className="text-[11px] font-mono text-slate-500 mt-0.5">
                  Entity: {a.entity_type} • {String(a.created_at || '').slice(0, 19)}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
