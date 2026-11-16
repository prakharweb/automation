import React, { useEffect, useState } from 'react';
import { apiClient } from '../services/api';

export default function WhatsAppTemplatesPage() {
  const [templates, setTemplates] = useState([]);
  const [dtStatus, setDtStatus] = useState(null);
  const [msg, setMsg] = useState('');
  const [showNewModal, setShowNewModal] = useState(false);

  const [newTpl, setNewTpl] = useState({
    template_name: '',
    language: 'en',
    category: 'UTILITY',
    purpose: 'hospital_for_sale',
    header_type: 'DOCUMENT',
    body_text: 'Hello {{1}}, thank you for contacting Space Consultant regarding {{2}}. Highlights: {{3}}.',
    variables_schema: ['full_name', 'campaign_name', 'summary'],
  });

  const [testPayload, setTestPayload] = useState({
    recipient_phone: '+919811122233',
    message_type: 'TEMPLATE',
    template_name: 'hospital_enquiry',
    language: 'en',
    placeholders: ['Dr. Rajesh Sharma', 'Campaign A - 100 Bed Hospital', 'NABH Accredited 100 Bed Hospital'],
  });

  const loadData = async () => {
    try {
      const [tRes, dRes] = await Promise.all([
        apiClient.getTemplates(),
        apiClient.getDoubleTickStatus(),
      ]);
      setTemplates(tRes.data || []);
      setDtStatus(dRes.data);
    } catch (err) {
      setMsg(`Error: ${err.message}`);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateTemplate = async (e) => {
    e.preventDefault();
    setMsg('');
    try {
      await apiClient.createTemplate(newTpl);
      setShowNewModal(false);
      setMsg(`Template '${newTpl.template_name}' registered.`);
      await loadData();
    } catch (err) {
      setMsg(`Error: ${err.message}`);
    }
  };

  const handleSendTest = async (e) => {
    e.preventDefault();
    setMsg('');
    try {
      const res = await apiClient.sendDoubleTickTestMessage(testPayload);
      setMsg(
        `DoubleTick test message dispatched (Status: ${res.data.status}, Message ID: ${res.data.doubletick_message_id})`
      );
    } catch (err) {
      setMsg(`Test message response: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* DoubleTick Status & Test Console */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-bold text-slate-900">
              DoubleTick WhatsApp Templates &amp; Test Console
            </h2>
            <p className="text-xs text-slate-500">
              Endpoint: <code>{dtStatus?.endpoints?.template || 'https://public.doubletick.io/whatsapp/message/template'}</code>
            </p>
          </div>
          <button
            onClick={() => setShowNewModal(true)}
            className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold"
          >
            + Register Approved Template
          </button>
        </div>

        {msg && (
          <div className="p-3 rounded-lg bg-sky-50 border border-sky-200 text-sky-900 text-xs font-medium">
            {msg}
          </div>
        )}

        <form onSubmit={handleSendTest} className="p-4 bg-slate-50 rounded-xl border border-slate-200 grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">Recipient WhatsApp Phone</label>
            <input
              type="text"
              value={testPayload.recipient_phone}
              onChange={(e) => setTestPayload({ ...testPayload, recipient_phone: e.target.value })}
              className="w-full px-3 py-1.5 border border-slate-300 rounded-lg font-mono"
            />
          </div>
          <div>
            <label className="block font-semibold text-slate-700 mb-1">Template Name</label>
            <select
              value={testPayload.template_name}
              onChange={(e) => setTestPayload({ ...testPayload, template_name: e.target.value })}
              className="w-full px-3 py-1.5 border border-slate-300 rounded-lg font-mono"
            >
              {templates.map((t) => (
                <option key={t.id} value={t.template_name}>
                  {t.template_name}
                </option>
              ))}
            </select>
          </div>
          <div className="sm:col-span-2 flex items-end">
            <button
              type="submit"
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-semibold"
            >
              ▶ Send DoubleTick Test Template Message
            </button>
          </div>
        </form>
      </div>

      {/* Templates Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {templates.map((tpl) => (
          <div key={tpl.id} className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="font-mono font-bold text-sm text-sky-700">{tpl.template_name}</span>
              <div className="flex items-center gap-1.5">
                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700">
                  Header: {tpl.header_type}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                  {tpl.approval_status}
                </span>
              </div>
            </div>
            <p className="text-xs text-slate-500">
              Purpose: <span className="font-mono text-slate-700">{tpl.purpose}</span> • Language: <code>{tpl.language}</code>
            </p>
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-800 leading-relaxed">
              {tpl.body_text}
            </div>
            <div className="text-[11px] text-slate-500">
              Variables: <code>{(tpl.variables_schema || []).join(', ')}</code>
            </div>
          </div>
        ))}
      </div>

      {showNewModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-lg w-full p-6 space-y-4 text-xs">
            <h3 className="text-sm font-bold text-slate-900">Register DoubleTick Approved Template</h3>
            <form onSubmit={handleCreateTemplate} className="space-y-3">
              <div>
                <label className="block font-semibold mb-1">Template Name (Exact DoubleTick Name)</label>
                <input
                  type="text"
                  value={newTpl.template_name}
                  onChange={(e) => setNewTpl({ ...newTpl, template_name: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold mb-1">Purpose</label>
                  <input
                    type="text"
                    value={newTpl.purpose}
                    onChange={(e) => setNewTpl({ ...newTpl, purpose: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Header Type</label>
                  <select
                    value={newTpl.header_type}
                    onChange={(e) => setNewTpl({ ...newTpl, header_type: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                  >
                    <option value="NONE">NONE</option>
                    <option value="DOCUMENT">DOCUMENT (PDF)</option>
                    <option value="IMAGE">IMAGE</option>
                    <option value="TEXT">TEXT</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block font-semibold mb-1">Template Body Text</label>
                <textarea
                  rows={3}
                  value={newTpl.body_text}
                  onChange={(e) => setNewTpl({ ...newTpl, body_text: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                  required
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewModal(false)}
                  className="px-3 py-1.5 rounded-lg border border-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg bg-sky-600 text-white font-semibold"
                >
                  Save Template
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
