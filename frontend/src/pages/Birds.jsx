import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Egg, Minus, Pencil, Plus, Trash2 } from 'lucide-react'

import { birdsApi } from '../api/endpoints'
import DataTable from '../components/DataTable'
import { FilterSelect, SearchBox } from '../components/Filters'
import StatCard from '../components/StatCard'
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
import { useSettings } from '../contexts/SettingsContext'
import { useToast } from '../contexts/ToastContext'
import { useListQuery } from '../hooks/useListQuery'
import { formatDate, formatMoney, formatNumber, formatPercent, titleCase, todayISO } from '../utils/format'

const STATUS_OPTIONS = [
  { value: 'ACTIVE', label: 'Active' },
  { value: 'SOLD_OUT', label: 'Sold out' },
  { value: 'CLOSED', label: 'Closed' },
]

const EMPTY = {
  batch_code: '',
  breed: '',
  initial_quantity: '',
  acquisition_date: todayISO(),
  source: '',
  age_days_at_acquisition: '0',
  cost_per_bird: '',
  notes: '',
}

export default function Birds() {
  const { isManager, isAdmin } = useAuth()
  const { currency } = useSettings()
  const toast = useToast()
  const [searchParams, setSearchParams] = useSearchParams()

  const query = useListQuery(birdsApi.list, { pageSize: 10, sort: 'acquisition_date', order: 'desc' })
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [adjusting, setAdjusting] = useState(null)
  const [deleting, setDeleting] = useState(null)

  // A search typed in the top bar arrives as ?q=
  useEffect(() => {
    const q = searchParams.get('q')
    if (q) {
      query.onSearch(q)
      setSearchParams({}, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams])

  const totals = query.items.reduce(
    (accumulator, batch) => ({
      current: accumulator.current + batch.current_quantity,
      sick: accumulator.sick + batch.sick_count,
      deaths: accumulator.deaths + batch.total_deaths,
      sold: accumulator.sold + batch.total_sold,
    }),
    { current: 0, sick: 0, deaths: 0, sold: 0 },
  )

  const columns = [
    {
      key: 'batch_code',
      header: 'Batch',
      sortable: true,
      render: (row) => (
        <div>
          <div style={{ fontWeight: 650 }}>{row.batch_code}</div>
          <div style={{ fontSize: '0.76rem', color: 'var(--ink-muted)' }}>{row.breed}</div>
        </div>
      ),
    },
    { key: 'acquisition_date', header: 'Acquired', sortable: true, render: (row) => formatDate(row.acquisition_date) },
    { key: 'age_days', header: 'Age', align: 'right', render: (row) => `${formatNumber(row.age_days)} d` },
    { key: 'initial_quantity', header: 'Initial', align: 'right', sortable: true, render: (row) => formatNumber(row.initial_quantity) },
    { key: 'total_deaths', header: 'Died', align: 'right', render: (row) => formatNumber(row.total_deaths) },
    { key: 'total_sold', header: 'Sold', align: 'right', render: (row) => formatNumber(row.total_sold) },
    {
      key: 'current_quantity',
      header: 'Current',
      align: 'right',
      render: (row) => <strong>{formatNumber(row.current_quantity)}</strong>,
    },
    {
      key: 'sick_count',
      header: 'Sick',
      align: 'right',
      render: (row) =>
        row.sick_count > 0 ? <Badge tone="warning">{formatNumber(row.sick_count)}</Badge> : '—',
    },
    {
      key: 'mortality_rate',
      header: 'Mortality',
      align: 'right',
      render: (row) => (
        <span style={{ color: row.mortality_rate >= 5 ? 'var(--critical)' : 'inherit' }}>
          {formatPercent(row.mortality_rate, 2)}
        </span>
      ),
    },
    {
      key: 'total_acquisition_cost',
      header: 'Cost',
      align: 'right',
      render: (row) => formatMoney(row.total_acquisition_cost, currency),
    },
    { key: 'status', header: 'Status', render: (row) => <Badge status={row.status}>{titleCase(row.status)}</Badge> },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (row) => (
          <div className="row-actions">
            <button
              type="button"
              className="icon-btn"
              title="Edit batch"
              aria-label={`Edit ${row.batch_code}`}
              onClick={() => {
                setEditing(row)
                setFormOpen(true)
              }}
            >
              <Pencil size={15} />
            </button>
            {isManager && (
            <button
              type="button"
              className="icon-btn"
              title="Record a loss (theft, escape, miscount)"
              aria-label={`Record a loss for ${row.batch_code}`}
              onClick={() => setAdjusting(row)}
            >
              <Minus size={15} />
            </button>
            )}
            {isAdmin && (
              <button
                type="button"
                className="icon-btn"
                title="Delete batch"
                aria-label={`Delete ${row.batch_code}`}
                onClick={() => setDeleting(row)}
              >
                <Trash2 size={15} />
              </button>
            )}
          </div>
      ),
    },
  ]

  const removeBatch = async () => {
    try {
      await birdsApi.remove(deleting.id)
      toast.success(`Batch ${deleting.batch_code} was removed.`)
      setDeleting(null)
      query.reload()
    } catch (error) {
      toast.error(error.message)
      setDeleting(null)
    }
  }

  return (
    <>
      <PageHeader title="Birds" subtitle="Every batch on the farm, with live population figures.">
        {isManager && (
          <Button
            icon={Plus}
            onClick={() => {
              setEditing(null)
              setFormOpen(true)
            }}
          >
            Add batch
          </Button>
        )}
      </PageHeader>

      <div className="grid cols-4" style={{ marginBottom: 14 }}>
        <StatCard label="Birds on this page" value={formatNumber(totals.current)} icon={Egg} tone="brand" />
        <StatCard label="Sick" value={formatNumber(totals.sick)} tone={totals.sick ? 'warning' : ''} />
        <StatCard label="Died" value={formatNumber(totals.deaths)} tone={totals.deaths ? 'critical' : ''} />
        <StatCard label="Sold" value={formatNumber(totals.sold)} tone="info" />
      </div>

      <Card>
        <div className="toolbar">
          <SearchBox
            value={query.search}
            onChange={query.onSearch}
            placeholder="Search by batch code, breed or source…"
          />
          <FilterSelect
            label="Status"
            value={query.filters.status}
            onChange={(value) => query.setFilter('status', value)}
            options={STATUS_OPTIONS}
            placeholder="All statuses"
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
          caption="Bird batches"
          empty={
            <EmptyState
              icon={Egg}
              title={query.search || query.filters.status ? 'No batches match your filters' : 'No bird batches have been added yet'}
              message={
                query.search || query.filters.status
                  ? 'Try clearing the search box or choosing a different status.'
                  : 'Add your first batch to start tracking birds, deaths, sales and costs.'
              }
              action={
                isManager && !query.search ? (
                  <Button
                    icon={Plus}
                    onClick={() => {
                      setEditing(null)
                      setFormOpen(true)
                    }}
                  >
                    Add first batch
                  </Button>
                ) : null
              }
            />
          }
        />
      </Card>

      <BatchForm
        open={formOpen}
        batch={editing}
        currency={currency}
        canEditFigures={isManager}
        onClose={() => setFormOpen(false)}
        onSaved={() => {
          setFormOpen(false)
          query.reload()
        }}
      />

      <AdjustForm
        batch={adjusting}
        onClose={() => setAdjusting(null)}
        onSaved={() => {
          setAdjusting(null)
          query.reload()
        }}
      />

      <ConfirmDialog
        open={Boolean(deleting)}
        title={`Delete ${deleting?.batch_code}?`}
        message="This batch will be removed from the farm records. Batches that already have mortality or sales recorded against them cannot be deleted — close them instead so the history is kept."
        confirmLabel="Delete batch"
        onConfirm={removeBatch}
        onClose={() => setDeleting(null)}
      />
    </>
  )
}

function BatchForm({ open, batch, currency, canEditFigures = true, onClose, onSaved }) {
  const toast = useToast()
  const [form, setForm] = useState(EMPTY)
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    setErrors({})
    setForm(
      batch
        ? {
            batch_code: batch.batch_code,
            breed: batch.breed,
            initial_quantity: String(batch.initial_quantity),
            acquisition_date: batch.acquisition_date,
            source: batch.source || '',
            age_days_at_acquisition: String(batch.age_days_at_acquisition ?? 0),
            cost_per_bird: batch.cost_per_bird ?? '',
            notes: batch.notes || '',
            status: batch.status,
          }
        : EMPTY,
    )
  }, [open, batch])

  const update = (name, value) => {
    setForm((current) => ({ ...current, [name]: value }))
    setErrors((current) => ({ ...current, [name]: undefined }))
  }

  const validate = () => {
    const next = {}
    if (!batch && form.batch_code.trim().length < 2) next.batch_code = 'Give the batch a code, e.g. BROILER-001.'
    if (form.breed.trim().length < 2) next.breed = 'Enter the breed.'
    if (canEditFigures) {
      const quantity = Number(form.initial_quantity)
      if (!Number.isInteger(quantity) || quantity <= 0) {
        next.initial_quantity = 'Enter a whole number greater than zero.'
      }
      if (!form.acquisition_date) next.acquisition_date = 'Choose the date the birds arrived.'
      else if (form.acquisition_date > todayISO()) next.acquisition_date = 'The date cannot be in the future.'
      if (form.cost_per_bird !== '' && Number(form.cost_per_bird) < 0) {
        next.cost_per_bird = 'Cost cannot be negative.'
      }
    }
    setErrors(next)
    return Object.keys(next).length === 0
  }

  const submit = async (event) => {
    event.preventDefault()
    if (!validate()) return

    // Staff may only change the descriptive fields — the server enforces this
    // too, so sending anything else would simply be refused.
    const descriptive = {
      breed: form.breed.trim(),
      source: form.source.trim() || null,
      age_days_at_acquisition: Number(form.age_days_at_acquisition || 0),
      notes: form.notes.trim() || null,
    }
    const payload = canEditFigures
      ? {
          ...descriptive,
          initial_quantity: Number(form.initial_quantity),
          acquisition_date: form.acquisition_date,
          cost_per_bird: form.cost_per_bird === '' ? '0' : String(form.cost_per_bird),
        }
      : descriptive

    setSaving(true)
    try {
      if (batch) {
        await birdsApi.update(batch.id, canEditFigures ? { ...payload, status: form.status } : payload)
        toast.success(`Batch ${batch.batch_code} was updated.`)
      } else {
        await birdsApi.create({ ...payload, batch_code: form.batch_code.trim().toUpperCase() })
        toast.success('The batch was added and its purchase cost recorded as an expense.')
      }
      onSaved()
    } catch (error) {
      setErrors(error.fieldErrors)
      toast.error(error.message)
    } finally {
      setSaving(false)
    }
  }

  const total = Number(form.initial_quantity || 0) * Number(form.cost_per_bird || 0)

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={batch ? `Edit ${batch.batch_code}` : 'Add a bird batch'}
      hint={
        !canEditFigures
          ? 'You can update the breed, source, age and notes. Quantity, cost and status need a manager.'
          : batch
            ? 'Changing the cost updates the matching expense entry automatically.'
            : 'The acquisition cost is recorded as an expense under “Birds” automatically.'
      }
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={submit} loading={saving}>
            {batch ? 'Save changes' : 'Add batch'}
          </Button>
        </>
      }
    >
      <form className="form-grid" onSubmit={submit} noValidate>
        <Field label="Batch code" error={errors.batch_code} required>
          {({ id, invalid }) => (
            <Input
              id={id}
              value={form.batch_code}
              onChange={(event) => update('batch_code', event.target.value)}
              placeholder="BROILER-001"
              disabled={Boolean(batch)}
              error={invalid}
            />
          )}
        </Field>

        <Field label="Breed" error={errors.breed} required>
          {({ id, invalid }) => (
            <Input
              id={id}
              value={form.breed}
              onChange={(event) => update('breed', event.target.value)}
              placeholder="Broiler"
              error={invalid}
            />
          )}
        </Field>

        <Field label="Number of birds" error={errors.initial_quantity} required>
          {({ id, invalid }) => (
            <Input
              id={id}
              type="number"
              min="1"
              step="1"
              value={form.initial_quantity}
              onChange={(event) => update('initial_quantity', event.target.value)}
              disabled={!canEditFigures}
              placeholder="500"
              error={invalid}
            />
          )}
        </Field>

        <Field label="Date acquired" error={errors.acquisition_date} required>
          {({ id, invalid }) => (
            <Input
              id={id}
              type="date"
              max={todayISO()}
              value={form.acquisition_date}
              onChange={(event) => update('acquisition_date', event.target.value)}
              disabled={!canEditFigures}
              error={invalid}
            />
          )}
        </Field>

        <Field label="Source / supplier" error={errors.source}>
          {({ id }) => (
            <Input
              id={id}
              value={form.source}
              onChange={(event) => update('source', event.target.value)}
              placeholder="Ugachick Hatchery"
            />
          )}
        </Field>

        <Field label="Age on arrival (days)" error={errors.age_days_at_acquisition}>
          {({ id }) => (
            <Input
              id={id}
              type="number"
              min="0"
              value={form.age_days_at_acquisition}
              onChange={(event) => update('age_days_at_acquisition', event.target.value)}
            />
          )}
        </Field>

        <Field
          label="Cost per bird"
          error={errors.cost_per_bird}
          help={total > 0 ? `Total acquisition cost: ${formatMoney(total, currency)}` : undefined}
        >
          {({ id, invalid }) => (
            <Input
              id={id}
              type="number"
              min="0"
              step="1"
              prefix={currency}
              value={form.cost_per_bird}
              onChange={(event) => update('cost_per_bird', event.target.value)}
              disabled={!canEditFigures}
              placeholder="2300"
              error={invalid}
            />
          )}
        </Field>

        {batch && canEditFigures && (
          <Field label="Status">
            {({ id }) => (
              <Select
                id={id}
                value={form.status}
                onChange={(event) => update('status', event.target.value)}
                options={STATUS_OPTIONS}
              />
            )}
          </Field>
        )}

        <Field label="Notes" span2>
          {({ id }) => (
            <TextArea
              id={id}
              value={form.notes}
              onChange={(event) => update('notes', event.target.value)}
              placeholder="Anything worth remembering about this batch…"
            />
          )}
        </Field>
      </form>
    </Modal>
  )
}

