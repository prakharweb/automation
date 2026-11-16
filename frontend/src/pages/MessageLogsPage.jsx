import React, { useEffect, useState } from 'react';
import { apiClient } from '../services/api';

export default function MessageLogsPage({ onSelectLead }) {
  const [outbound, setOutbound] = useState([]);
  const [inbound, setInbound] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);

  const loadMessages = async () => {
    setLoading(true);
    try {
      const res = await apiClient.getMessages({ status: statusFilter });
      setOutbound(res.data || []);
      setInbound(res.incoming_messages || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMessages();
  }, [statusFilter]);

  return (
    <div className="space-y-6">
      {/* Outbound Message Logs */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Outbound DoubleTick Message Logs ({outbound.length})
            </h2>
            <p className="text-xs text-slate-500">
              Tracks SENT, DELIVERED, READ, and FAILED status updates reconciled via POST /webhooks/doubletick
            </p>
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs"
          >
            <option value="">All Delivery Statuses</option>
            <option value="SENT">SENT</option>
            <option value="DELIVERED">DELIVERED</option>
            <option value="READ">READ</option>
            <option value="FAILED">FAILED</option>
          </select>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3">DoubleTick Message ID</th>
                <th className="px-4 py-3">Lead</th>
                <th className="px-4 py-3">Recipient Phone</th>
                <th className="px-4 py-3">Type / Template</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Content Preview</th>
                <th className="px-4 py-3">Sent At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {outbound.map((m) => (
                <tr
                  key={m.id}
                  onClick={() => m.lead_id && onSelectLead(m.lead_id)}
                  className="hover:bg-slate-50 cursor-pointer"
                >
                  <td className="px-4 py-3 font-mono text-slate-600">{m.doubletick_message_id}</td>
                  <td className="px-4 py-3 font-semibold text-slate-900">{m.lead_name}</td>
                  <td className="px-4 py-3 font-mono text-slate-700">{m.recipient_phone}</td>
                  <td className="px-4 py-3 font-mono text-teal-700">
                    {m.template_name || m.message_type}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 rounded font-semibold ${
                        m.status === 'READ'
                          ? 'bg-emerald-100 text-emerald-800'
                          : m.status === 'DELIVERED'
                          ? 'bg-teal-100 text-teal-800'
                          : m.status === 'FAILED'
                          ? 'bg-rose-100 text-rose-800'
                          : 'bg-sky-100 text-sky-800'
                      }`}
                    >
                      {m.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-600 max-w-xs truncate">{m.content_preview}</td>
                  <td className="px-4 py-3 font-mono text-slate-500">
                    {String(m.sent_at || m.created_at || '').slice(0, 19)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Incoming Customer Replies */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200">
          <h3 className="text-sm font-bold text-slate-900">
            Incoming WhatsApp Customer Replies &amp; Opt-Out Feed ({inbound.length})
          </h3>
          <p className="text-xs text-slate-500">
            Captured via DoubleTick MESSAGE_RECEIVED webhook • Automatically cancels pending follow-ups and opens 24h service window
          </p>
        </div>
        <div className="divide-y divide-slate-200 text-xs">
          {inbound.map((inc) => (
            <div key={inc.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-900">{inc.sender_name || inc.sender_phone}</span>
                  <span className="font-mono text-slate-500">{inc.sender_phone}</span>
                  {inc.is_opt_out_command && (
                    <span className="px-2 py-0.5 rounded bg-rose-100 text-rose-800 font-bold">
                      STOP / OPT-OUT
                    </span>
                  )}
                </div>
                <p className="text-slate-700 mt-1">{inc.message_text}</p>
                {inc.ai_reply_text && (
                  <p className="text-emerald-700 mt-1 bg-emerald-50 p-2 rounded border border-emerald-200">
                    <strong>AI Reply:</strong> {inc.ai_reply_text}
                  </p>
                )}
              </div>
              <span className="font-mono text-slate-400">
                {String(inc.received_at || '').slice(0, 19)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
