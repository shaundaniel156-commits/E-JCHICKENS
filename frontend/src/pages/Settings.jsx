import { useEffect, useState } from 'react'
import { Bell, Building2, Monitor, Moon, Save, Sun } from 'lucide-react'

import { settingsApi } from '../api/endpoints'
import { Button, Card, CardHead, Field, Input, PageHeader, Select, Spinner } from '../components/ui'
import { useAuth } from '../contexts/AuthContext'
import { useSettings } from '../contexts/SettingsContext'
import { useToast } from '../contexts/ToastContext'
import { toNumber } from '../utils/format'

const CURRENCIES = [
  { value: 'UGX', label: 'UGX — Ugandan shilling' },
  { value: 'KES', label: 'KES — Kenyan shilling' },
  { value: 'TZS', label: 'TZS — Tanzanian shilling' },
  { value: 'USD', label: 'USD — US dollar' },
]

const DATE_FORMATS = [
  { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY (31/12/2026)' },
  { value: 'MM/DD/YYYY', label: 'MM/DD/YYYY (12/31/2026)' },
  { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD (2026-12-31)' },
]

const THEMES = [
  { value: 'system', label: 'Match my device', icon: Monitor },
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
]

export default function Settings() {
  const { isAdmin } = useAuth()
  const { settings, reload, theme, setTheme } = useSettings()
  const toast = useToast()

  const [form, setForm] = useState(null)
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (settings?.id) {
      setForm({
        farm_name: settings.farm_name || '',
        owner_name: settings.owner_name || '',
        location: settings.location || '',
        phone: settings.phone || '',
        email: settings.email || '',
        logo_url: settings.logo_url || '',
        currency: settings.currency || 'UGX',
        date_format: settings.date_format || 'DD/MM/YYYY',
        low_feed_threshold_bags: settings.low_feed_threshold_bags ?? '5',
        high_mortality_rate_percent: settings.high_mortality_rate_percent ?? '5',
        budget_warning_percent: settings.budget_warning_percent ?? '80',
        notifications_enabled: settings.notifications_enabled ?? true,
      })
    }
  }, [settings])

  if (!form) return <Spinner label="Loading settings…" />

  const update = (name, value) => {
    setForm((current) => ({ ...current, [name]: value }))
    setErrors((current) => ({ ...current, [name]: undefined }))
  }

  const save = async () => {
    const next = {}
    if (form.farm_name.trim().length < 2) next.farm_name = 'Enter the farm name.'
    if (form.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email.trim())) {
      next.email = 'Enter a valid email address.'
    }
    if (toNumber(form.low_feed_threshold_bags) < 0) next.low_feed_threshold_bags = 'Cannot be negative.'
    const mortality = toNumber(form.high_mortality_rate_percent)
    if (mortality < 0 || mortality > 100) next.high_mortality_rate_percent = 'Enter a value between 0 and 100.'
    const budget = toNumber(form.budget_warning_percent)
    if (budget < 0 || budget > 100) next.budget_warning_percent = 'Enter a value between 0 and 100.'
    setErrors(next)
    if (Object.keys(next).length) return

    setSaving(true)
    try {
      await settingsApi.update({
        farm_name: form.farm_name.trim(),
        owner_name: form.owner_name.trim() || null,
        location: form.location.trim() || null,
        phone: form.phone.trim() || null,
        email: form.email.trim() || null,
        logo_url: form.logo_url.trim() || null,
        currency: form.currency,
        date_format: form.date_format,
        low_feed_threshold_bags: String(form.low_feed_threshold_bags),
        high_mortality_rate_percent: String(form.high_mortality_rate_percent),
        budget_warning_percent: String(form.budget_warning_percent),
        notifications_enabled: form.notifications_enabled,
      })
      await reload()
      toast.success('Your settings were saved.')
    } catch (error) {
      setErrors(error.fieldErrors)
      toast.error(error.message)
    } finally {
      setSaving(false)
    }
  }

  const readOnly = !isAdmin

  return (
    <>
      <PageHeader title="Settings" subtitle="Farm details, currency and the thresholds that trigger alerts.">
        {isAdmin && (
          <Button icon={Save} onClick={save} loading={saving}>
            Save settings
          </Button>
        )}
      </PageHeader>

      {readOnly && (
        <Card style={{ marginBottom: 14 }}>
          <div className="card-body" style={{ fontSize: '0.86rem', color: 'var(--ink-2)' }}>
            You can view these settings, but only an administrator can change them. Your own name,
            email and password are on the <a href="/profile">profile page</a>.
          </div>
        </Card>
      )}

      <div className="grid cols-2" style={{ marginBottom: 14 }}>
        <Card>
          <CardHead title="Farm information" hint="Shown on reports and exports" />
          <div className="card-body">
            <div className="form-grid">
              <Field label="Farm name" error={errors.farm_name} required span2>
                {({ id, invalid }) => (
                  <Input
                    id={id}
                    value={form.farm_name}
                    onChange={(event) => update('farm_name', event.target.value)}
                    disabled={readOnly}
                    error={invalid}
                  />
                )}
              </Field>
              <Field label="Owner">
                {({ id }) => (
                  <Input
                    id={id}
                    value={form.owner_name}
                    onChange={(event) => update('owner_name', event.target.value)}
                    disabled={readOnly}
                  />
                )}
              </Field>
              <Field label="Location">
                {({ id }) => (
                  <Input
                    id={id}
                    value={form.location}
                    onChange={(event) => update('location', event.target.value)}
                    placeholder="Wakiso, Uganda"
                    disabled={readOnly}
                  />
                )}
              </Field>
              <Field label="Phone">
                {({ id }) => (
                  <Input
                    id={id}
                    value={form.phone}
                    onChange={(event) => update('phone', event.target.value)}
                    disabled={readOnly}
                  />
                )}
              </Field>
              <Field label="Email" error={errors.email}>
                {({ id, invalid }) => (
                  <Input
                    id={id}
                    type="email"
                    value={form.email}
                    onChange={(event) => update('email', event.target.value)}
                    disabled={readOnly}
                    error={invalid}
                  />
                )}
              </Field>
              <Field label="Logo link" help="A link to your own logo image, used on reports." span2>
                {({ id }) => (
                  <Input
                    id={id}
                    type="url"
                    value={form.logo_url}
                    onChange={(event) => update('logo_url', event.target.value)}
                    placeholder="https://…"
                    disabled={readOnly}
                  />
                )}
              </Field>
            </div>
          </div>
        </Card>

        <Card>
          <CardHead title="System" hint="Currency, dates and how the app looks" />
          <div className="card-body">
            <div className="form-grid">
              <Field label="Currency">
                {({ id }) => (
                  <Select
                    id={id}
                    value={form.currency}
                    onChange={(event) => update('currency', event.target.value)}
                    options={CURRENCIES}
                    disabled={readOnly}
                  />
                )}
              </Field>
              <Field label="Date format">
                {({ id }) => (
                  <Select
                    id={id}
                    value={form.date_format}
                    onChange={(event) => update('date_format', event.target.value)}
                    options={DATE_FORMATS}
                    disabled={readOnly}
                  />
                )}
              </Field>
              <Field label="Appearance" span2 help="Saved on this device only.">
                <div className="row" style={{ gap: 8 }}>
                  {THEMES.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      className={`btn ${theme === option.value ? '' : 'secondary'} sm`}
                      onClick={() => setTheme(option.value)}
                      aria-pressed={theme === option.value}
                    >
                      <option.icon size={15} /> {option.label}
                    </button>
                  ))}
                </div>
              </Field>
            </div>
          </div>
        </Card>
      </div>

      <Card style={{ marginBottom: 14 }}>
        <CardHead
          title="Alert thresholds"
          hint="These decide when the system warns you. Changing them affects future alerts."
        />
        <div className="card-body">
          <div className="form-grid">
            <Field
              label="Warn when feed falls below (bags)"
              error={errors.low_feed_threshold_bags}
              help="A feed type below this level is flagged as low stock."
            >
              {({ id, invalid }) => (
                <Input
                  id={id}
                  type="number"
                  min="0"
                  step="1"
                  value={form.low_feed_threshold_bags}
                  onChange={(event) => update('low_feed_threshold_bags', event.target.value)}
                  disabled={readOnly}
                  error={invalid}
                />
              )}
            </Field>

            <Field
              label="Warn when mortality exceeds (%)"
              error={errors.high_mortality_rate_percent}
              help="Raised per batch, against the birds that were exposed to risk."
            >
              {({ id, invalid }) => (
                <Input
                  id={id}
                  type="number"
                  min="0"
                  max="100"
                  step="0.5"
                  value={form.high_mortality_rate_percent}
                  onChange={(event) => update('high_mortality_rate_percent', event.target.value)}
                  disabled={readOnly}
                  error={invalid}
                />
              )}
            </Field>

            <Field
              label="Warn when the budget is spent beyond (%)"
              error={errors.budget_warning_percent}
              help="A second, stronger alert fires if the budget is exceeded."
            >
              {({ id, invalid }) => (
                <Input
                  id={id}
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  value={form.budget_warning_percent}
                  onChange={(event) => update('budget_warning_percent', event.target.value)}
                  disabled={readOnly}
                  error={invalid}
                />
              )}
            </Field>

            <Field label="Notifications" className="inline-check">
              <label className="row" style={{ gap: 8, fontSize: '0.86rem' }}>
                <input
                  type="checkbox"
                  checked={form.notifications_enabled}
                  onChange={(event) => update('notifications_enabled', event.target.checked)}
                  disabled={readOnly}
                  style={{ width: 'auto', minHeight: 0 }}
                />
                <Bell size={15} aria-hidden="true" /> Raise automatic notifications
              </label>
            </Field>
          </div>
        </div>
      </Card>

      {isAdmin && (
        <div className="row end">
          <Button icon={Save} onClick={save} loading={saving}>
            Save settings
          </Button>
        </div>
      )}
    </>
  )
}
