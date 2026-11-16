import React, { useEffect, useState } from 'react';
import { apiClient } from '../services/api';

export default function LeadManagementPage({ onSelectLead }) {
  const [leads, setLeads] = useState([]);
  const [total, setTotal] = useState(0);
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState('');

  const [filters, setFilters] = useState({
    search: '',
    campaign_id: '',
    lead_status: '',
    message_status: '',
    date_from: '',
    date_to: '',
  });

  const loadLeads = async () => {
    setLoading(true);
    try {
      const [lRes, cRes] = await Promise.all([
        apiClient.getLeads(filters),
        apiClient.getCampaigns(),
      ]);
      setLeads(lRes.data || []);
      setTotal(lRes.total || 0);
      setCampaigns(cRes.data || []);
    } catch (err) {
      setActionMsg(`Error loading leads: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLeads();
  }, [
    filters.campaign_id,
    filters.lead_status,
    filters.message_status,
    filters.date_from,
    filters.date_to,
  ]);

  const handleQuickResend = async (e, leadId) => {
    e.stopPropagation();
    setActionMsg('');
    try {
      await apiClient.resendLeadMessage(leadId);
      setActionMsg('WhatsApp template message resent.');
      await loadLeads();
    } catch (err) {
      setActionMsg(`Resend blocked: ${err.message}`);
    }
  };

  return (
    <div className="space-y-5">
      {/* Filter & Export Bar */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Captured Leads Directory ({total})
            </h2>
            <p className="text-xs text-slate-500">
              Search, filter by campaign/date/status, assign executives, resend WhatsApp templates, or export CSV
            </p>
          </div>
          <button
            onClick={() => apiClient.exportLeadsCsv(filters)}
            className="px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold"
          >
            ⬇ Export CSV
          </button>
        </div>

        {actionMsg && (
          <div className="p-3 rounded-lg bg-sky-50 border border-sky-200 text-sky-900 text-xs font-medium">
            {actionMsg}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3 text-xs">
          <div className="lg:col-span-2 flex gap-1.5">
            <input
              type="text"
              placeholder="Search name, phone, email..."
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg"
            />
            <button
              onClick={loadLeads}
              className="px-3 py-2 bg-sky-600 text-white rounded-lg font-semibold"
            >
              Search
            </button>
          </div>

          <select
            value={filters.campaign_id}
            onChange={(e) => setFilters({ ...filters, campaign_id: e.target.value })}
            className="px-3 py-2 border border-slate-300 rounded-lg"
          >
            <option value="">All Campaigns</option>
            {campaigns.map((c) => (
              <option key={c.id} value={c.meta_campaign_id}>
                {c.campaign_name}
              </option>
            ))}
          </select>

          <select
            value={filters.lead_status}
            onChange={(e) => setFilters({ ...filters, lead_status: e.target.value })}
            className="px-3 py-2 border border-slate-300 rounded-lg"
          >
            <option value="">All Lead Statuses</option>
            <option value="NEW">NEW</option>
            <option value="CONTACTED">CONTACTED</option>
            <option value="INTERESTED">INTERESTED</option>
            <option value="MANUAL_REVIEW">MANUAL_REVIEW</option>
            <option value="CONVERTED">CONVERTED</option>
            <option value="OPTED_OUT">OPTED_OUT</option>
          </select>

          <input
            type="date"
            value={filters.date_from}
            onChange={(e) => setFilters({ ...filters, date_from: e.target.value })}
            className="px-3 py-2 border border-slate-300 rounded-lg"
          />

          <input
            type="date"
            value={filters.date_to}
            onChange={(e) => setFilters({ ...filters, date_to: e.target.value })}
            className="px-3 py-2 border border-slate-300 rounded-lg"
          />
        </div>
      </div>

      {/* Leads Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Phone</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Campaign</th>
                <th className="px-4 py-3">Lead Source</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Message Status</th>
                <th className="px-4 py-3">Lead Status</th>
                <th className="px-4 py-3">Assigned Executive</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {leads.length === 0 && !loading && (
                <tr>
                  <td colSpan={10} className="p-8 text-center text-slate-500">
                    No leads match the current filters.
                  </td>
                </tr>
              )}
              {leads.map((lead) => (
                <tr
                  key={lead.id}
                  onClick={() => onSelectLead(lead.id)}
                  className="hover:bg-sky-50/50 cursor-pointer"
                >
                  <td className="px-4 py-3 font-semibold text-slate-900">{lead.full_name}</td>
                  <td className="px-4 py-3 font-mono text-slate-700">{lead.phone || 'Missing'}</td>
                  <td className="px-4 py-3 text-slate-600">{lead.email || '—'}</td>
                  <td className="px-4 py-3 text-slate-800 max-w-xs truncate">{lead.campaign_name}</td>
                  <td className="px-4 py-3">
                    <span className="uppercase text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-100">
                      {lead.platform}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-500 font-mono">
                    {String(lead.created_at || '').slice(0, 10)}
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded font-semibold bg-teal-50 text-teal-800">
                      {lead.message_status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 rounded font-semibold ${
                        lead.lead_status === 'CONVERTED'
                          ? 'bg-emerald-100 text-emerald-800'
                          : lead.lead_status === 'MANUAL_REVIEW'
                          ? 'bg-amber-100 text-amber-800'
                          : lead.lead_status === 'OPTED_OUT'
                          ? 'bg-rose-100 text-rose-800'
                          : 'bg-sky-100 text-sky-800'
                      }`}
                    >
                      {lead.lead_status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-700">
                    {lead.assigned_executive_name || 'Unassigned'}
                  </td>
                  <td className="px-4 py-3 text-right space-x-1.5">
                    <button
                      onClick={(e) => handleQuickResend(e, lead.id)}
                      disabled={lead.opted_out || !lead.whatsapp_opt_in}
                      className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 text-white font-medium"
                    >
                      Resend
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectLead(lead.id);
                      }}
                      className="px-2.5 py-1 rounded border border-slate-300 text-slate-700"
                    >
                      Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
