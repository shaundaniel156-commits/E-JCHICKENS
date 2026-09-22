/** Formatting helpers. Money arrives from the API as an exact decimal string. */

const DEFAULT_CURRENCY = 'UGX'

export function toNumber(value) {
  if (value === null || value === undefined || value === '') return 0
  const parsed = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

/**
 * UGX has no practical sub-unit, so amounts are shown whole:
 *   "UGX 800,000"  —  never "UGX 800,000.00"
 */
export function formatMoney(value, currency = DEFAULT_CURRENCY, { sign = false } = {}) {
  const amount = toNumber(value)
  const rounded = Math.round(Math.abs(amount))
  const prefix = amount < 0 ? '−' : sign && amount > 0 ? '+' : ''
  return `${prefix}${currency} ${rounded.toLocaleString('en-US')}`
}

/** Compact form for labels: UGX 1.2M, UGX 850K. */
export function formatMoneyCompact(value, currency = DEFAULT_CURRENCY) {
  return `${currency} ${compactAmount(value)}`
}

/**
 * Compact amount with no currency, for axis ticks. The chart title carries the
 * unit, so repeating it on every tick only makes the label wrap onto two lines.
 */
export function compactAmount(value) {
  const amount = toNumber(value)
  const abs = Math.abs(amount)
  const sign = amount < 0 ? '−' : ''
  if (abs >= 1_000_000_000) return `${sign}${(abs / 1_000_000_000).toFixed(1)}B`
  if (abs >= 1_000_000) return `${sign}${(abs / 1_000_000).toFixed(abs >= 10_000_000 ? 0 : 1)}M`
  if (abs >= 1_000) return `${sign}${Math.round(abs / 1_000)}K`
  return `${sign}${Math.round(abs)}`
}

export function formatNumber(value, maximumFractionDigits = 0) {
  return toNumber(value).toLocaleString('en-US', { maximumFractionDigits })
}

/** Quantities keep up to 2 decimals but drop trailing zeros: 8, 8.5, 8.25. */
export function formatQuantity(value, unit = '') {
  const amount = toNumber(value)
  const text = amount.toLocaleString('en-US', { maximumFractionDigits: 2 })
  return unit ? `${text} ${unit}` : text
}

export function formatPercent(value, digits = 1) {
  return `${toNumber(value).toFixed(digits)}%`
}

export function formatDate(value, style = 'medium') {
  if (!value) return '—'
  const date = typeof value === 'string' ? new Date(`${value.slice(0, 10)}T00:00:00`) : value
  if (Number.isNaN(date.getTime())) return '—'
  if (style === 'short') {
    return date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
  }
  if (style === 'numeric') {
    return date.toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' })
  }
  return date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

export function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value.endsWith('Z') || value.includes('+') ? value : `${value}Z`)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatRelative(value) {
  if (!value) return '—'
  const date = new Date(value.endsWith('Z') || value.includes('+') ? value : `${value}Z`)
  if (Number.isNaN(date.getTime())) return '—'
  const seconds = Math.round((Date.now() - date.getTime()) / 1000)
  if (seconds < 60) return 'just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`
  if (seconds < 86_400) return `${Math.floor(seconds / 3600)} h ago`
  if (seconds < 604_800) return `${Math.floor(seconds / 86_400)} d ago`
  return formatDate(date)
}

export function todayISO() {
  const now = new Date()
  const offset = now.getTimezoneOffset() * 60_000
  return new Date(now.getTime() - offset).toISOString().slice(0, 10)
}

export function greeting(name = '') {
  const hour = new Date().getHours()
  const part = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
  // The full name is used rather than the first word: many accounts are named
  // after a role ("Farm Administrator"), where a first-word greeting reads oddly.
  const trimmed = name.trim()
  return trimmed ? `${part}, ${trimmed}` : part
}

export function initials(name = '') {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('')
}

export function titleCase(value = '') {
  return value
    .toString()
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (character) => character.toUpperCase())
}
