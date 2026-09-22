import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { KeyRound, Save, ShieldCheck, User as UserIcon } from 'lucide-react'

import { authApi, usersApi } from '../api/endpoints'
import {
  Badge,
  Button,
  Card,
  CardHead,
  Field,
  Input,
  PageHeader,
} from '../components/ui'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { formatDateTime, initials, titleCase } from '../utils/format'

export default function Profile() {
  const { user, refreshUser, logout } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()

  // Navigate explicitly so the next sign-in starts at the dashboard rather than
  // being returned to this page by the protected-route redirect.
  const signOut = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  const [profile, setProfile] = useState({ full_name: '', email: '', phone: '' })
  const [profileErrors, setProfileErrors] = useState({})
  const [savingProfile, setSavingProfile] = useState(false)

  const [passwords, setPasswords] = useState({ current_password: '', new_password: '', confirm: '' })
  const [passwordErrors, setPasswordErrors] = useState({})
  const [savingPassword, setSavingPassword] = useState(false)

  useEffect(() => {
    if (user) {
      setProfile({ full_name: user.full_name, email: user.email, phone: user.phone || '' })
    }
  }, [user])

  const saveProfile = async () => {
    const next = {}
    if (profile.full_name.trim().length < 2) next.full_name = 'Enter your full name.'
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(profile.email.trim())) next.email = 'Enter a valid email address.'
    setProfileErrors(next)
    if (Object.keys(next).length) return

    setSavingProfile(true)
    try {
      await usersApi.updateProfile({
        full_name: profile.full_name.trim(),
        email: profile.email.trim(),
        phone: profile.phone.trim() || null,
      })
      await refreshUser()
      toast.success('Your profile was updated.')
    } catch (error) {
      setProfileErrors(error.fieldErrors)
      toast.error(error.message)
    } finally {
      setSavingProfile(false)
    }
  }

  const changePassword = async () => {
    const next = {}
    if (!passwords.current_password) next.current_password = 'Enter your current password.'
    if (passwords.new_password.length < 8) next.new_password = 'At least 8 characters.'
    if (passwords.new_password !== passwords.confirm) next.confirm = 'The two passwords do not match.'
    setPasswordErrors(next)
    if (Object.keys(next).length) return

    setSavingPassword(true)
    try {
      await authApi.changePassword({
        current_password: passwords.current_password,
        new_password: passwords.new_password,
      })
      setPasswords({ current_password: '', new_password: '', confirm: '' })
      toast.success('Your password was changed.')
    } catch (error) {
      setPasswordErrors(error.fieldErrors)
      toast.error(error.message)
    } finally {
      setSavingPassword(false)
    }
  }

  return (
    <>
      <PageHeader title="My profile" subtitle="Your details and the password you sign in with." />

      {user?.must_change_password && (
        <Card style={{ marginBottom: 14, borderColor: 'var(--warning)' }}>
          <div className="card-body" style={{ fontSize: '0.87rem' }}>
            <strong>Please choose a new password.</strong> Your current one was issued by an
            administrator and should be replaced.
          </div>
        </Card>
      )}

      <div className="grid cols-2">
        <Card>
          <CardHead title="Your details" />
          <div className="card-body">
            <div className="row" style={{ gap: 12, marginBottom: 16 }}>
              <span className="avatar" style={{ width: 52, height: 52, fontSize: '1.1rem' }}>
                {initials(user?.full_name)}
              </span>
              <div>
                <div style={{ fontWeight: 650 }}>{user?.full_name}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--ink-muted)' }}>@{user?.username}</div>
                <div className="row" style={{ gap: 6, marginTop: 5 }}>
                  <Badge status={user?.role} icon={ShieldCheck}>
                    {titleCase(user?.role || '')}
                  </Badge>
                  {user?.is_active && <Badge tone="good">Active</Badge>}
                </div>
              </div>
            </div>

            <div className="form-grid">
              <Field label="Full name" error={profileErrors.full_name} required span2>
                {({ id, invalid }) => (
                  <Input
                    id={id}
                    value={profile.full_name}
                    onChange={(event) => setProfile((c) => ({ ...c, full_name: event.target.value }))}
                    error={invalid}
                  />
                )}
              </Field>
              <Field label="Email address" error={profileErrors.email} required>
                {({ id, invalid }) => (
                  <Input
                    id={id}
                    type="email"
                    value={profile.email}
                    onChange={(event) => setProfile((c) => ({ ...c, email: event.target.value }))}
                    error={invalid}
                  />
                )}
              </Field>
              <Field label="Phone">
                {({ id }) => (
                  <Input
                    id={id}
                    value={profile.phone}
                    onChange={(event) => setProfile((c) => ({ ...c, phone: event.target.value }))}
                  />
                )}
              </Field>
            </div>

            <div className="row end" style={{ marginTop: 14 }}>
              <Button icon={Save} onClick={saveProfile} loading={savingProfile}>
                Save details
              </Button>
            </div>

            <p style={{ fontSize: '0.78rem', color: 'var(--ink-muted)', marginTop: 12 }}>
              Last signed in: {user?.last_login_at ? formatDateTime(user.last_login_at) : 'this session'}
            </p>
          </div>
        </Card>

        <Card>
          <CardHead title="Security" hint="Change your password, or end this session" />
          <div className="card-body">
            <div className="stack" style={{ gap: 12 }}>
              <Field label="Current password" error={passwordErrors.current_password} required>
                {({ id, invalid }) => (
                  <Input
                    id={id}
                    type="password"
                    autoComplete="current-password"
                    value={passwords.current_password}
                    onChange={(event) =>
                      setPasswords((c) => ({ ...c, current_password: event.target.value }))
                    }
                    error={invalid}
                  />
                )}
              </Field>
              <Field
                label="New password"
                error={passwordErrors.new_password}
                required
                help="At least 8 characters. Mix letters with numbers or symbols."
              >
                {({ id, invalid }) => (
                  <Input
                    id={id}
                    type="password"
                    autoComplete="new-password"
                    value={passwords.new_password}
                    onChange={(event) => setPasswords((c) => ({ ...c, new_password: event.target.value }))}
                    error={invalid}
                  />
                )}
              </Field>
              <Field label="Confirm new password" error={passwordErrors.confirm} required>
                {({ id, invalid }) => (
                  <Input
                    id={id}
                    type="password"
                    autoComplete="new-password"
                    value={passwords.confirm}
                    onChange={(event) => setPasswords((c) => ({ ...c, confirm: event.target.value }))}
                    error={invalid}
                  />
                )}
              </Field>

              <div className="row end">
                <Button icon={KeyRound} onClick={changePassword} loading={savingPassword}>
                  Change password
                </Button>
              </div>

              <hr style={{ border: 0, borderTop: '1px solid var(--border)', margin: '6px 0' }} />

              <div className="row between">
                <div style={{ fontSize: '0.84rem', color: 'var(--ink-2)' }}>
                  <UserIcon size={14} style={{ verticalAlign: '-2px' }} /> Signed in as {user?.email}
                </div>
                <Button variant="secondary" onClick={signOut}>
                  Sign out
                </Button>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </>
  )
}
