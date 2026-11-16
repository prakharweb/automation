import React, { useEffect, useState } from 'react';
import LeadDetailModal from './components/LeadDetailModal';
import SetupWizardModal from './components/SetupWizardModal';
import { AuthProvider, useAuth } from './context/AuthContext';
import DashboardLayout from './layouts/DashboardLayout';
import AdminUsersPage from './pages/AdminUsersPage';
import CampaignManagementPage from './pages/CampaignManagementPage';
import DashboardPage from './pages/DashboardPage';
import FollowupManagementPage from './pages/FollowupManagementPage';
import LeadManagementPage from './pages/LeadManagementPage';
import LoginPage from './pages/LoginPage';
import MessageLogsPage from './pages/MessageLogsPage';
import MetaIntegrationPage from './pages/MetaIntegrationPage';
import SettingsPage from './pages/SettingsPage';
import WhatsAppTemplatesPage from './pages/WhatsAppTemplatesPage';
import { apiClient } from './services/api';

function MainPortal() {
  const { user, loading, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [stats, setStats] = useState(null);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [selectedLeadId, setSelectedLeadId] = useState(null);

  const loadDashboardStats = async () => {
    if (!user) return;
    try {
      const res = await apiClient.getDashboardStats();
      setStats(res.data);
    } catch {
      // ignore initial error
    }
  };

  useEffect(() => {
    if (user) {
      loadDashboardStats();
    }
  }, [user]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 text-white text-sm">
        Loading Space Consultant Automation Platform...
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  return (
    <DashboardLayout
      activeTab={activeTab}
      setActiveTab={setActiveTab}
      onOpenWizard={() => setWizardOpen(true)}
      user={user}
      onLogout={logout}
      integrationStatus={stats?.integrations}
    >
      {activeTab === 'dashboard' && (
        <DashboardPage
          stats={stats}
          onOpenWizard={() => setWizardOpen(true)}
          onSelectLead={(id) => setSelectedLeadId(id)}
          onNavigate={(tab) => setActiveTab(tab)}
        />
      )}
      {activeTab === 'meta' && <MetaIntegrationPage />}
      {activeTab === 'campaigns' && <CampaignManagementPage />}
      {activeTab === 'leads' && (
        <LeadManagementPage onSelectLead={(id) => setSelectedLeadId(id)} />
      )}
      {activeTab === 'templates' && <WhatsAppTemplatesPage />}
      {activeTab === 'messages' && (
        <MessageLogsPage onSelectLead={(id) => setSelectedLeadId(id)} />
      )}
      {activeTab === 'followups' && (
        <FollowupManagementPage onSelectLead={(id) => setSelectedLeadId(id)} />
      )}
      {activeTab === 'settings' && <SettingsPage />}
      {activeTab === 'users' && <AdminUsersPage />}

      <SetupWizardModal
        isOpen={wizardOpen}
        onClose={() => setWizardOpen(false)}
        onCompleted={loadDashboardStats}
      />

      <LeadDetailModal
        leadId={selectedLeadId}
        onClose={() => setSelectedLeadId(null)}
        onUpdated={loadDashboardStats}
      />
    </DashboardLayout>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainPortal />
    </AuthProvider>
  );
}
