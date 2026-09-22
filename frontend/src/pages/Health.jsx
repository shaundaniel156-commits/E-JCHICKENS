import { useEffect, useState } from 'react'
import { HeartPulse, Pencil, Plus, Trash2 } from 'lucide-react'

import { healthApi } from '../api/endpoints'
import DataTable from '../components/DataTable'
import { FilterSelect, PeriodFilter, SearchBox, periodParams } from '../components/Filters'
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
import { useApi } from '../hooks/useApi'
import { useListQuery } from '../hooks/useListQuery'
import { useBatchOptions } from '../hooks/useOptions'
import { formatDate, formatMoney, formatNumber, titleCase, todayISO } from '../utils/format'

const STATUSES = [
  { value: 'SICK', label: 'Sick' },
  { value: 'UNDER_TREATMENT', label: 'Under treatment' },
  { value: 'CRITICAL', label: 'Critical' },
  { value: 'RECOVERED', label: 'Recovered' },
]

const EMPTY = {
  batch_id: '',
  record_date: todayISO(),
  sick_count: '',
  symptoms: '',
  diagnosis: '',
  treatment: '',
  medicine: '',
  dosage: '',
  treatment_cost: '',
  veterinarian: '',
  status: 'SICK',
  notes: '',
}

export default function Health() {
  const { isManager } = useAuth()
  const { currency } = useSettings()
  const toast = useToast()
  const { options: batchOptions, reload: reloadBatches } = useBatchOptions()

  const [period, setPeriod] = useState({ preset: 'all_time', start_date: '', end_date: '' })
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [deleting, setDeleting] = useState(null)

  const query = useListQuery(healthApi.list, { pageSize: 10, sort: 'record_date', order: 'desc' })
  const summary = useApi(() => healthApi.summary(), [])

  useEffect(() => {
    query.setFilters(periodParams(period))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period])

  const counts = summary.data ?? {}
  const openCases = (counts.SICK || 0) + (counts.UNDER_TREATMENT || 0) + (counts.CRITICAL || 0)

  const columns = [
    { key: 'record_date', header: 'Date', sortable: true, render: (row) => formatDate(row.record_date) },
    { key: 'batch_code', header: 'Batch', render: (row) => row.batch_code || '—' },
    {
      key: 'sick_count',
      header: 'Sick birds',
      align: 'right',
      sortable: true,
      render: (row) => <strong>{formatNumber(row.sick_count)}</strong>,
    },
    { key: 'diagnosis', header: 'Diagnosis', className: 'wrap', render: (row) => row.diagnosis || '—' },
    { key: 'medicine', header: 'Medicine', className: 'wrap', render: (row) => row.medicine || '—' },
    {
      key: 'treatment_cost',
      header: 'Treatment cost',
      align: 'right',
      sortable: true,
      render: (row) => formatMoney(row.treatment_cost, currency),
    },
    { key: 'veterinarian', header: 'Attended by', render: (row) => row.veterinarian || '—' },
    {
      key: 'status',
      header: 'Status',
      render: (row) => <Badge status={row.status}>{titleCase(row.status)}</Badge>,
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (row) => (
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
          {isManager && (
            <button
              type="button"
              className="icon-btn"
              aria-label="Remove record"
              title="Remove record"
              onClick={() => setDeleting(row)}
            >
              <Trash2 size={15} />
            </button>
          )}
        </div>
      ),
    },
  ]

  const remove = async () => {
    try {
      await healthApi.remove(deleting.id)
      toast.success('The health record was removed, along with its treatment expense.')
      setDeleting(null)
      query.reload()
      summary.reload()
      reloadBatches()
    } catch (error) {
      toast.error(error.message)
      setDeleting(null)
    }
  }

  return (
    <>
      <PageHeader
        title="Health"
        subtitle="Sickness, treatment and recovery. Treatment costs become Medicine expenses automatically."
      >
        <Button
          icon={Plus}
          onClick={() => {
            setEditing(null)
            setFormOpen(true)
          }}
        >
          Record sick birds
        </Button>
      </PageHeader>

      <div className="grid cols-4" style={{ marginBottom: 14 }}>
        <StatCard
          label="Birds needing attention"
          value={formatNumber(openCases)}
          meta="Sick, critical or under treatment"
          icon={HeartPulse}
          tone={openCases > 0 ? 'warning' : 'good'}
        />
        <StatCard label="Sick" value={formatNumber(counts.SICK || 0)} tone="warning" small />
        <StatCard label="Under treatment" value={formatNumber(counts.UNDER_TREATMENT || 0)} tone="info" small />
        <StatCard label="Recovered" value={formatNumber(counts.RECOVERED || 0)} tone="good" small />
      </div>

      <Card>
        <div className="toolbar">
          <SearchBox
            value={query.search}
            onChange={query.onSearch}
            placeholder="Search diagnosis, symptoms, medicine or vet…"
          />
          <FilterSelect
            label="Batch"
            value={query.filters.batch_id}
            onChange={(value) => query.setFilter('batch_id', value)}
            options={batchOptions}
            placeholder="All batches"
          />
          <FilterSelect
            label="Status"
            value={query.filters.status}
            onChange={(value) => query.setFilter('status', value)}
            options={STATUSES}
            placeholder="All statuses"
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
          caption="Health records"
          empty={
            <EmptyState
              icon={HeartPulse}
              title="No health records yet"
              message="Record sick birds here so treatment, cost and recovery are all tracked in one place."
              action={
                <Button
                  icon={Plus}
                  onClick={() => {
                    setEditing(null)
                    setFormOpen(true)
                  }}
                >
                  Record sick birds
                </Button>
              }
            />
          }
        />
      </Card>

      <HealthForm
        open={formOpen}
        record={editing}
        batchOptions={batchOptions}
        currency={currency}
        onClose={() => setFormOpen(false)}
        onSaved={() => {
          setFormOpen(false)
          query.reload()
          summary.reload()
          reloadBatches()
        }}
      />

      <ConfirmDialog
        open={Boolean(deleting)}
        title="Remove this health record?"
        message="The record and any treatment expense it created will be reversed. The entry stays in the audit trail."
        confirmLabel="Remove record"
        onConfirm={remove}
        onClose={() => setDeleting(null)}
      />
    </>
  )
}

