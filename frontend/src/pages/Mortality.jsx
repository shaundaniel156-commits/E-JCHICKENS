import { useEffect, useMemo, useState } from 'react'
import { Pencil, Plus, Skull, Trash2 } from 'lucide-react'

import { mortalityApi } from '../api/endpoints'
import { MortalityChart } from '../components/charts'
import DataTable from '../components/DataTable'
import { FilterSelect, PeriodFilter, SearchBox, periodParams } from '../components/Filters'
import StatCard from '../components/StatCard'
import {
  Button,
  Card,
  CardHead,
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
import { useApi } from '../hooks/useApi'
import { useListQuery } from '../hooks/useListQuery'
import { useBatchOptions } from '../hooks/useOptions'
import { formatDate, formatNumber, todayISO } from '../utils/format'

const CAUSES = [
  'Respiratory infection',
  'Coccidiosis',
  'Newcastle disease',
  'Gumboro',
  'Heat stress',
  'Cold stress',
  'Crushing / piling',
  'Predator',
  'Unknown',
]

const GROUPINGS = [
  { value: 'day', label: 'By day' },
  { value: 'week', label: 'By week' },
  { value: 'month', label: 'By month' },
]

export default function Mortality() {
  const { isManager } = useAuth()
  const toast = useToast()
  const { options: batchOptions, reload: reloadBatches } = useBatchOptions()

  const [period, setPeriod] = useState({ preset: 'all_time', start_date: '', end_date: '' })
  const [grouping, setGrouping] = useState('day')
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [deleting, setDeleting] = useState(null)

  const query = useListQuery(mortalityApi.list, { pageSize: 10, sort: 'record_date', order: 'desc' })

  useEffect(() => {
    query.setFilters(periodParams(period))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period])

  const series = useApi(() => mortalityApi.series({ grouping }), [grouping])

  const totals = useMemo(
    () => query.items.reduce((sum, row) => sum + row.quantity, 0),
    [query.items],
  )

  const columns = [
    { key: 'record_date', header: 'Date', sortable: true, render: (row) => formatDate(row.record_date) },
    { key: 'batch_code', header: 'Batch', render: (row) => row.batch_code || '—' },
    {
      key: 'quantity',
      header: 'Deaths',
      align: 'right',
      sortable: true,
      render: (row) => <strong>{formatNumber(row.quantity)}</strong>,
    },
    { key: 'cause', header: 'Suspected cause', className: 'wrap', render: (row) => row.cause || '—' },
    { key: 'notes', header: 'Notes', className: 'wrap', render: (row) => row.notes || '—' },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (row) =>
        isManager ? (
          <div className="row-actions">
            <button
              type="button"
              className="icon-btn"
              aria-label="Edit record"
              title="Edit record"
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
              aria-label="Reverse record"
              title="Reverse record"
              onClick={() => setDeleting(row)}
            >
              <Trash2 size={15} />
            </button>
          </div>
        ) : null,
    },
  ]

  const reverse = async () => {
    try {
      await mortalityApi.remove(deleting.id)
      toast.success('The record was reversed and the birds returned to the batch.')
      setDeleting(null)
      query.reload()
      series.reload()
      reloadBatches()
    } catch (error) {
      toast.error(error.message)
      setDeleting(null)
    }
  }

  return (
    <>
      <PageHeader
        title="Mortality"
        subtitle="Recorded deaths. Every entry reduces the batch population immediately."
      >
        <Button
          icon={Plus}
          onClick={() => {
            setEditing(null)
            setFormOpen(true)
          }}
        >
          Record deaths
        </Button>
      </PageHeader>

      <div className="grid cols-2" style={{ marginBottom: 14 }}>
        <StatCard
          label="Deaths in the current view"
          value={formatNumber(totals)}
          meta={`${query.meta.total} record${query.meta.total === 1 ? '' : 's'} match your filters`}
          icon={Skull}
          tone={totals > 0 ? 'critical' : ''}
        />
        <Card>
          <CardHead title="Deaths over time" hint="Grouped as you choose below">
            <Select
              value={grouping}
              onChange={(event) => setGrouping(event.target.value)}
              options={GROUPINGS}
              aria-label="Group mortality by"
              style={{ minHeight: 32, padding: '4px 8px', fontSize: '0.8rem' }}
            />
          </CardHead>
          <div className="card-body tight">
            <MortalityChart data={series.data ?? []} height={180} />
          </div>
        </Card>
      </div>

      <Card>
        <div className="toolbar">
          <SearchBox value={query.search} onChange={query.onSearch} placeholder="Search by cause or note…" />
          <FilterSelect
            label="Batch"
            value={query.filters.batch_id}
            onChange={(value) => query.setFilter('batch_id', value)}
            options={batchOptions}
            placeholder="All batches"
          />
          <PeriodFilter value={period} onChange={setPeriod} />
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
          caption="Mortality records"
          empty={
            <EmptyState
              icon={Skull}
              title="No deaths recorded"
              message="That is good news. If birds are lost, record them here so the flock count and mortality rate stay accurate."
              action={
                <Button
                  icon={Plus}
                  onClick={() => {
                    setEditing(null)
                    setFormOpen(true)
                  }}
                >
                  Record deaths
                </Button>
              }
            />
          }
        />
      </Card>

      <MortalityForm
        open={formOpen}
        record={editing}
        batchOptions={batchOptions}
        onClose={() => setFormOpen(false)}
        onSaved={() => {
          setFormOpen(false)
          query.reload()
          series.reload()
          reloadBatches()
        }}
      />

      <ConfirmDialog
        open={Boolean(deleting)}
        title="Reverse this mortality record?"
        message={`${deleting?.quantity} bird(s) will be returned to batch ${deleting?.batch_code}. The record is kept in the audit trail rather than erased.`}
        confirmLabel="Reverse record"
        onConfirm={reverse}
        onClose={() => setDeleting(null)}
      />
    </>
  )
}

