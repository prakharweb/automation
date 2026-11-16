import React, { useEffect, useState } from 'react';
import { apiClient } from '../services/api';

export default function FollowupManagementPage({ onSelectLead }) {
  const [jobs, setJobs] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [msg, setMsg] = useState('');
  const [loading, setLoading] = useState(true);

  const loadJobs = async () => {
    setLoading(true);
    try {
      const res = await apiClient.getFollowups(statusFilter);
      setJobs(res.data || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
  }, [statusFilter]);

  const handleRunDue = async () => {
    setMsg('');
    try {
      const res = await apiClient.processDueFollowups();
      setMsg(
        `Worker executed: ${res.data.processed} due job(s) checked, ${res.data.sent} sent, ${res.data.cancelled} cancelled.`
      );
      await loadJobs();
    } catch (err) {
      setMsg(`Error: ${err.message}`);
    }
  };

  const handleCancelJob = async (jobId) => {
    try {
      await apiClient.updateFollowup(jobId, {
        status: 'CANCELLED_PAUSED',
        cancellation_reason: 'Manually cancelled by administrator',
      });
      setMsg('Follow-up job cancelled.');
      await loadJobs();
    } catch (err) {
      setMsg(`Error: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Persistent Follow-Up Scheduler &amp; Compliance Engine
            </h2>
            <p className="text-xs text-slate-500">
              24h &amp; 72h follow-ups stored in PostgreSQL (`followup_jobs`) • Automatically stops when customer replies, converts, or opts out
            </p>
          </div>
          <div className="flex gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs"
            >
              <option value="">All Job Statuses</option>
              <option value="SCHEDULED">SCHEDULED</option>
              <option value="COMPLETED">COMPLETED</option>
              <option value="CANCELLED_REPLIED">CANCELLED_REPLIED</option>
              <option value="CANCELLED_CONVERTED">CANCELLED_CONVERTED</option>
              <option value="CANCELLED_OPT_OUT">CANCELLED_OPT_OUT</option>
            </select>
            <button
              onClick={handleRunDue}
              className="px-4 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold"
            >
              ▶ Run Due Follow-Ups Now
            </button>
          </div>
        </div>

        {msg && (
          <div className="p-3 rounded-lg bg-sky-50 border border-sky-200 text-sky-900 text-xs font-medium">
            {msg}
          </div>
        )}
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3">Step</th>
                <th className="px-4 py-3">Lead Name</th>
                <th className="px-4 py-3">Phone</th>
                <th className="px-4 py-3">Campaign</th>
                <th className="px-4 py-3">Approved Template</th>
                <th className="px-4 py-3">Scheduled At</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Notes / Cancellation Reason</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {jobs.map((job) => (
                <tr key={job.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-bold">Step #{job.step_number}</td>
                  <td
                    onClick={() => onSelectLead(job.lead_id)}
                    className="px-4 py-3 font-semibold text-sky-700 hover:underline cursor-pointer"
                  >
                    {job.lead_name}
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-600">{job.lead_phone}</td>
                  <td className="px-4 py-3 text-slate-700 max-w-xs truncate">{job.campaign_name}</td>
                  <td className="px-4 py-3 font-mono text-teal-700">{job.template_name}</td>
                  <td className="px-4 py-3 font-mono text-slate-600">
                    {String(job.scheduled_at || '').slice(0, 19)}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 rounded font-semibold ${
                        job.status === 'SCHEDULED'
                          ? 'bg-amber-100 text-amber-800'
                          : job.status === 'COMPLETED'
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {job.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-500">{job.cancellation_reason || '—'}</td>
                  <td className="px-4 py-3 text-right">
                    {job.status === 'SCHEDULED' && (
                      <button
                        onClick={() => handleCancelJob(job.id)}
                        className="px-2.5 py-1 rounded border border-rose-200 text-rose-600 hover:bg-rose-50 font-medium"
                      >
                        Cancel
                      </button>
                    )}
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
