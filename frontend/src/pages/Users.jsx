import { useEffect, useState } from 'react'
import { KeyRound, Pencil, Plus, ShieldCheck, UserCheck, UserX, Users as UsersIcon } from 'lucide-react'

import { usersApi } from '../api/endpoints'
import DataTable from '../components/DataTable'
import { FilterSelect, SearchBox } from '../components/Filters'
import {
  Badge,
  Button,
  Card,
  ConfirmDialog,
  EmptyState,
  Field,
  Input,
  Modal,
  PageHeader,
  Select,
  TextArea,
} from '../components/ui'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { useListQuery } from '../hooks/useListQuery'
import { formatDate, formatDateTime, titleCase } from '../utils/format'

const ROLES = [
  { value: 'ADMIN', label: 'Administrator — full access' },
  { value: 'MANAGER', label: 'Farm manager — runs the farm and its finances' },
  { value: 'STAFF', label: 'Staff — records daily activity' },
]

const ROLE_FILTER = [
  { value: 'ADMIN', label: 'Administrator' },
  { value: 'MANAGER', label: 'Farm manager' },
  { value: 'STAFF', label: 'Staff' },
]

export default function Users() {
  const { user: me } = useAuth()
  const toast = useToast()
  const query = useListQuery(usersApi.list, { pageSize: 10, sort: 'full_name', order: 'asc' })

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [deactivating, setDeactivating] = useState(null)
  const [resetting, setResetting] = useState(null)
  const [temporaryPassword, setTemporaryPassword] = useState(null)

  const columns = [
    {
      key: 'full_name',
      header: 'User',
      sortable: true,
      render: (row) => (
        <div>
          <div style={{ fontWeight: 650 }}>
            {row.full_name}
            {row.id === me?.id && (
              <span style={{ fontSize: '0.74rem', color: 'var(--ink-muted)', fontWeight: 400 }}> (you)</span>
            )}
          </div>
          <div style={{ fontSize: '0.76rem', color: 'var(--ink-muted)' }}>@{row.username}</div>
        </div>
      ),
    },
    { key: 'email', header: 'Email', sortable: true },
    { key: 'phone', header: 'Phone', render: (row) => row.phone || '—' },
    { key: 'role', header: 'Role', render: (row) => <Badge status={row.role}>{titleCase(row.role)}</Badge> },
    {
      key: 'is_active',
      header: 'Status',
      render: (row) =>
        row.is_active ? <Badge tone="good">Active</Badge> : <Badge tone="critical">Deactivated</Badge>,
    },
    {
      key: 'last_login_at',
      header: 'Last signed in',
      sortable: true,
      render: (row) => (row.last_login_at ? formatDateTime(row.last_login_at) : 'Never'),
    },
    { key: 'created_at', header: 'Added', sortable: true, render: (row) => formatDate(row.created_at) },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (row) => (
        <div className="row-actions">
          <button
            type="button"
            className="icon-btn"
            title="Edit user"
            aria-label={`Edit ${row.full_name}`}
            onClick={() => {
              setEditing(row)
              setFormOpen(true)
            }}
          >
            <Pencil size={15} />
          </button>
          <button
            type="button"
            className="icon-btn"
            title="Reset password"
            aria-label={`Reset the password for ${row.full_name}`}
            onClick={() => setResetting(row)}
          >
            <KeyRound size={15} />
          </button>
          {row.is_active ? (
            <button
              type="button"
              className="icon-btn"
              title="Deactivate user"
              aria-label={`Deactivate ${row.full_name}`}
              onClick={() => setDeactivating(row)}
              disabled={row.id === me?.id}
            >
              <UserX size={15} />
            </button>
          ) : (
            <button
              type="button"
              className="icon-btn"
              title="Re-activate user"
              aria-label={`Re-activate ${row.full_name}`}
              onClick={async () => {
                try {
                  await usersApi.activate(row.id)
                  toast.success(`${row.full_name} can sign in again.`)
                  query.reload()
                } catch (error) {
                  toast.error(error.message)
                }
              }}
            >
              <UserCheck size={15} />
            </button>
          )}
        </div>
      ),
    },
  ]

  const deactivate = async () => {
    try {
      const response = await usersApi.deactivate(deactivating.id)
      toast.success(response.message)
      setDeactivating(null)
      query.reload()
    } catch (error) {
      toast.error(error.message)
      setDeactivating(null)
    }
  }

  const resetPassword = async () => {
    try {
      const response = await usersApi.resetPassword(resetting.id)
      setTemporaryPassword({ user: resetting, ...response })
      setResetting(null)
      query.reload()
    } catch (error) {
      toast.error(error.message)
      setResetting(null)
    }
  }

  return (
    <>
      <PageHeader title="Users" subtitle="Who can use the system, and what each of them is allowed to do.">
        <Button
          icon={Plus}
          onClick={() => {
            setEditing(null)
            setFormOpen(true)
          }}
        >
          Add user
        </Button>
      </PageHeader>

      <Card style={{ marginBottom: 14 }}>
        <div className="card-body" style={{ display: 'grid', gap: 10 }}>
          <div className="row" style={{ gap: 8 }}>
            <ShieldCheck size={17} style={{ color: 'var(--brand-600)' }} aria-hidden="true" />
            <strong style={{ fontSize: '0.9rem' }}>What each role can do</strong>
          </div>
          <div className="grid cols-3" style={{ gap: 12 }}>
            <div style={{ fontSize: '0.82rem', color: 'var(--ink-2)' }}>
              <Badge status="ADMIN">Administrator</Badge>
              <p style={{ marginTop: 6 }}>
                Everything: farm records, finances, users, settings and the audit log.
              </p>
            </div>
            <div style={{ fontSize: '0.82rem', color: 'var(--ink-2)' }}>
              <Badge status="MANAGER">Farm manager</Badge>
              <p style={{ marginTop: 6 }}>
                Birds, feed, health, mortality, sales, expenses, finance and reports — but not users or
                the audit log.
              </p>
            </div>
            <div style={{ fontSize: '0.82rem', color: 'var(--ink-2)' }}>
              <Badge status="STAFF">Staff</Badge>
              <p style={{ marginTop: 6 }}>
                Day-to-day recording: mortality, sickness and feed use. No access to financial pages.
              </p>
            </div>
          </div>
        </div>
      </Card>

      <Card>
        <div className="toolbar">
          <SearchBox value={query.search} onChange={query.onSearch} placeholder="Search name, email or username…" />
          <FilterSelect
            label="Role"
            value={query.filters.role}
            onChange={(value) => query.setFilter('role', value)}
            options={ROLE_FILTER}
            placeholder="All roles"
          />
          <FilterSelect
            label="Status"
            value={query.filters.is_active}
            onChange={(value) => query.setFilter('is_active', value)}
            options={[
              { value: 'true', label: 'Active' },
              { value: 'false', label: 'Deactivated' },
            ]}
            placeholder="All"
          />
        </div>

        <DataTable
          columns={columns}
          rows={query.items}
          loading={query.loading}
          error={query.error}
          onRetry={query.reload}
          sortBy={query.sortBy}
          sortOrder={query.sortOrder}
          onSort={query.toggleSort}
          meta={query.meta}
          page={query.page}
          onPage={query.setPage}
          pageSize={query.pageSize}
          onPageSize={query.setPageSize}
          caption="Users"
          empty={<EmptyState icon={UsersIcon} title="No users match your filters" />}
        />
      </Card>

      <UserForm
        open={formOpen}
        user={editing}
        onClose={() => setFormOpen(false)}
        onSaved={() => {
          setFormOpen(false)
          query.reload()
        }}
      />

      <ConfirmDialog
        open={Boolean(deactivating)}
        title={`Deactivate ${deactivating?.full_name}?`}
        message="They will no longer be able to sign in. Their records stay in the system and you can re-activate them at any time."
        confirmLabel="Deactivate"
        onConfirm={deactivate}
        onClose={() => setDeactivating(null)}
      />

      <ConfirmDialog
        open={Boolean(resetting)}
        title={`Reset the password for ${resetting?.full_name}?`}
        message="A temporary password will be generated and shown once. They will be asked to change it when they next sign in."
        confirmLabel="Reset password"
        destructive={false}
        onConfirm={resetPassword}
        onClose={() => setResetting(null)}
      />

      <Modal
        open={Boolean(temporaryPassword)}
        onClose={() => setTemporaryPassword(null)}
        title="Temporary password"
        hint="This is shown once. Copy it now and pass it on securely."
        size="sm"
        footer={<Button onClick={() => setTemporaryPassword(null)}>Done</Button>}
      >
        <p style={{ fontSize: '0.87rem', color: 'var(--ink-2)', marginBottom: 12 }}>
          {temporaryPassword?.message}
        </p>
        <code
          style={{
            display: 'block',
            padding: '12px 14px',
            borderRadius: 'var(--radius-sm)',
            background: 'var(--surface-3)',
            fontSize: '1.05rem',
            fontFamily: 'ui-monospace, Menlo, monospace',
            letterSpacing: '0.04em',
            wordBreak: 'break-all',
          }}
        >
          {temporaryPassword?.temporary_password}
        </code>
      </Modal>
    </>
  )
}