function AdjustForm({ batch, onClose, onSaved }) {
  const toast = useToast()
  const [quantity, setQuantity] = useState('')
  const [reason, setReason] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    setQuantity('')
    setReason('')
    setError('')
  }, [batch])

  const submit = async () => {
    const amount = Number(quantity)
    if (!Number.isInteger(amount) || amount <= 0) {
      setError('Enter a whole number greater than zero.')
      return
    }
    if (amount > batch.current_quantity) {
      setError(`This batch only has ${batch.current_quantity} birds left.`)
      return
    }
    if (reason.trim().length < 3) {
      setError('Give a short reason so the record makes sense later.')
      return
    }

    setSaving(true)
    try {
      await birdsApi.adjust(batch.id, { quantity: amount, reason: reason.trim() })
      toast.success(`${amount} bird(s) removed from ${batch.batch_code}.`)
      onSaved()
    } catch (caught) {
      setError(caught.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={Boolean(batch)}
      onClose={onClose}
      title={`Record a loss in ${batch?.batch_code || ''}`}
      hint="For birds lost to theft, escape or a corrected miscount. Deaths belong in the Mortality module so the mortality rate stays accurate."
      size="sm"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={submit} loading={saving}>
            Record loss
          </Button>
        </>
      }
    >
      <div className="stack" style={{ gap: 12 }}>
        {error && (
          <div className="login-alert" role="alert">
            <span>{error}</span>
          </div>
        )}
        <Field label="Number of birds" required help={batch ? `${batch.current_quantity} birds currently in this batch.` : ''}>
          {({ id }) => (
            <Input
              id={id}
              type="number"
              min="1"
              max={batch?.current_quantity}
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
            />
          )}
        </Field>
        <Field label="Reason" required>
          {({ id }) => (
            <Input
              id={id}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="Stolen overnight / escaped / miscount corrected"
            />
          )}
        </Field>
      </div>
    </Modal>
  )
}