function MortalityForm({ open, record, batchOptions, onClose, onSaved }) {
  const toast = useToast()
  const [form, setForm] = useState({ batch_id: '', record_date: todayISO(), quantity: '', cause: '', notes: '' })
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    setErrors({})
    setForm(
      record
        ? {
            batch_id: String(record.batch_id),
            record_date: record.record_date,
            quantity: String(record.quantity),
            cause: record.cause || '',
            notes: record.notes || '',
          }
        : { batch_id: '', record_date: todayISO(), quantity: '', cause: '', notes: '' },
    )
  }, [open, record])

  const selected = batchOptions.find((option) => option.value === form.batch_id)

  const update = (name, value) => {
    setForm((current) => ({ ...current, [name]: value }))
    setErrors((current) => ({ ...current, [name]: undefined }))
  }

  const submit = async (event) => {
    event.preventDefault()
    const next = {}
    if (!record && !form.batch_id) next.batch_id = 'Choose the batch the birds came from.'
    const quantity = Number(form.quantity)
    if (!Number.isInteger(quantity) || quantity <= 0) next.quantity = 'Enter a whole number greater than zero.'
    else if (selected && !record && quantity > selected.available) {
      next.quantity = `That batch only has ${selected.available} bird(s).`
    }
    if (!form.record_date) next.record_date = 'Choose the date.'
    else if (form.record_date > todayISO()) next.record_date = 'The date cannot be in the future.'
    setErrors(next)
    if (Object.keys(next).length) return

    setSaving(true)
    try {
      const payload = {
        record_date: form.record_date,
        quantity,
        cause: form.cause.trim() || null,
        notes: form.notes.trim() || null,
      }
      if (record) await mortalityApi.update(record.id, payload)
      else await mortalityApi.create({ ...payload, batch_id: Number(form.batch_id) })
      toast.success(record ? 'The record was updated.' : `${quantity} death(s) recorded.`)
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
      title={record ? 'Edit mortality record' : 'Record deaths'}
      hint="The batch population and the mortality rate update as soon as you save."
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={submit} loading={saving}>
            {record ? 'Save changes' : 'Record deaths'}
          </Button>
        </>
      }
    >
      <form className="form-grid" onSubmit={submit} noValidate>
        <Field label="Batch" error={errors.batch_id} required>
          {({ id, invalid }) => (
            <Select
              id={id}
              value={form.batch_id}
              onChange={(event) => update('batch_id', event.target.value)}
              options={batchOptions}
              placeholder="Choose a batch…"
              disabled={Boolean(record)}
              error={invalid}
            />
          )}
        </Field>

        <Field label="Date" error={errors.record_date} required>
          {({ id, invalid }) => (
            <Input
              id={id}
              type="date"
              max={todayISO()}
              value={form.record_date}
              onChange={(event) => update('record_date', event.target.value)}
              error={invalid}
            />
          )}
        </Field>

        <Field
          label="Number of deaths"
          error={errors.quantity}
          required
          help={selected ? `${selected.available} bird(s) currently in this batch.` : undefined}
        >
          {({ id, invalid }) => (
            <Input
              id={id}
              type="number"
              min="1"
              step="1"
              value={form.quantity}
              onChange={(event) => update('quantity', event.target.value)}
              error={invalid}
            />
          )}
        </Field>

        <Field label="Suspected cause" error={errors.cause}>
          {({ id }) => (
            <>
              <Input
                id={id}
                list="mortality-causes"
                value={form.cause}
                onChange={(event) => update('cause', event.target.value)}
                placeholder="Respiratory infection"
              />
              <datalist id="mortality-causes">
                {CAUSES.map((cause) => (
                  <option key={cause} value={cause} />
                ))}
              </datalist>
            </>
          )}
        </Field>

        <Field label="Notes" span2>
          {({ id }) => (
            <TextArea
              id={id}
              value={form.notes}
              onChange={(event) => update('notes', event.target.value)}
              placeholder="What was observed?"
            />
          )}
        </Field>
      </form>
    </Modal>
  )
}