function UserForm({ open, user, onClose, onSaved }) {
  const toast = useToast()
  const blank = {
    full_name: '',
    username: '',
    email: '',
    phone: '',
    role: 'STAFF',
    password: '',
    is_active: true,
    notes: '',
  }
  const [form, setForm] = useState(blank)
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    setErrors({})
    setForm(
      user
        ? {
            full_name: user.full_name,
            username: user.username,
            email: user.email,
            phone: user.phone || '',
            role: user.role,
            password: '',
            is_active: user.is_active,
            notes: user.notes || '',
          }
        : blank,
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, user])

  const update = (name, value) => {
    setForm((current) => ({ ...current, [name]: value }))
    setErrors((current) => ({ ...current, [name]: undefined }))
  }

  const submit = async (event) => {
    event.preventDefault()
    const next = {}
    if (form.full_name.trim().length < 2) next.full_name = 'Enter the full name.'
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email.trim())) next.email = 'Enter a valid email address.'
    if (!user) {
      if (!/^[A-Za-z0-9._-]{3,}$/.test(form.username.trim())) {
        next.username = 'At least 3 characters; letters, numbers, dots, dashes and underscores only.'
      }
      if (form.password.length < 8) next.password = 'At least 8 characters.'
      else if (/^[A-Za-z]+$/.test(form.password) || /^\d+$/.test(form.password)) {
        next.password = 'Mix letters with numbers or symbols.'
      }
    }
    setErrors(next)
    if (Object.keys(next).length) return

    setSaving(true)
    try {
      if (user) {
        await usersApi.update(user.id, {
          full_name: form.full_name.trim(),
          email: form.email.trim(),
          phone: form.phone.trim() || null,
          role: form.role,
          is_active: form.is_active,
          notes: form.notes.trim() || null,
        })
        toast.success(`${form.full_name} was updated.`)
      } else {
        await usersApi.create({
          full_name: form.full_name.trim(),
          username: form.username.trim(),
          email: form.email.trim(),
          phone: form.phone.trim() || null,
          role: form.role,
          password: form.password,
          is_active: form.is_active,
          notes: form.notes.trim() || null,
        })
        toast.success(`${form.full_name} can now sign in.`)
      }
      onSaved()
    } catch (error) {
      setErrors(error.fieldErrors)
      toast.error(error.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={user ? `Edit ${user.full_name}` : 'Add a user'}
      hint={user ? 'Use the key icon in the list to reset their password.' : 'They can change this password after signing in.'}
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={submit} loading={saving}>
            {user ? 'Save changes' : 'Add user'}
          </Button>
        </>
      }
    >
      <form className="form-grid" onSubmit={submit} noValidate>
        <Field label="Full name" error={errors.full_name} required>
          {({ id, invalid }) => (
            <Input
              id={id}
              value={form.full_name}
              onChange={(event) => update('full_name', event.target.value)}
              error={invalid}
            />
          )}
        </Field>

        <Field label="Username" error={errors.username} required>
          {({ id, invalid }) => (
            <Input
              id={id}
              value={form.username}
              onChange={(event) => update('username', event.target.value)}
              disabled={Boolean(user)}
              error={invalid}
            />
          )}
        </Field>

        <Field label="Email address" error={errors.email} required>
          {({ id, invalid }) => (
            <Input
              id={id}
              type="email"
              value={form.email}
              onChange={(event) => update('email', event.target.value)}
              error={invalid}
            />
          )}
        </Field>

        <Field label="Phone" error={errors.phone}>
          {({ id }) => (
            <Input id={id} value={form.phone} onChange={(event) => update('phone', event.target.value)} />
          )}
        </Field>

        <Field label="Role" error={errors.role} required span2>
          {({ id }) => (
            <Select id={id} value={form.role} onChange={(event) => update('role', event.target.value)} options={ROLES} />
          )}
        </Field>

        {!user && (
          <Field
            label="Password"
            error={errors.password}
            required
            help="At least 8 characters, mixing letters with numbers or symbols."
            span2
          >
            {({ id, invalid }) => (
              <Input
                id={id}
                type="password"
                autoComplete="new-password"
                value={form.password}
                onChange={(event) => update('password', event.target.value)}
                error={invalid}
              />
            )}
          </Field>
        )}

        <Field label="Account status" className="inline-check" span2>
          <label className="row" style={{ gap: 8, fontSize: '0.86rem' }}>
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(event) => update('is_active', event.target.checked)}
              style={{ width: 'auto', minHeight: 0 }}
            />
            This user can sign in
          </label>
        </Field>

        <Field label="Notes" span2>
          {({ id }) => (
            <TextArea id={id} value={form.notes} onChange={(event) => update('notes', event.target.value)} />
          )}
        </Field>
      </form>
    </Modal>
  )
}