function HealthForm({ open, record, batchOptions, currency, onClose, onSaved }) {
  const toast = useToast()
  const [form, setForm] = useState(EMPTY)
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
            sick_count: String(record.sick_count),
            symptoms: record.symptoms || '',
            diagnosis: record.diagnosis || '',
            treatment: record.treatment || '',
            medicine: record.medicine || '',
            dosage: record.dosage || '',
            treatment_cost: record.treatment_cost ?? '',
            veterinarian: record.veterinarian || '',
            status: record.status,
            notes: record.notes || '',
          }
        : EMPTY,
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
    if (!record && !form.batch_id) next.batch_id = 'Choose the affected batch.'
    const count = Number(form.sick_count)
    if (!Number.isInteger(count) || count <= 0) next.sick_count = 'Enter a whole number greater than zero.'
    if (!form.record_date) next.record_date = 'Choose the date.'
    else if (form.record_date > todayISO()) next.record_date = 'The date cannot be in the future.'
    if (form.treatment_cost !== '' && Number(form.treatment_cost) < 0) {
      next.treatment_cost = 'Cost cannot be negative.'
    }
    setErrors(next)
    if (Object.keys(next).length) return

    setSaving(true)
    try {
      const payload = {
        record_date: form.record_date,
        sick_count: count,
        symptoms: form.symptoms.trim() || null,
        diagnosis: form.diagnosis.trim() || null,
        treatment: form.treatment.trim() || null,
        medicine: form.medicine.trim() || null,
        dosage: form.dosage.trim() || null,
        treatment_cost: form.treatment_cost === '' ? '0' : String(form.treatment_cost),
        veterinarian: form.veterinarian.trim() || null,
        status: form.status,
        notes: form.notes.trim() || null,
      }
      if (record) await healthApi.update(record.id, payload)
      else await healthApi.create({ ...payload, batch_id: Number(form.batch_id) })
      toast.success(record ? 'The health record was updated.' : 'The health record was saved.')
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
      title={record ? 'Edit health record' : 'Record sick birds'}
      hint="Birds stop counting as sick once the record is marked Recovered."
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={submit} loading={saving}>
            {record ? 'Save changes' : 'Save record'}
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
          label="Number of sick birds"
          error={errors.sick_count}
          required
          help={selected ? `${selected.available} bird(s) in this batch.` : undefined}
        >
          {({ id, invalid }) => (
            <Input
              id={id}
              type="number"
              min="1"
              step="1"
              value={form.sick_count}
              onChange={(event) => update('sick_count', event.target.value)}
              error={invalid}
            />
          )}
        </Field>

        <Field label="Status" error={errors.status} required>
          {({ id }) => (
            <Select
              id={id}
              value={form.status}
              onChange={(event) => update('status', event.target.value)}
              options={STATUSES}
            />
          )}
        </Field>

        <Field label="Symptoms" span2>
          {({ id }) => (
            <TextArea
              id={id}
              value={form.symptoms}
              onChange={(event) => update('symptoms', event.target.value)}
              placeholder="Coughing, nasal discharge, ruffled feathers…"
            />
          )}
        </Field>

        <Field label="Diagnosis" error={errors.diagnosis}>
          {({ id }) => (
            <Input
              id={id}
              value={form.diagnosis}
              onChange={(event) => update('diagnosis', event.target.value)}
              placeholder="Chronic respiratory disease"
            />
          )}
        </Field>

        <Field label="Attended by" error={errors.veterinarian}>
          {({ id }) => (
            <Input
              id={id}
              value={form.veterinarian}
              onChange={(event) => update('veterinarian', event.target.value)}
              placeholder="Dr. Okello"
            />
          )}
        </Field>

        <Field label="Medicine used" error={errors.medicine}>
          {({ id }) => (
            <Input
              id={id}
              value={form.medicine}
              onChange={(event) => update('medicine', event.target.value)}
              placeholder="Doxycycline 20%"
            />
          )}
        </Field>

        <Field label="Dosage" error={errors.dosage}>
          {({ id }) => (
            <Input
              id={id}
              value={form.dosage}
              onChange={(event) => update('dosage', event.target.value)}
              placeholder="1 g per 2 litres"
            />
          )}
        </Field>

        <Field
          label="Treatment cost"
          error={errors.treatment_cost}
          help="Recorded automatically as a Medicine expense."
        >
          {({ id, invalid }) => (
            <Input
              id={id}
              type="number"
              min="0"
              step="1"
              prefix={currency}
              value={form.treatment_cost}
              onChange={(event) => update('treatment_cost', event.target.value)}
              placeholder="40000"
              error={invalid}
            />
          )}
        </Field>

        <Field label="Treatment given" span2>
          {({ id }) => (
            <TextArea
              id={id}
              value={form.treatment}
              onChange={(event) => update('treatment', event.target.value)}
              placeholder="Antibiotic in drinking water for 5 days…"
            />
          )}
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
