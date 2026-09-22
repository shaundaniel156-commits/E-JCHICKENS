/** Typed-ish wrappers around the REST API, grouped by module. */
import { api } from './client'

export const authApi = {
  login: (payload) => api.post('/auth/login', payload),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
  forgotPassword: (email) => api.post('/auth/forgot-password', { email }),
  resetPassword: (payload) => api.post('/auth/reset-password', payload),
  changePassword: (payload) => api.post('/auth/change-password', payload),
}

export const dashboardApi = {
  summary: () => api.get('/dashboard/summary'),
}

export const birdsApi = {
  list: (params) => api.get('/birds', params),
  options: (params) => api.get('/birds/options', params),
  get: (id) => api.get(`/birds/${id}`),
  create: (payload) => api.post('/birds', payload),
  update: (id, payload) => api.put(`/birds/${id}`, payload),
  adjust: (id, payload) => api.post(`/birds/${id}/adjust`, payload),
  remove: (id) => api.del(`/birds/${id}`),
}

export const mortalityApi = {
  list: (params) => api.get('/mortality', params),
  series: (params) => api.get('/mortality/series', params),
  create: (payload) => api.post('/mortality', payload),
  update: (id, payload) => api.put(`/mortality/${id}`, payload),
  remove: (id) => api.del(`/mortality/${id}`),
}

export const healthApi = {
  list: (params) => api.get('/health-records', params),
  summary: () => api.get('/health-records/summary'),
  create: (payload) => api.post('/health-records', payload),
  update: (id, payload) => api.put(`/health-records/${id}`, payload),
  remove: (id) => api.del(`/health-records/${id}`),
}

export const feedApi = {
  stock: () => api.get('/feed/stock'),
  types: () => api.get('/feed/types'),
  createType: (payload) => api.post('/feed/types', payload),
  updateType: (id, payload) => api.put(`/feed/types/${id}`, payload),
  removeType: (id) => api.del(`/feed/types/${id}`),
  purchases: (params) => api.get('/feed/purchases', params),
  createPurchase: (payload) => api.post('/feed/purchases', payload),
  updatePurchase: (id, payload) => api.put(`/feed/purchases/${id}`, payload),
  removePurchase: (id) => api.del(`/feed/purchases/${id}`),
  consumption: (params) => api.get('/feed/consumption', params),
  createConsumption: (payload) => api.post('/feed/consumption', payload),
  updateConsumption: (id, payload) => api.put(`/feed/consumption/${id}`, payload),
  removeConsumption: (id) => api.del(`/feed/consumption/${id}`),
}

export const expensesApi = {
  list: (params) => api.get('/expenses', params),
  categories: () => api.get('/expenses/categories'),
  createCategory: (payload) => api.post('/expenses/categories', payload),
  removeCategory: (id) => api.del(`/expenses/categories/${id}`),
  breakdown: (params) => api.get('/expenses/breakdown', params),
  create: (payload) => api.post('/expenses', payload),
  update: (id, payload) => api.put(`/expenses/${id}`, payload),
  remove: (id) => api.del(`/expenses/${id}`),
}

export const salesApi = {
  list: (params) => api.get('/sales', params),
  get: (id) => api.get(`/sales/${id}`),
  create: (payload) => api.post('/sales', payload),
  update: (id, payload) => api.put(`/sales/${id}`, payload),
  remove: (id) => api.del(`/sales/${id}`),
  customers: (params) => api.get('/customers', params),
  createCustomer: (payload) => api.post('/customers', payload),
  updateCustomer: (id, payload) => api.put(`/customers/${id}`, payload),
  removeCustomer: (id) => api.del(`/customers/${id}`),
}

export const financeApi = {
  summary: (params) => api.get('/finance/summary', params),
  budgets: () => api.get('/budgets'),
  activeBudget: () => api.get('/budgets/active'),
  createBudget: (payload) => api.post('/budgets', payload),
  updateBudget: (id, payload) => api.put(`/budgets/${id}`, payload),
  removeBudget: (id) => api.del(`/budgets/${id}`),
}

export const reportsApi = {
  birds: (params) => api.get('/reports/birds', params),
  feed: (params) => api.get('/reports/feed', params),
  expenses: (params) => api.get('/reports/expenses', params),
  sales: (params) => api.get('/reports/sales', params),
  profitLoss: (params) => api.get('/reports/profit-loss', params),
  performance: (params) => api.get('/reports/performance', params),
  download: (report, params) =>
    api.download(`/reports/${report}/export`, params, `ej-chickens-${report}-report`),
}

export const notificationsApi = {
  list: (params) => api.get('/notifications', params),
  count: () => api.get('/notifications/count'),
  markRead: (id) => api.post(`/notifications/${id}/read`),
  markAllRead: () => api.post('/notifications/read-all'),
  remove: (id) => api.del(`/notifications/${id}`),
}

export const activityApi = {
  list: (params) => api.get('/activity', params),
}

export const usersApi = {
  list: (params) => api.get('/users', params),
  get: (id) => api.get(`/users/${id}`),
  create: (payload) => api.post('/users', payload),
  update: (id, payload) => api.put(`/users/${id}`, payload),
  deactivate: (id) => api.del(`/users/${id}`),
  activate: (id) => api.post(`/users/${id}/activate`),
  resetPassword: (id) => api.post(`/users/${id}/reset-password`),
  profile: () => api.get('/users/me'),
  updateProfile: (payload) => api.put('/users/me', payload),
}

export const settingsApi = {
  get: () => api.get('/settings'),
  update: (payload) => api.put('/settings', payload),
}
