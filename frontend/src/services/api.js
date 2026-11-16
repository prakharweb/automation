/**
 * Space Consultant API Client Service (src/services/api.js)
 * Connects the React Frontend to the FastAPI Backend using VITE_API_URL.
 * Never embeds API keys in frontend source code.
 */
const RAW_BASE_URL = import.meta.env.VITE_API_URL || '';
export const API_BASE_URL = RAW_BASE_URL.replace(/\/$/, '');

const TOKEN_STORAGE_KEY = 'space_consultant_auth_token';

export function getStoredToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

async function request(path, options = {}) {
  const token = getStoredToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}`;
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || errorDetail;
    } catch {
      // Fallback to status text
    }
    const err = new Error(errorDetail);
    err.status = response.status;
    throw err;
  }

  return response.json();
}

export const apiClient = {
  // Health & Auth
  getHealth: () => request('/api/health'),
  login: (email, password) =>
    request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  getMe: () => request('/api/auth/me'),

  // Dashboard
  getDashboardStats: () => request('/api/dashboard/stats'),

  // Meta Lead Ads Integration
  getMetaStatus: () => request('/api/meta/status'),
  getMetaPages: () => request('/api/meta/pages'),
  getMetaCampaigns: () => request('/api/meta/campaigns'),
  getMetaForms: (pageId) =>
    request(`/api/meta/forms${pageId ? `?page_id=${encodeURIComponent(pageId)}` : ''}`),
  connectMeta: (payload) =>
    request('/api/meta/connect', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  simulateMetaLead: (payload) =>
    request('/api/meta/simulate-lead', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // DoubleTick WhatsApp Integration
  getDoubleTickStatus: () => request('/api/doubletick/status'),
  sendDoubleTickTestMessage: (payload) =>
    request('/api/doubletick/test-message', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Campaigns & Campaign-Wise Automation
  getCampaigns: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.purpose) qs.set('purpose', params.purpose);
    if (params.status_filter) qs.set('status_filter', params.status_filter);
    const query = qs.toString();
    return request(`/api/campaigns${query ? `?${query}` : ''}`);
  },
  createCampaign: (payload) =>
    request('/api/campaigns', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateCampaign: (id, payload) =>
    request(`/api/campaigns/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  deleteCampaign: (id) =>
    request(`/api/campaigns/${id}`, {
      method: 'DELETE',
    }),

  // Leads Management
  getLeads: (filters = {}) => {
    const qs = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        qs.set(k, v);
      }
    });
    const query = qs.toString();
    return request(`/api/leads${query ? `?${query}` : ''}`);
  },
  getLeadDetail: (id) => request(`/api/leads/${id}`),
  updateLead: (id, payload) =>
    request(`/api/leads/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  assignLead: (id, payload) =>
    request(`/api/leads/${id}/assign`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  resendLeadMessage: (id, payload = {}) =>
    request(`/api/leads/${id}/resend`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  exportLeadsCsv: async (filters = {}) => {
    const token = getStoredToken();
    const qs = new URLSearchParams({ ...filters, export: 'csv' });
    const res = await fetch(`${API_BASE_URL}/api/leads?${qs.toString()}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error('Failed to export leads CSV');
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `space_consultant_leads_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  },

  // WhatsApp Templates
  getTemplates: () => request('/api/templates'),
  createTemplate: (payload) =>
    request('/api/templates', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateTemplate: (id, payload) =>
    request(`/api/templates/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),

  // Message Logs
  getMessages: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.status) qs.set('status', params.status);
    if (params.message_type) qs.set('message_type', params.message_type);
    const query = qs.toString();
    return request(`/api/messages${query ? `?${query}` : ''}`);
  },
  getMessageDetail: (id) => request(`/api/messages/${id}`),

  // Follow-up Jobs
  getFollowups: (statusFilter = '') =>
    request(`/api/followups${statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : ''}`),
  createFollowup: (payload) =>
    request('/api/followups', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateFollowup: (id, payload) =>
    request(`/api/followups/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  processDueFollowups: () =>
    request('/api/followups/process-due', {
      method: 'POST',
    }),

  // Admin Users & System Settings
  getUsers: () => request('/api/users'),
  createUser: (payload) =>
    request('/api/users', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateUser: (id, payload) =>
    request(`/api/users/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  getSettings: () => request('/api/settings'),
  updateSettings: (settingsObj) =>
    request('/api/settings', {
      method: 'PUT',
      body: JSON.stringify({ settings: settingsObj }),
    }),
};
