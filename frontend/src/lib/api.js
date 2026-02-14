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
  register: (data) => api.post('/auth/register', data),
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

// Whitelist
export const whitelistAPI = {
  list: (projectId) => api.get(`/projects/${projectId}/whitelist`),
  add: (projectId, data) => api.post(`/projects/${projectId}/whitelist`, data),
  update: (projectId, id, data) => api.patch(`/projects/${projectId}/whitelist/${id}`, data),
  delete: (projectId, id) => api.delete(`/projects/${projectId}/whitelist/${id}`),
};

// Scripts
export const scriptAPI = {
  list: (projectId) => api.get(`/projects/${projectId}/scripts`),
  get: (projectId, id) => api.get(`/projects/${projectId}/scripts/${id}`),
  create: (projectId, data) => api.post(`/projects/${projectId}/scripts`, data),
  update: (projectId, id, data) => api.patch(`/projects/${projectId}/scripts/${id}`, data),
  delete: (projectId, id) => api.delete(`/projects/${projectId}/scripts/${id}`),
};

// Dashboard
export const dashboardAPI = {
  stats: () => api.get('/dashboard/stats'),
};

// Access Logs
export const logsAPI = {
  list: (projectId, limit = 50) => api.get(`/projects/${projectId}/logs?limit=${limit}`),
};

// Analytics
export const analyticsAPI = {
  get: (projectId) => api.get(`/projects/${projectId}/analytics`),
};

// Domain Tester
export const domainTestAPI = {
  test: (projectId, domain) => api.post(`/projects/${projectId}/test-domain`, { domain }),
};

export default api;
