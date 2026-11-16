import React, { useEffect, useState } from 'react';
import { apiClient } from '../services/api';

const PURPOSE_OPTIONS = [
  { value: 'hospital_for_sale', label: 'Hospital for Sale Advertisement' },
  { value: 'doctor_recruitment', label: 'Doctor Recruitment Advertisement' },
  { value: 'healthcare_recruitment', label: 'Healthcare Recruitment Advertisement' },
  { value: 'hospital_property', label: 'Hospital Property Advertisement' },
  { value: 'real_estate', label: 'Real Estate Advertisement' },
];

export default function CampaignManagementPage() {
  const [campaigns, setCampaigns] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const [statusMsg, setStatusMsg] = useState('');

  const [formData, setFormData] = useState({
    name: '',
    meta_campaign_id: '',
    facebook_page_id: '104928374650192',
    lead_form_id: '',
    purpose: 'hospital_for_sale',
    whatsapp_template_name: 'hospital_enquiry',
    template_language: 'en',
    auto_reply_enabled: true,
    pdf_brochure_url: '',
    pdf_filename: '',
    website_url: 'https://spaceconsultant.in',
    summary: '',
    executive_name: 'Rohit Verma (Hospital M&A Advisor)',
    step_2_delay_hours: 24,
    step_3_delay_hours: 72,
  });

  const loadData = async () => {
    setLoading(true);
    try {
      const [cRes, tRes] = await Promise.all([
        apiClient.getCampaigns(),
        apiClient.getTemplates(),
      ]);
      setCampaigns(cRes.data || []);
      setTemplates(tRes.data || []);
    } catch (err) {
      setStatusMsg(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const openCreateModal = () => {
    setEditingItem(null);
    setFormData({
      name: '',
      meta_campaign_id: '',
      facebook_page_id: '104928374650192',
      lead_form_id: '',
      purpose: 'hospital_for_sale',
      whatsapp_template_name: 'hospital_enquiry',
      template_language: 'en',
      auto_reply_enabled: true,
      pdf_brochure_url: 'https://spaceconsultant.in/assets/brochures/100_bed_hospital_delhi_ncr.pdf',
      pdf_filename: 'Space_Consultant_Brochure.pdf',
      website_url: 'https://spaceconsultant.in',
      summary: '100-Bed Multispeciality Hospital in Delhi NCR',
      executive_name: 'Rohit Verma (Hospital M&A Advisor)',
      step_2_delay_hours: 24,
      step_3_delay_hours: 72,
    });
    setShowModal(true);
  };

  const openEditModal = (item) => {
    setEditingItem(item);
    const details = item.template_variables?.details || {};
    setFormData({
      name: item.campaign_name,
      meta_campaign_id: item.meta_campaign_id,
      facebook_page_id: item.facebook_page_id,
      lead_form_id: item.lead_form_id || '',
      purpose: item.campaign_purpose,
      whatsapp_template_name: item.whatsapp_template_name,
      template_language: item.template_language || 'en',
      auto_reply_enabled: item.auto_reply_enabled,
      pdf_brochure_url: item.pdf_brochure_url || '',
      pdf_filename: item.pdf_filename || '',
      website_url: item.website_url || '',
      summary: details.summary || item.description || '',
      executive_name: item.assignment_config?.default_executive_name || '',
      step_2_delay_hours: item.followup_config?.step_2_delay_hours ?? 24,
      step_3_delay_hours: item.followup_config?.step_3_delay_hours ?? 72,
    });
    setShowModal(true);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setStatusMsg('');
    const payload = {
      name: formData.name,
      meta_campaign_id: formData.meta_campaign_id,
      facebook_page_id: formData.facebook_page_id,
      lead_form_id: formData.lead_form_id || null,
      purpose: formData.purpose,
      whatsapp_template_name: formData.whatsapp_template_name,
      template_language: formData.template_language,
      auto_reply_enabled: formData.auto_reply_enabled,
      pdf_brochure_url: formData.pdf_brochure_url || null,
      pdf_filename: formData.pdf_filename || null,
      website_url: formData.website_url || null,
      description: formData.summary,
      template_variables: {
        placeholders: ['{full_name}', formData.name, formData.summary],
        details: { summary: formData.summary },
      },
      followup_config: {
        enabled: true,
        step_2_delay_hours: Number(formData.step_2_delay_hours),
        step_2_template: 'hospital_enquiry_followup_24h',
        step_3_delay_hours: Number(formData.step_3_delay_hours),
        step_3_template: 'hospital_enquiry_followup_24h',
      },
      assignment_config: {
        default_executive_name: formData.executive_name,
      },
      campaign_knowledge: {
        summary: formData.summary,
      },
    };

    try {
      if (editingItem) {
        await apiClient.updateCampaign(editingItem.id, payload);
        setStatusMsg(`Updated campaign automation '${formData.name}'.`);
      } else {
        await apiClient.createCampaign(payload);
        setStatusMsg(`Created campaign automation '${formData.name}'.`);
      }
      setShowModal(false);
      await loadData();
    } catch (err) {
      setStatusMsg(`Error: ${err.message}`);
    }
  };

  const handleDelete = async (id) => {
    try {
      await apiClient.deleteCampaign(id);
      setConfirmDeleteId(null);
      setStatusMsg('Campaign automation deleted.');
      await loadData();
    } catch (err) {
      setStatusMsg(`Error: ${err.message}`);
    }
  };

  const handleToggleAutoReply = async (item) => {
    try {
      await apiClient.updateCampaign(item.id, {
        auto_reply_enabled: !item.auto_reply_enabled,
      });
      await loadData();
    } catch (err) {
      setStatusMsg(`Error: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
        <div>
          <h2 className="text-base font-bold text-slate-900">
            Campaign-Wise Automation Configuration Engine
          </h2>
          <p className="text-xs text-slate-500">
            Map each Meta Campaign ID &amp; Lead Form ID to its dedicated WhatsApp Template, Brochure PDF, and Follow-up Schedule
          </p>
        </div>
        <button
          onClick={openCreateModal}
          className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold"
        >
          + Add Campaign Automation
        </button>
      </div>

      {statusMsg && (
        <div className="p-3 rounded-lg bg-sky-50 border border-sky-200 text-sky-900 text-xs font-medium">
          {statusMsg}
        </div>
      )}

      {/* Campaign Cards / Table */}
      <div className="grid grid-cols-1 gap-4">
        {campaigns.map((c) => {
          const summary = c.template_variables?.details?.summary || c.description || '';
          return (
            <div
              key={c.id}
              className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4"
            >
              <div className="space-y-1.5 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-sky-100 text-sky-800">
                    {c.campaign_purpose}
                  </span>
                  <h3 className="text-sm font-bold text-slate-900">{c.campaign_name}</h3>
                </div>
                <p className="text-xs text-slate-600">{summary}</p>
                <div className="flex flex-wrap gap-4 pt-1 text-xs text-slate-500 font-mono">
                  <span>Meta Campaign ID: <strong className="text-slate-800">{c.meta_campaign_id}</strong></span>
                  <span>Form ID: <strong className="text-slate-800">{c.lead_form_id || 'Any'}</strong></span>
                  <span>Template: <strong className="text-teal-700">{c.whatsapp_template_name} ({c.template_language})</strong></span>
                  <span>Leads Captured: <strong className="text-slate-900">{c.leads_count ?? 0}</strong></span>
                </div>
                <div className="flex flex-wrap gap-4 text-[11px] text-slate-500">
                  <span>Assigned Executive: <strong>{c.assignment_config?.default_executive_name || 'Unassigned'}</strong></span>
                  {c.pdf_brochure_url && (
                    <span>PDF Brochure: <strong className="text-sky-700">{c.pdf_filename || 'Attached'}</strong></span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 self-end lg:self-center">
                <button
                  onClick={() => handleToggleAutoReply(c)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                    c.auto_reply_enabled
                      ? 'bg-emerald-100 text-emerald-800 hover:bg-emerald-200'
                      : 'bg-amber-100 text-amber-800 hover:bg-amber-200'
                  }`}
                >
                  {c.auto_reply_enabled ? '● Auto-Reply ON' : '○ Auto-Reply Paused'}
                </button>
                <button
                  onClick={() => openEditModal(c)}
                  className="px-3 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-100 text-xs font-medium text-slate-700"
                >
                  Edit
                </button>
                <button
                  onClick={() => setConfirmDeleteId(c.id)}
                  className="px-3 py-1.5 rounded-lg border border-rose-200 hover:bg-rose-50 text-xs font-medium text-rose-600"
                >
                  Delete
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Create / Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-2xl w-full overflow-hidden">
            <div className="px-6 py-4 bg-slate-900 text-white flex justify-between items-center">
              <h3 className="text-sm font-bold">
                {editingItem ? 'Edit Campaign Automation' : 'New Campaign Automation'}
              </h3>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-white text-sm">
                ✕
              </button>
            </div>
            <form onSubmit={handleSave} className="p-6 space-y-4 max-h-[80vh] overflow-y-auto text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="sm:col-span-2">
                  <label className="block font-semibold text-slate-700 mb-1">Campaign Name</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                    required
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Meta Campaign ID</label>
                  <input
                    type="text"
                    value={formData.meta_campaign_id}
                    onChange={(e) => setFormData({ ...formData, meta_campaign_id: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono"
                    required
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Meta Lead Form ID</label>
                  <input
                    type="text"
                    value={formData.lead_form_id}
                    onChange={(e) => setFormData({ ...formData, lead_form_id: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Campaign Purpose</label>
                  <select
                    value={formData.purpose}
                    onChange={(e) => setFormData({ ...formData, purpose: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                  >
                    {PURPOSE_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Approved WhatsApp Template</label>
                  <select
                    value={formData.whatsapp_template_name}
                    onChange={(e) => setFormData({ ...formData, whatsapp_template_name: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono"
                  >
                    {templates.map((t) => (
                      <option key={t.id} value={t.template_name}>
                        {t.template_name} ({t.purpose})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="sm:col-span-2">
                  <label className="block font-semibold text-slate-700 mb-1">
                    Campaign Highlights / Template Variable {{3}} Summary
                  </label>
                  <textarea
                    rows={2}
                    value={formData.summary}
                    onChange={(e) => setFormData({ ...formData, summary: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                    required
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">PDF Brochure URL</label>
                  <input
                    type="text"
                    value={formData.pdf_brochure_url}
                    onChange={(e) => setFormData({ ...formData, pdf_brochure_url: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Assigned Executive</label>
                  <input
                    type="text"
                    value={formData.executive_name}
                    onChange={(e) => setFormData({ ...formData, executive_name: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 rounded-lg border border-slate-300 text-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-lg bg-sky-600 hover:bg-sky-700 text-white font-semibold"
                >
                  Save Campaign Automation
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirmation Dialog for Delete */}
      {confirmDeleteId && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl p-6 max-w-md w-full space-y-4 shadow-xl">
            <h4 className="text-sm font-bold text-slate-900">Confirm Campaign Deletion</h4>
            <p className="text-xs text-slate-600">
              Are you sure you want to delete this campaign automation configuration? Existing captured leads will remain preserved in PostgreSQL.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setConfirmDeleteId(null)}
                className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(confirmDeleteId)}
                className="px-4 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold"
              >
                Delete Automation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
