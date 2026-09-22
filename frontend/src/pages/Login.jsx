import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  AlertCircle,
  ArrowRight,
  BarChart3,
  Eye,
  EyeOff,
  ShieldCheck,
  Wheat,
} from 'lucide-react'

import { authApi } from '../api/endpoints'
import Logo from '../components/Logo'
import { Button, Field, Input, Modal } from '../components/ui'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'

export default function Login() {
  const { login } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const location = useLocation()

  const [form, setForm] = useState({ identifier: '', password: '', remember_me: true })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [forgotOpen, setForgotOpen] = useState(false)

  const update = (name, value) => {
    setForm((current) => ({ ...current, [name]: value }))
    setErrors((current) => ({ ...current, [name]: undefined }))
    setFormError('')
  }

  const validate = () => {
    const next = {}
    if (!form.identifier.trim()) next.identifier = 'Enter your email address or username.'
    if (!form.password) next.password = 'Enter your password.'
    setErrors(next)
    return Object.keys(next).length === 0
  }

  const submit = async (event) => {
    event.preventDefault()
    if (!validate()) return

    setSubmitting(true)
    setFormError('')
    try {
      const user = await login({ ...form, identifier: form.identifier.trim() })
      toast.success(`Welcome back, ${user.full_name}.`)
      navigate(location.state?.from?.pathname || '/', { replace: true })
    } catch (error) {
      setFormError(error.message)
      setErrors(error.fieldErrors || {})
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="login-page">
      <aside className="login-aside">
        <Logo size={44} showWordmark tagline="Poultry farm management" />
        <div>
          <h2>Every bird, bag and shilling in one place.</h2>
          <p>
            Record what happens on the farm once, and watch it flow through your stock, your feed
            store, your books and your reports — automatically.
          </p>
          <div className="login-points">
            <div>
              <BarChart3 size={18} aria-hidden="true" />
              <span>Live flock numbers, mortality rates and profit or loss</span>
            </div>
            <div>
              <Wheat size={18} aria-hidden="true" />
              <span>Feed stock that updates itself and warns you before you run out</span>
            </div>
            <div>
              <ShieldCheck size={18} aria-hidden="true" />
              <span>Role-based access with a full audit trail of every change</span>
            </div>
          </div>
        </div>
        <footer>© {new Date().getFullYear()} E&amp;J&apos;s CHICKENS</footer>
      </aside>

      <main className="login-main">
        <div className="login-card">
          <div className="login-brand">
            <Logo size={40} />
            <div>
              <h1>E&amp;J&apos;s CHICKENS</h1>
              <span>Sign in to your farm</span>
            </div>
          </div>

          <form className="login-form" onSubmit={submit} noValidate>
            {formError && (
              <div className="login-alert" role="alert">
                <AlertCircle size={17} style={{ flexShrink: 0, color: 'var(--critical)' }} />
                <span>{formError}</span>
              </div>
            )}

            <Field label="Email or username" name="identifier" error={errors.identifier} required>
              {({ id, invalid }) => (
                <Input
                  id={id}
                  name="identifier"
                  type="text"
                  autoComplete="username"
                  autoFocus
                  value={form.identifier}
                  onChange={(event) => update('identifier', event.target.value)}
                  placeholder="you@ejchickens.com"
                  error={invalid}
                />
              )}
            </Field>

            <Field label="Password" name="password" error={errors.password} required>
              {({ id, invalid }) => (
                <span className="password-field">
                  <Input
                    id={id}
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    value={form.password}
                    onChange={(event) => update('password', event.target.value)}
                    placeholder="Your password"
                    error={invalid}
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    onClick={() => setShowPassword((value) => !value)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                  </button>
                </span>
              )}
            </Field>

            <div className="login-row">
              <label>
                <input
                  type="checkbox"
                  checked={form.remember_me}
                  onChange={(event) => update('remember_me', event.target.checked)}
                />
                Keep me signed in
              </label>
              <button
                type="button"
                className="btn ghost sm"
                onClick={() => setForgotOpen(true)}
                style={{ padding: '2px 4px', minHeight: 0 }}
              >
                Forgot password?
              </button>
            </div>

            <Button type="submit" loading={submitting} className="block" icon={ArrowRight}>
              {submitting ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>

          <div className="login-hint">
            <strong>Development sign-in:</strong> <code>admin@ejchickens.com</code> /{' '}
            <code>Admin@12345</code>
            <br />
            Change this password before using the system on a real farm.
          </div>
        </div>
      </main>

      <ForgotPasswordModal open={forgotOpen} onClose={() => setForgotOpen(false)} />
    </div>
  )
}

function ForgotPasswordModal({ open, onClose }) {
  const toast = useToast()
  const [email, setEmail] = useState('')
  const [token, setToken] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [stage, setStage] = useState('request')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const close = () => {
    setStage('request')
    setEmail('')
    setToken('')
    setNewPassword('')
    setError('')
    onClose()
  }

  const requestReset = async () => {
    setBusy(true)
    setError('')
    try {
      const response = await authApi.forgotPassword(email.trim())
      if (response.reset_token) {
        // Development convenience: with no mail service configured the API
        // returns the token directly so the reset can be completed here.
        setToken(response.reset_token)
        setStage('reset')
      } else {
        toast.info(response.message)
        close()
      }
    } catch (caught) {
      setError(caught.message)
    } finally {
      setBusy(false)
    }
  }

  const completeReset = async () => {
    setBusy(true)
    setError('')
    try {
      await authApi.resetPassword({ token, new_password: newPassword })
      toast.success('Your password has been reset. You can sign in now.')
      close()
    } catch (caught) {
      setError(caught.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={close}
      title="Reset your password"
      size="sm"
      hint={
        stage === 'request'
          ? 'Enter the email address on your account.'
          : 'Choose a new password of at least 8 characters.'
      }
      footer={
        <>
          <Button variant="secondary" onClick={close} disabled={busy}>
            Cancel
          </Button>
          {stage === 'request' ? (
            <Button onClick={requestReset} loading={busy} disabled={!email.trim()}>
              Continue
            </Button>
          ) : (
            <Button onClick={completeReset} loading={busy} disabled={newPassword.length < 8}>
              Set new password
            </Button>
          )}
        </>
      }
    >
      {error && (
        <div className="login-alert" role="alert" style={{ marginBottom: 12 }}>
          <AlertCircle size={16} style={{ flexShrink: 0, color: 'var(--critical)' }} />
          <span>{error}</span>
        </div>
      )}
      {stage === 'request' ? (
        <Field label="Email address" required>
          {({ id }) => (
            <Input
              id={id}
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@ejchickens.com"
            />
          )}
        </Field>
      ) : (
        <Field label="New password" required help="At least 8 characters.">
          {({ id }) => (
            <Input
              id={id}
              type="password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              placeholder="New password"
            />
          )}
        </Field>
      )}
    </Modal>
  )
}
