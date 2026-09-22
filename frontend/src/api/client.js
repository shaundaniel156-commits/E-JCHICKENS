/**
 * Single HTTP client for the whole app.
 *
 * Responsibilities: attach the access token, refresh it once when it expires,
 * and turn every backend error shape into one predictable ApiError.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const ACCESS_KEY = 'ejc.access_token'
const REFRESH_KEY = 'ejc.refresh_token'
const USER_KEY = 'ejc.user'

export class ApiError extends Error {
  constructor(message, { status = 0, code = 'error', details = null } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }

  /** Field-level messages, keyed by field name, for inline form errors. */
  get fieldErrors() {
    return this.details && typeof this.details === 'object' ? this.details : {}
  }
}

export const tokenStore = {
  get access() {
    return localStorage.getItem(ACCESS_KEY)
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY)
  },
  get user() {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY) || 'null')
    } catch {
      return null
    }
  },
  save({ access_token, refresh_token }, user) {
    if (access_token) localStorage.setItem(ACCESS_KEY, access_token)
    if (refresh_token) localStorage.setItem(REFRESH_KEY, refresh_token)
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
  },
  saveUser(user) {
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
    localStorage.removeItem(USER_KEY)
  },
}

let refreshInFlight = null

async function refreshAccessToken() {
  const refresh_token = tokenStore.refresh
  if (!refresh_token) return null

  // Collapse concurrent 401s into a single refresh call.
  if (!refreshInFlight) {
    refreshInFlight = fetch(`${BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token }),
    })
      .then(async (response) => {
        if (!response.ok) return null
        const tokens = await response.json()
        tokenStore.save(tokens)
        return tokens.access_token
      })
      .catch(() => null)
      .finally(() => {
        refreshInFlight = null
      })
  }
  return refreshInFlight
}

function buildQuery(params) {
  if (!params) return ''
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    search.append(key, value)
  })
  const query = search.toString()
  return query ? `?${query}` : ''
}

async function parseError(response) {
  let body = null
  try {
    body = await response.json()
  } catch {
    /* non-JSON body (e.g. a proxy error page) */
  }

  if (body?.error) {
    return new ApiError(body.error.message, {
      status: response.status,
      code: body.error.code,
      details: body.error.details ?? null,
    })
  }
  if (typeof body?.detail === 'string') {
    return new ApiError(body.detail, { status: response.status })
  }

  const fallbacks = {
    401: 'Your session has expired. Please sign in again.',
    403: 'You do not have permission to do that.',
    404: 'We could not find what you were looking for.',
    500: 'Something went wrong on the server. Please try again.',
    503: 'The service is temporarily unavailable. Please try again shortly.',
  }
  return new ApiError(fallbacks[response.status] || 'The request could not be completed.', {
    status: response.status,
  })
}

async function request(method, path, { body, params, retry = true, raw = false } = {}) {
  const url = `${BASE_URL}${path}${buildQuery(params)}`
  const headers = {}
  const token = tokenStore.access
  if (token) headers.Authorization = `Bearer ${token}`
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  let response
  try {
    response = await fetch(url, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(
      'Cannot reach the server. Check your connection and that the API is running.',
      { status: 0, code: 'network_error' },
    )
  }

  if (response.status === 401 && retry && tokenStore.refresh) {
    const refreshed = await refreshAccessToken()
    if (refreshed) return request(method, path, { body, params, retry: false, raw })
    tokenStore.clear()
    window.dispatchEvent(new CustomEvent('ejc:session-expired'))
  }

  if (!response.ok) throw await parseError(response)
  if (raw) return response
  if (response.status === 204) return null
  const text = await response.text()
  return text ? JSON.parse(text) : null
}

export const api = {
  get: (path, params) => request('GET', path, { params }),
  post: (path, body, params) => request('POST', path, { body, params }),
  put: (path, body) => request('PUT', path, { body }),
  del: (path) => request('DELETE', path),
  /** Streams a file download (reports export) straight to the browser. */
  async download(path, params, fallbackName = 'download') {
    const response = await request('GET', path, { params, raw: true })
    const blob = await response.blob()
    const disposition = response.headers.get('Content-Disposition') || ''
    const match = disposition.match(/filename="?([^";]+)"?/)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = match ? match[1] : fallbackName
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  },
}
