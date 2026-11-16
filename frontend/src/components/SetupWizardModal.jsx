import React, { useState } from 'react';
import { apiClient } from '../services/api';

const WIZARD_STEPS = [
  { step: 1, title: 'Connect Meta App', desc: 'Configure Meta App ID & Graph API permissions' },
  { step: 2, title: 'Configure Facebook Page', desc: 'Link Space Consultant Facebook Page & Ad Account' },
  { step: 3, title: 'Connect DoubleTick', desc: 'Verify DoubleTick API & Webhook endpoints' },
  { step: 4, title: 'Configure WhatsApp Templates', desc: 'Verify approved campaign WhatsApp templates' },
  { step: 5, title: 'Create Campaign Automation', desc: 'Map Meta Campaign ID & Form to WhatsApp Template' },
  { step: 6, title: 'Test Lead Processing', desc: 'Simulate a Meta Instant Form lead & verify routing' },
  { step: 7, title: 'Activate Automation', desc: 'Confirm webhook readiness & activate live routing' },
];

export default function SetupWizardModal({ isOpen, onClose, onCompleted }) {
  const [currentStep, setCurrentStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [testResult, setTestResult] = useState(null);

  const [metaForm, setMetaForm] = useState({
    app_id: '148920384756102',
    app_name: 'Space Consultant Meta Lead Automation App',
    business_id: '892019283746501',
    page_id: '104928374650192',
    page_name: 'Space Consultant - Hospital M&A & Healthcare Advisory',
    ad_account_id: 'act_1029384756',
  });

  const [testLeadForm, setTestLeadForm] = useState({
    meta_campaign_id: '2385910000101',
    meta_form_id: '900100200301',
    full_name: 'Dr. Siddharth Malhotra',
    phone: '+919811556677',
    email: 'dr.siddharth@medinvest.in',
    city: 'Delhi NCR',
  });

  if (!isOpen) return null;

  const handleSaveMetaStep = async () => {
    setBusy(true);
    setStatusMsg('');
    try {
      await apiClient.connectMeta(metaForm);
      setStatusMsg('Meta App & Page configuration saved.');
      setCurrentStep((s) => Math.min(7, s + 1));
    } catch (err) {
      setStatusMsg(`Error: ${err.message}`);
    } finally {
      setBusy(false);
    }
  };

  const handleRunTestLead = async () => {
    setBusy(true);
    setStatusMsg('');
    try {
      const res = await apiClient.simulateMetaLead(testLeadForm);
      setTestResult(res.data);
      setStatusMsg('Test lead captured, mapped to campaign, and processed!');
    } catch (err) {
      setStatusMsg(`Error: ${err.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-4xl w-full overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold">
              Space Consultant — 7-Step Lead Automation Setup Wizard
            </h2>
            <p className="text-xs text-slate-400">
              End-to-end onboarding for Meta Instant Forms → Campaign Engine → DoubleTick WhatsApp
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white text-sm px-2 py-1"
          >
            ✕ Close
          </button>
        </div>

        {/* Stepper Bar */}
        <div className="bg-slate-100 px-6 py-3 border-b border-slate-200 overflow-x-auto">
          <div className="flex items-center gap-2 min-w-max">
            {WIZARD_STEPS.map((item) => {
              const active = currentStep === item.step;
              const done = currentStep > item.step;
              return (
                <button
                  key={item.step}
                  onClick={() => setCurrentStep(item.step)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                    active
                      ? 'bg-sky-600 text-white shadow-sm'
                      : done
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-white text-slate-600 border border-slate-200'
                  }`}
                >
                  <span className="font-bold">{done ? '✓' : item.step}.</span>
                  <span>{item.title}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          {statusMsg && (
            <div className="p-3 rounded-lg bg-sky-50 border border-sky-200 text-sky-900 text-xs font-medium">
              {statusMsg}
            </div>
          )}

          {currentStep === 1 && (
            <div className="space-y-4">
              <h3 className="text-base font-bold text-slate-900">
                Step 1: Connect Meta Developer App
              </h3>
              <p className="text-xs text-slate-600">
                Configure your Meta Developer App ID and Business Manager ID. Set{' '}
                <code className="bg-slate-100 px-1.5 py-0.5 rounded">META_APP_SECRET</code>,{' '}
                <code className="bg-slate-100 px-1.5 py-0.5 rounded">META_VERIFY_TOKEN</code>, and{' '}
                <code className="bg-slate-100 px-1.5 py-0.5 rounded">META_ACCESS_TOKEN</code> in your Render environment variables.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Meta App ID
                  </label>
                  <input
                    type="text"
                    value={metaForm.app_id}
                    onChange={(e) => setMetaForm({ ...metaForm, app_id: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    App Display Name
                  </label>
                  <input
                    type="text"
                    value={metaForm.app_name}
                    onChange={(e) => setMetaForm({ ...metaForm, app_name: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
              </div>
              <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-1">
                <p className="font-semibold text-slate-800">Required Meta App Review Permissions:</p>
                <p className="text-slate-600">
                  <code>leads_retrieval</code>, <code>pages_manage_metadata</code>,{' '}
                  <code>pages_show_list</code>, <code>pages_read_engagement</code>,{' '}
                  <code>pages_manage_ads</code>, <code>ads_management</code>
                </p>
              </div>
            </div>
          )}

          {currentStep === 2 && (
            <div className="space-y-4">
              <h3 className="text-base font-bold text-slate-900">
                Step 2: Configure Facebook Page & Ad Account
              </h3>
              <p className="text-xs text-slate-600">
                Subscribe your Space Consultant Facebook Page to the <code>leadgen</code> webhook field.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Facebook Page ID
                  </label>
                  <input
                    type="text"
                    value={metaForm.page_id}
                    onChange={(e) => setMetaForm({ ...metaForm, page_id: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Facebook Page Name
                  </label>
                  <input
                    type="text"
                    value={metaForm.page_name}
                    onChange={(e) => setMetaForm({ ...metaForm, page_name: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Ad Account ID
                  </label>
                  <input
                    type="text"
                    value={metaForm.ad_account_id}
                    onChange={(e) => setMetaForm({ ...metaForm, ad_account_id: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
              </div>
              <button
                onClick={handleSaveMetaStep}
                disabled={busy}
                className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold"
              >
                {busy ? 'Saving...' : 'Save Meta App & Page Configuration'}
              </button>
            </div>
          )}

          {currentStep === 3 && (
            <div className="space-y-4">
              <h3 className="text-base font-bold text-slate-900">
                Step 3: Connect DoubleTick WhatsApp Business API
              </h3>
              <p className="text-xs text-slate-600">
                DoubleTick credentials are loaded securely from environment variables and never exposed in browser code.
              </p>
              <div className="p-4 rounded-xl bg-slate-900 text-slate-100 text-xs font-mono space-y-1.5">
                <div>DOUBLETICK_API_KEY=&lt;Your DoubleTick Public API Key&gt;</div>
                <div>DOUBLETICK_SENDER=+919810000000</div>
                <div>DOUBLETICK_WEBHOOK_SECRET=&lt;Your Webhook Bearer Secret&gt;</div>
                <div className="text-sky-400 pt-1">
                  Webhook Endpoint: POST /webhooks/doubletick (Events: MESSAGE_RECEIVED, MESSAGE_STATUS_UPDATE)
                </div>
              </div>
            </div>
          )}

          {currentStep === 4 && (
            <div className="space-y-4">
              <h3 className="text-base font-bold text-slate-900">
                Step 4: Approved WhatsApp Templates
              </h3>
              <p className="text-xs text-slate-600">
                The platform comes pre-configured with Space Consultant&apos;s 5 core campaign templates plus 24h follow-up templates:
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                {[
                  ['hospital_enquiry', 'Hospital for Sale (with PDF Brochure Header)'],
                  ['doctor_recruitment', 'Doctor Recruitment (Job Description & Eligibility)'],
                  ['healthcare_job_information', 'Healthcare Recruitment (Nursing & Ops Jobs)'],
                  ['hospital_property_info', 'Hospital Property (Plot & Building Dossier)'],
                  ['real_estate_brochure', 'Commercial Real Estate (Medical Suites Brochure)'],
                ].map(([tpl, desc]) => (
                  <div key={tpl} className="p-3 border border-slate-200 rounded-lg bg-slate-50">
                    <span className="font-mono font-bold text-sky-700">{tpl}</span>
                    <p className="text-slate-600 mt-0.5">{desc}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {currentStep === 5 && (
            <div className="space-y-4">
              <h3 className="text-base font-bold text-slate-900">
                Step 5: Campaign-Wise Automation Mapping
              </h3>
              <p className="text-xs text-slate-600">
                Every incoming Meta lead is matched deterministically by <code>meta_campaign_id</code> or{' '}
                <code>lead_form_id</code>. Unmapped leads are placed safely in the{' '}
                <span className="font-semibold text-amber-700">MANUAL_REVIEW</span> queue so an unrelated WhatsApp message is never sent.
              </p>
              <div className="overflow-x-auto border border-slate-200 rounded-lg">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-100 text-slate-700">
                    <tr>
                      <th className="p-2.5">Campaign Purpose</th>
                      <th className="p-2.5">Meta Campaign ID</th>
                      <th className="p-2.5">Lead Form ID</th>
                      <th className="p-2.5">WhatsApp Template</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    <tr>
                      <td className="p-2.5 font-medium">Hospital for Sale</td>
                      <td className="p-2.5 font-mono">2385910000101</td>
                      <td className="p-2.5 font-mono">900100200301</td>
                      <td className="p-2.5 font-mono text-sky-700">hospital_enquiry</td>
                    </tr>
                    <tr>
                      <td className="p-2.5 font-medium">Doctor Recruitment</td>
                      <td className="p-2.5 font-mono">2385910000102</td>
                      <td className="p-2.5 font-mono">900100200302</td>
                      <td className="p-2.5 font-mono text-sky-700">doctor_recruitment</td>
                    </tr>
                    <tr>
                      <td className="p-2.5 font-medium">Healthcare Recruitment</td>
                      <td className="p-2.5 font-mono">2385910000103</td>
                      <td className="p-2.5 font-mono">900100200303</td>
                      <td className="p-2.5 font-mono text-sky-700">healthcare_job_information</td>
                    </tr>
                    <tr>
                      <td className="p-2.5 font-medium">Hospital Property</td>
                      <td className="p-2.5 font-mono">2385910000104</td>
                      <td className="p-2.5 font-mono">900100200304</td>
                      <td className="p-2.5 font-mono text-sky-700">hospital_property_info</td>
                    </tr>
                    <tr>
                      <td className="p-2.5 font-medium">Real Estate</td>
                      <td className="p-2.5 font-mono">2385910000105</td>
                      <td className="p-2.5 font-mono">900100200305</td>
                      <td className="p-2.5 font-mono text-sky-700">real_estate_brochure</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {currentStep === 6 && (
            <div className="space-y-4">
              <h3 className="text-base font-bold text-slate-900">
                Step 6: Test Lead Processing End-to-End
              </h3>
              <p className="text-xs text-slate-600">
                Simulate a Meta Instant Form submission to verify campaign identification, PostgreSQL storage, and DoubleTick template routing:
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Select Campaign to Simulate
                  </label>
                  <select
                    value={testLeadForm.meta_campaign_id}
                    onChange={(e) => {
                      const map = {
                        '2385910000101': '900100200301',
                        '2385910000102': '900100200302',
                        '2385910000103': '900100200303',
                        '2385910000104': '900100200304',
                        '2385910000105': '900100200305',
                        '9999999999999': '888888888888',
                      };
                      setTestLeadForm({
                        ...testLeadForm,
                        meta_campaign_id: e.target.value,
                        meta_form_id: map[e.target.value] || '',
                      });
                    }}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                  >
                    <option value="2385910000101">Campaign A: Hospital for Sale</option>
                    <option value="2385910000102">Campaign B: Doctor Recruitment</option>
                    <option value="2385910000103">Campaign C: Healthcare Recruitment</option>
                    <option value="2385910000104">Campaign D: Hospital Property</option>
                    <option value="2385910000105">Campaign E: Commercial Real Estate</option>
                    <option value="9999999999999">Unmapped Campaign (Test Manual Review Queue)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Lead Full Name
                  </label>
                  <input
                    type="text"
                    value={testLeadForm.full_name}
                    onChange={(e) => setTestLeadForm({ ...testLeadForm, full_name: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    WhatsApp Phone Number
                  </label>
                  <input
                    type="text"
                    value={testLeadForm.phone}
                    onChange={(e) => setTestLeadForm({ ...testLeadForm, phone: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                  />
                </div>
              </div>
              <button
                onClick={handleRunTestLead}
                disabled={busy}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold"
              >
                {busy ? 'Processing Lead...' : '▶ Run End-to-End Lead Simulation'}
              </button>

              {testResult && (
                <div className="p-3.5 rounded-lg bg-slate-900 text-slate-100 text-xs font-mono overflow-x-auto">
                  <pre>{JSON.stringify(testResult, null, 2)}</pre>
                </div>
              )}
            </div>
          )}

          {currentStep === 7 && (
            <div className="space-y-4">
              <h3 className="text-base font-bold text-slate-900">
                Step 7: Activate Live Production Automation
              </h3>
              <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-950 text-xs space-y-2">
                <p className="font-bold text-sm">✅ Platform Ready for Production Operation</p>
                <ul className="list-disc pl-5 space-y-1">
                  <li>Meta Webhook Endpoint: <code>GET &amp; POST /webhooks/meta</code> (HMAC-SHA256 verified)</li>
                  <li>DoubleTick Webhook Endpoint: <code>POST /webhooks/doubletick</code> (Bearer/Secret verified)</li>
                  <li>Campaign-Wise Routing Engine active across all 5 healthcare &amp; real estate verticals</li>
                  <li>24-hour &amp; 72-hour Follow-up Worker active with automatic reply/opt-out cancellation</li>
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* Footer Controls */}
        <div className="px-6 py-3.5 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
          <button
            onClick={() => setCurrentStep((s) => Math.max(1, s - 1))}
            disabled={currentStep === 1}
            className="px-3.5 py-1.5 rounded-lg border border-slate-300 text-xs font-medium text-slate-700 disabled:opacity-40"
          >
            ← Previous Step
          </button>
          <div className="flex items-center gap-2">
            {currentStep < 7 ? (
              <button
                onClick={() => setCurrentStep((s) => Math.min(7, s + 1))}
                className="px-4 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold"
              >
                Next Step →
              </button>
            ) : (
              <button
                onClick={() => {
                  if (onCompleted) onCompleted();
                  onClose();
                }}
                className="px-5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold"
              >
                ✓ Finish &amp; Refresh Dashboard
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
