import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API_BASE = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('jshost_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 responses
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('jshost_token');
      localStorage.removeItem('jshost_user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth
export const authAPI = {
  login: (data) => api.post('/auth/login', data),
  me: () => api.get('/auth/me'),
};

// Categories
export const categoryAPI = {
  list: () => api.get('/categories'),
  listAll: () => api.get('/categories/all'),
  create: (data) => api.post('/categories', data),
  update: (id, data) => api.patch(`/categories/${id}`, data),
  delete: (id) => api.delete(`/categories/${id}`),
};

// Projects
export const projectAPI = {
  list: () => api.get('/projects'),
  get: (id) => api.get(`/projects/${id}`),
  create: (data) => api.post('/projects', data),
  update: (id, data) => api.patch(`/projects/${id}`, data),
  delete: (id) => api.delete(`/projects/${id}`),
};

// Whitelist (per Script)
export const whitelistAPI = {
  list: (projectId, scriptId) => api.get(`/projects/${projectId}/scripts/${scriptId}/whitelist`),
  add: (projectId, scriptId, data) => api.post(`/projects/${projectId}/scripts/${scriptId}/whitelist`, data),
  update: (projectId, scriptId, id, data) => api.patch(`/projects/${projectId}/scripts/${scriptId}/whitelist/${id}`, data),
  delete: (projectId, scriptId, id) => api.delete(`/projects/${projectId}/scripts/${scriptId}/whitelist/${id}`),
};

// Scripts
export const scriptAPI = {
  list: (projectId) => api.get(`/projects/${projectId}/scripts`),
  get: (projectId, id) => api.get(`/projects/${projectId}/scripts/${id}`),
  create: (projectId, data) => api.post(`/projects/${projectId}/scripts`, data),
  update: (projectId, id, data) => api.patch(`/projects/${projectId}/scripts/${id}`, data),
  delete: (projectId, id) => api.delete(`/projects/${projectId}/scripts/${id}`),
  analytics: (projectId, scriptId) => api.get(`/projects/${projectId}/scripts/${scriptId}/analytics`),
  logs: (projectId, scriptId, page = 1, perPage = 20) => api.get(`/projects/${projectId}/scripts/${scriptId}/logs?page=${page}&per_page=${perPage}`),
  clearLogs: (projectId, scriptId) => api.delete(`/projects/${projectId}/scripts/${scriptId}/logs`),
};

// Dashboard
export const dashboardAPI = {
  stats: () => api.get('/dashboard/stats'),
};

// Access Logs
export const logsAPI = {
  list: (projectId, limit = 50) => api.get(`/projects/${projectId}/logs?limit=${limit}`),
  clear: (projectId) => api.delete(`/projects/${projectId}/logs`),
  delete: (projectId, logId) => api.delete(`/projects/${projectId}/logs/${logId}`),
};

// Analytics
export const analyticsAPI = {
  get: (projectId) => api.get(`/projects/${projectId}/analytics`),
  getLogs: (projectId, page = 1, perPage = 20) => api.get(`/projects/${projectId}/analytics/logs?page=${page}&per_page=${perPage}`),
  getBlacklistedDomains: (projectId) => api.get(`/projects/${projectId}/blacklisted-domains`),
};

// Domain Tester (per Script)
export const domainTestAPI = {
  test: (projectId, scriptId, domain) => api.post(`/projects/${projectId}/scripts/${scriptId}/test-domain`, { domain }),
};

// Custom Domains
export const customDomainAPI = {
  list: () => api.get('/custom-domains'),
  listActive: () => api.get('/custom-domains/active'),
  add: (domain) => api.post('/custom-domains', { domain }),
  verify: (id) => api.post(`/custom-domains/${id}/verify`),
  update: (id, data) => api.patch(`/custom-domains/${id}`, data),
  delete: (id) => api.delete(`/custom-domains/${id}`),
};

// Popunder Campaigns (standalone)
export const popunderAPI = {
  list: () => api.get('/popunders'),
  get: (id) => api.get(`/popunders/${id}`),
  create: (data) => api.post('/popunders', data),
  update: (id, data) => api.patch(`/popunders/${id}`, data),
  delete: (id) => api.delete(`/popunders/${id}`),
  // Analytics
  getAnalytics: (id) => api.get(`/popunders/${id}/analytics`),
  getAnalyticsLogs: (id, page = 1, perPage = 20) => api.get(`/popunders/${id}/analytics/logs?page=${page}&per_page=${perPage}`),
  clearAnalytics: (id) => api.delete(`/popunders/${id}/analytics`),
  deleteAnalyticsLog: (id, logId) => api.delete(`/popunders/${id}/analytics/${logId}`),
};

// Auth - remove register
export const authAPI = {
  login: (data) => api.post('/auth/login', data),
  me: () => api.get('/auth/me'),
};

export default api;
