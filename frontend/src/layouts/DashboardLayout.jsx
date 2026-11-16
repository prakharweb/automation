import React, { useState } from 'react';

const NAV_ITEMS = [
  { id: 'dashboard', label: '1. Dashboard', badge: 'Live' },
  { id: 'meta', label: '2. Meta Integration', badge: 'Graph API' },
  { id: 'campaigns', label: '3. Campaign Management', badge: 'Core' },
  { id: 'leads', label: '4. Lead Management', badge: null },
  { id: 'templates', label: '5. WhatsApp Templates', badge: 'DoubleTick' },
  { id: 'messages', label: '6. Message Logs', badge: null },
  { id: 'followups', label: '7. Follow-up Management', badge: '24h/72h' },
  { id: 'settings', label: '8. Settings', badge: null },
  { id: 'users', label: '9. Admin Users', badge: 'RBAC' },
];

export default function DashboardLayout({
  activeTab,
  setActiveTab,
  onOpenWizard,
  user,
  onLogout,
  integrationStatus,
  children,
}) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const metaConnected = integrationStatus?.meta?.connected;
  const dtConfigured = integrationStatus?.doubletick?.configured;

  return (
    <div className="min-h-screen flex bg-slate-50 text-slate-900">
      {/* Sidebar (Desktop & Mobile Drawer) */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-72 bg-slate-900 text-slate-100 flex flex-col transition-transform duration-200 lg:static lg:translate-x-0 ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-sky-500 text-white font-bold text-sm">
                SC
              </span>
              <span className="font-bold text-lg tracking-tight text-white">
                Space Consultant
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Meta Ads + DoubleTick Automation
            </p>
          </div>
          <button
            onClick={() => setMobileMenuOpen(false)}
            className="lg:hidden text-slate-400 hover:text-white text-sm"
          >
            ✕
          </button>
        </div>

        {/* 7-Step Setup Wizard CTA */}
        <div className="px-4 pt-4">
          <button
            onClick={onOpenWizard}
            className="w-full py-2.5 px-3 rounded-lg bg-gradient-to-r from-sky-600 to-teal-600 hover:from-sky-500 hover:to-teal-500 text-white font-medium text-xs shadow flex items-center justify-between transition"
          >
            <span>⚡ 7-Step Setup Wizard</span>
            <span className="bg-white/20 px-1.5 py-0.5 rounded text-[10px]">Launch</span>
          </button>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const active = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  setActiveTab(item.id);
                  setMobileMenuOpen(false);
                }}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition ${
                  active
                    ? 'bg-sky-600 text-white shadow-sm'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
              >
                <span>{item.label}</span>
                {item.badge && (
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full ${
                      active
                        ? 'bg-white/20 text-white'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Integration Status & User Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/60 space-y-3">
          <div className="space-y-1.5 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Meta Webhooks</span>
              <span
                className={`inline-flex items-center gap-1 font-medium ${
                  metaConnected ? 'text-emerald-400' : 'text-amber-400'
                }`}
              >
                <span className="w-2 h-2 rounded-full bg-current" />
                {metaConnected ? 'Connected' : 'Setup Needed'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">DoubleTick API</span>
              <span
                className={`inline-flex items-center gap-1 font-medium ${
                  dtConfigured ? 'text-emerald-400' : 'text-amber-400'
                }`}
              >
                <span className="w-2 h-2 rounded-full bg-current" />
                {dtConfigured ? 'Active' : 'Env Key Needed'}
              </span>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
            <div className="truncate pr-2">
              <p className="text-xs font-semibold text-white truncate">
                {user?.full_name || 'Admin'}
              </p>
              <p className="text-[11px] text-slate-400 uppercase tracking-wider">
                {user?.role || 'admin'}
              </p>
            </div>
            <button
              onClick={onLogout}
              className="text-xs px-2.5 py-1.5 rounded bg-slate-800 hover:bg-red-600/80 text-slate-300 hover:text-white transition"
            >
              Sign Out
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header */}
        <header className="bg-white border-b border-slate-200 px-4 lg:px-8 py-3.5 flex items-center justify-between sticky top-0 z-20">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="lg:hidden px-2.5 py-1.5 border border-slate-300 rounded-md text-slate-700 text-sm"
            >
              ☰ Menu
            </button>
            <div>
              <h1 className="text-base lg:text-lg font-bold text-slate-900">
                Space Consultant Lead Automation Hub
              </h1>
              <p className="text-xs text-slate-500 hidden sm:block">
                Hospital M&A • Doctor & Healthcare Recruitment • Institutional & Commercial Real Estate
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={() => setActiveTab('campaigns')}
              className="hidden sm:inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
            >
              🎯 Campaign Rules
            </button>
            <button
              onClick={onOpenWizard}
              className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-semibold bg-sky-600 hover:bg-sky-700 text-white transition"
            >
              ⚡ Setup Wizard
            </button>
          </div>
        </header>

        {/* Page Body */}
        <main className="flex-1 p-4 lg:p-8 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
