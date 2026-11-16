import React, { useEffect, useState } from 'react';
import { apiClient } from '../services/api';

export default function LeadDetailModal({ leadId, onClose, onUpdated }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [execName, setExecName] = useState('');
  const [statusVal, setStatusVal] = useState('');
  const [notesVal, setNotesVal] = useState('');
  const [actionMsg, setActionMsg] = useState('');

  const loadDetail = async () => {
    if (!leadId) return;
    setLoading(true);
    setError('');
    try {
      const res = await apiClient.getLeadDetail(leadId);
      setDetail(res.data);
      setExecName(res.data.assigned_executive_name || '');
      setStatusVal(res.data.lead_status || 'NEW');
      setNotesVal(res.data.notes || '');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDetail();
  }, [leadId]);

  if (!leadId) return null;

  const handleSaveLead = async () => {
    setActionMsg('');
    try {
      await apiClient.updateLead(leadId, {
        lead_status: statusVal,
        notes: notesVal,
      });
      setActionMsg('Lead status & notes updated.');
      await loadDetail();
      if (onUpdated) onUpdated();
    } catch (err) {
      setActionMsg(`Error: ${err.message}`);
    }
  };

  const handleAssign = async () => {
    if (!execName.trim()) return;
    setActionMsg('');
    try {
      await apiClient.assignLead(leadId, { executive_name: execName.trim() });
      setActionMsg(`Assigned to ${execName}.`);
      await loadDetail();
      if (onUpdated) onUpdated();
    } catch (err) {
      setActionMsg(`Error: ${err.message}`);
    }
  };

  const handleResend = async () => {
    setActionMsg('');
    try {
      await apiClient.resendLeadMessage(leadId);
      setActionMsg('Approved WhatsApp template resent via DoubleTick.');
      await loadDetail();
      if (onUpdated) onUpdated();
    } catch (err) {
      setActionMsg(`Error: ${err.message}`);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold">
              Lead Profile &amp; WhatsApp Automation Audit
            </h3>
            <p className="text-xs text-slate-400 font-mono">
              Meta Lead ID: {detail?.meta_lead_id || leadId}
            </p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-sm">
            ✕ Close
          </button>
        </div>

        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {loading && <p className="text-sm text-slate-500">Loading complete lead details...</p>}
          {error && <p className="text-sm text-red-600">{error}</p>}
          {actionMsg && (
            <div className="p-3 rounded-lg bg-sky-50 border border-sky-200 text-sky-900 text-xs font-medium">
              {actionMsg}
            </div>
          )}

          {detail && (
            <>
              {/* Top Summary Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs">
                <div>
                  <p className="text-slate-500">Full Name &amp; Contact</p>
                  <p className="font-bold text-sm text-slate-900 mt-0.5">{detail.full_name}</p>
                  <p className="font-mono text-slate-700">{detail.phone || 'Missing Phone'}</p>
                  <p className="text-slate-600">{detail.email || 'No Email'}</p>
                </div>
                <div>
                  <p className="text-slate-500">Campaign &amp; Source</p>
                  <p className="font-semibold text-slate-900 mt-0.5">{detail.campaign_name}</p>
                  <p className="text-slate-600">
                    Purpose: <span className="font-mono">{detail.campaign_purpose}</span>
                  </p>
                  <p className="text-slate-600">
                    Platform: <span className="uppercase">{detail.platform}</span> ({detail.lead_source})
                  </p>
                </div>
                <div>
                  <p className="text-slate-500">WhatsApp Compliance State</p>
                  <p className="mt-0.5">
                    Opt-In:{' '}
                    <span className={detail.whatsapp_opt_in ? 'text-emerald-700 font-bold' : 'text-red-600 font-bold'}>
                      {detail.whatsapp_opt_in ? 'OPTED IN' : 'NO CONSENT'}
                    </span>
                  </p>
                  <p>
                    Opted Out (STOP):{' '}
                    <span className="font-semibold">{detail.opted_out ? 'YES (Blocked)' : 'No'}</span>
                  </p>
                  <p>
                    24h Service Window:{' '}
                    <span className={detail.within_24h_service_window ? 'text-emerald-700 font-semibold' : 'text-slate-600'}>
                      {detail.within_24h_service_window ? 'OPEN (Free-form permitted)' : 'Closed (Template only)'}
                    </span>
                  </p>
                </div>
              </div>

              {/* Status, Executive Assignment & Manual Resend */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 border border-slate-200 rounded-xl space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Update Lead Status &amp; Notes
                  </h4>
                  <div className="flex gap-2">
                    <select
                      value={statusVal}
                      onChange={(e) => setStatusVal(e.target.value)}
                      className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs flex-1"
                    >
                      <option value="NEW">NEW</option>
                      <option value="CONTACTED">CONTACTED</option>
                      <option value="INTERESTED">INTERESTED</option>
                      <option value="QUALIFIED">QUALIFIED</option>
                      <option value="MANUAL_REVIEW">MANUAL_REVIEW</option>
                      <option value="CONVERTED">CONVERTED</option>
                      <option value="OPTED_OUT">OPTED_OUT</option>
                    </select>
                    <button
                      onClick={handleSaveLead}
                      className="px-3 py-1.5 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold"
                    >
                      Save Status
                    </button>
                  </div>
                  <textarea
                    rows={2}
                    value={notesVal}
                    onChange={(e) => setNotesVal(e.target.value)}
                    placeholder="Advisor notes..."
                    className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-xs"
                  />
                </div>

                <div className="p-4 border border-slate-200 rounded-xl space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Assign Executive &amp; Template Actions
                  </h4>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={execName}
                      onChange={(e) => setExecName(e.target.value)}
                      placeholder="Executive Name"
                      className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs flex-1"
                    />
                    <button
                      onClick={handleAssign}
                      className="px-3 py-1.5 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-semibold"
                    >
                      Assign
                    </button>
                  </div>
                  <div className="pt-1 flex items-center gap-2">
                    <button
                      onClick={handleResend}
                      disabled={detail.opted_out || !detail.whatsapp_opt_in}
                      className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 text-white rounded-lg text-xs font-semibold"
                    >
                      ↻ Manually Resend Campaign WhatsApp Template
                    </button>
                  </div>
                </div>
              </div>

              {/* Outbound & Inbound Message History */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="border border-slate-200 rounded-xl p-4">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                    Outbound WhatsApp Messages ({detail.outbound_messages?.length || 0})
                  </h4>
                  <div className="space-y-2 max-h-48 overflow-y-auto text-xs">
                    {(detail.outbound_messages || []).map((m) => (
                      <div key={m.id} className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                        <div className="flex justify-between font-semibold">
                          <span>{m.template_name || m.message_type}</span>
                          <span className="text-sky-700">{m.status}</span>
                        </div>
                        <p className="text-slate-600 mt-1">{m.content_preview}</p>
                        <p className="text-[10px] text-slate-400 font-mono mt-1">
                          ID: {m.doubletick_message_id}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="border border-slate-200 rounded-xl p-4">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                    Customer Replies ({detail.inbound_messages?.length || 0}) &amp; Follow-ups ({detail.followup_jobs?.length || 0})
                  </h4>
                  <div className="space-y-2 max-h-48 overflow-y-auto text-xs">
                    {(detail.inbound_messages || []).map((inc) => (
                      <div key={inc.id} className="p-2.5 bg-emerald-50 rounded-lg border border-emerald-200">
                        <p className="font-semibold text-emerald-900">{inc.message_text}</p>
                        <p className="text-[10px] text-emerald-700 mt-0.5">
                          Received: {String(inc.received_at).slice(0, 19)}
                        </p>
                      </div>
                    ))}
                    {(detail.followup_jobs || []).map((job) => (
                      <div key={job.id} className="p-2.5 bg-amber-50/70 rounded-lg border border-amber-200">
                        <div className="flex justify-between font-semibold">
                          <span>Follow-up Step #{job.step_number}</span>
                          <span>{job.status}</span>
                        </div>
                        <p className="text-[11px] text-slate-600">
                          Scheduled: {String(job.scheduled_at).slice(0, 19)}
                        </p>
                        {job.cancellation_reason && (
                          <p className="text-[11px] text-amber-800">{job.cancellation_reason}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
