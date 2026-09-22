import { Search } from 'lucide-react'

import { todayISO } from '../utils/format'

export const PERIOD_PRESETS = [
  { value: 'all_time', label: 'All time' },
  { value: 'today', label: 'Today' },
  { value: 'yesterday', label: 'Yesterday' },
  { value: 'this_week', label: 'This week' },
  { value: 'last_week', label: 'Last week' },
  { value: 'this_month', label: 'This month' },
  { value: 'last_month', label: 'Last month' },
  { value: 'this_year', label: 'This year' },
  { value: 'custom', label: 'Custom range…' },
]

export function SearchBox({ value, onChange, placeholder = 'Search…', label }) {
  return (
    <div className="search">
      <Search size={15} aria-hidden="true" />
      <input
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        aria-label={label || placeholder}
      />
    </div>
  )
}

export function FilterSelect({ label, value, onChange, options, placeholder = 'All' }) {
  return (
    <label className="field" style={{ minWidth: 150 }}>
      <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--ink-2)' }}>{label}</span>
      <select value={value ?? ''} onChange={(event) => onChange(event.target.value)}>
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}

/**
 * Period control: a preset list plus a custom range. The presets are resolved
 * server-side, so the client never has to compute "this month" itself.
 */
export function PeriodFilter({ value, onChange }) {
  const { preset = 'all_time', start_date = '', end_date = '' } = value || {}

  const update = (next) => onChange({ preset, start_date, end_date, ...next })

  return (
    <>
      <label className="field" style={{ minWidth: 150 }}>
        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--ink-2)' }}>Period</span>
        <select
          value={preset}
          onChange={(event) => {
            const nextPreset = event.target.value
            if (nextPreset === 'custom') {
              update({
                preset: 'custom',
                start_date: start_date || todayISO(),
                end_date: end_date || todayISO(),
              })
            } else {
              update({ preset: nextPreset, start_date: '', end_date: '' })
            }
          }}
        >
          {PERIOD_PRESETS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>

      {preset === 'custom' && (
        <>
          <label className="field" style={{ minWidth: 142 }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--ink-2)' }}>From</span>
            <input
              type="date"
              value={start_date}
              max={end_date || todayISO()}
              onChange={(event) => update({ start_date: event.target.value })}
            />
          </label>
          <label className="field" style={{ minWidth: 142 }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--ink-2)' }}>To</span>
            <input
              type="date"
              value={end_date}
              min={start_date}
              max={todayISO()}
              onChange={(event) => update({ end_date: event.target.value })}
            />
          </label>
        </>
      )}
    </>
  )
}

/** Turns the PeriodFilter state into query parameters for the API. */
export function periodParams(period) {
  if (!period) return {}
  if (period.preset === 'custom') {
    return { start_date: period.start_date || undefined, end_date: period.end_date || undefined }
  }
  if (!period.preset || period.preset === 'all_time') return {}
  return { preset: period.preset }
}
