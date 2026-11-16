import React from 'react';

export default function DashboardPage({ stats, onOpenWizard, onSelectLead, onNavigate }) {
  const ov = stats?.overview || {};
  const breakdown = stats?.campaign_breakdown || [];
  const recentLeads = stats?.recent_leads || [];

  const kpiCards = [
    { label: 'Total Leads', value: ov.total_leads ?? 0, tone: 'bg-sky-50 text-sky-900 border-sky-200' },
    { label: "Today's Leads", value: ov.todays_leads ?? 0, tone: 'bg-indigo-50 text-indigo-900 border-indigo-200' },
    { label: 'Messages Sent', value: ov.messages_sent ?? 0, tone: 'bg-slate-50 text-slate-900 border-slate-200' },
    { label: 'Messages Delivered', value: ov.messages_delivered ?? 0, tone: 'bg-teal-50 text-teal-900 border-teal-200' },
    { label: 'Messages Read', value: ov.messages_read ?? 0, tone: 'bg-emerald-50 text-emerald-900 border-emerald-200' },
    { label: 'Failed Messages', value: ov.failed_messages ?? 0, tone: 'bg-rose-50 text-rose-900 border-rose-200' },
    { label: 'Interested Leads', value: ov.interested_leads ?? 0, tone: 'bg-amber-50 text-amber-900 border-amber-200' },
    { label: 'Converted Leads', value: ov.converted_leads ?? 0, tone: 'bg-purple-50 text-purple-900 border-purple-200' },
  ];

  return (
    <div className="space-y-6">
      {/* KPI Overview Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {kpiCards.map((card) => (
          <div
            key={card.label}
            className={`p-4 rounded-xl border shadow-sm ${card.tone}`}
          >
            <p className="text-xs font-medium opacity-80">{card.label}</p>
            <p className="text-2xl font-extrabold mt-1">{card.value}</p>
          </div>
        ))}
      </div>

      {/* Campaign-Wise Automation Performance Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900">
              Campaign-Wise WhatsApp Routing Matrix
            </h2>
            <p className="text-xs text-slate-500">
              Automatic campaign identification &amp; DoubleTick template selection per Meta Instant Form
            </p>
          </div>
          <button
            onClick={() => onNavigate('campaigns')}
            className="text-xs font-semibold text-sky-600 hover:text-sky-800"
          >
            Manage Campaigns →
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3">Campaign Name</th>
                <th className="px-4 py-3">Purpose</th>
                <th className="px-4 py-3">Meta Campaign ID</th>
                <th className="px-4 py-3">WhatsApp Template</th>
                <th className="px-4 py-3">Auto Reply</th>
                <th className="px-4 py-3 text-right">Leads</th>
                <th className="px-4 py-3 text-right">Interested</th>
                <th className="px-4 py-3 text-right">Converted</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {breakdown.map((row) => (
                <tr key={row.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-semibold text-slate-900">{row.campaign_name}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded-full bg-sky-100 text-sky-800 font-mono text-[11px]">
                      {row.purpose}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-600">{row.meta_campaign_id}</td>
                  <td className="px-4 py-3 font-mono font-semibold text-teal-700">{row.template_name}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                        row.auto_reply_enabled
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-slate-200 text-slate-600'
                      }`}
                    >
                      {row.auto_reply_enabled ? 'Enabled' : 'Paused'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right font-bold">{row.total_leads}</td>
                  <td className="px-4 py-3 text-right text-amber-700 font-semibold">{row.interested_leads}</td>
                  <td className="px-4 py-3 text-right text-emerald-700 font-semibold">{row.converted_leads}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent Captured Leads */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900">Recent Meta Instant Form Leads</h2>
            <p className="text-xs text-slate-500">
              Click any lead to inspect full form answers, WhatsApp consent, and DoubleTick delivery status
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={onOpenWizard}
              className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold"
            >
              + Simulate Test Lead
            </button>
            <button
              onClick={() => onNavigate('leads')}
              className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-semibold text-slate-700"
            >
              View All Leads
            </button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Phone</th>
                <th className="px-4 py-3">Campaign</th>
                <th className="px-4 py-3">Platform</th>
                <th className="px-4 py-3">Message Status</th>
                <th className="px-4 py-3">Lead Status</th>
                <th className="px-4 py-3">Assigned Executive</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {recentLeads.map((lead) => (
                <tr
                  key={lead.id}
                  onClick={() => onSelectLead(lead.id)}
                  className="hover:bg-sky-50/60 cursor-pointer"
                >
                  <td className="px-4 py-3 font-semibold text-slate-900">{lead.full_name}</td>
                  <td className="px-4 py-3 font-mono text-slate-700">{lead.phone || 'Missing'}</td>
                  <td className="px-4 py-3 text-slate-700">{lead.campaign_name}</td>
                  <td className="px-4 py-3 uppercase text-[11px] font-medium text-slate-500">
                    {lead.platform}
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded bg-slate-100 font-semibold text-slate-800">
                      {lead.message_status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded bg-sky-100 font-semibold text-sky-900">
                      {lead.lead_status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {lead.assigned_executive_name || 'Unassigned'}
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
