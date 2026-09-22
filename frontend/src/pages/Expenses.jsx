import { useEffect, useState } from 'react'
import { Lock, Pencil, Plus, Receipt, Trash2 } from 'lucide-react'

import { expensesApi } from '../api/endpoints'
import { ExpenseBreakdownChart } from '../components/charts'
import DataTable from '../components/DataTable'
import { FilterSelect, PeriodFilter, SearchBox, periodParams } from '../components/Filters'
import StatCard from '../components/StatCard'
import {
  Badge,
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
import { useSettings } from '../contexts/SettingsContext'
import { useToast } from '../contexts/ToastContext'
import { useApi } from '../hooks/useApi'
import { useListQuery } from '../hooks/useListQuery'
import { useCategoryOptions } from '../hooks/useOptions'
import { formatDate, formatMoney, titleCase, toNumber, todayISO } from '../utils/format'

const PAYMENT_METHODS = [
  { value: 'CASH', label: 'Cash' },
  { value: 'MOBILE_MONEY', label: 'Mobile money' },
  { value: 'BANK_TRANSFER', label: 'Bank transfer' },
  { value: 'CHEQUE', label: 'Cheque' },
  { value: 'CREDIT', label: 'Credit' },
  { value: 'OTHER', label: 'Other' },
]

export default function Expenses() {
  const { currency } = useSettings()
  const toast = useToast()
  const { options: categoryOptions, reload: reloadCategories } = useCategoryOptions()

  const [period, setPeriod] = useState({ preset: 'all_time', start_date: '', end_date: '' })
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [deleting, setDeleting] = useState(null)

  const query = useListQuery(expensesApi.list, { pageSize: 10, sort: 'expense_date', order: 'desc' })
  const breakdown = useApi(() => expensesApi.breakdown(periodParams(period)), [JSON.stringify(period)])

  useEffect(() => {
    query.setFilters(periodParams(period))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period])

  const rows = breakdown.data ?? []
  const total = rows.reduce((sum, row) => sum + toNumber(row.amount), 0)
  const biggest = rows[0]

  const columns = [
    { key: 'expense_date', header: 'Date', sortable: true, render: (row) => formatDate(row.expense_date) },
    { key: 'category_name', header: 'Category', render: (row) => <Badge>{row.category_name}</Badge> },
    {
      key: 'description',
      header: 'Description',
      className: 'wrap',
      sortable: true,
      render: (row) => (
        <div>
          <div>{row.description}</div>
          {row.is_system_generated && (
            <span style={{ fontSize: '0.72rem', color: 'var(--ink-muted)', display: 'inline-flex', gap: 4, alignItems: 'center' }}>
              <Lock size={11} /> Created automatically from the {titleCase(row.source_type)} record
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'amount',
      header: 'Amount',
      align: 'right',
      sortable: true,
      render: (row) => <strong>{formatMoney(row.amount, currency)}</strong>,
    },
    { key: 'vendor', header: 'Supplier', render: (row) => row.vendor || '—' },
    { key: 'payment_method', header: 'Paid by', render: (row) => titleCase(row.payment_method) },
    { key: 'reference_number', header: 'Reference', render: (row) => row.reference_number || '—' },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (row) =>
        row.is_system_generated ? (
          <span title="Edit the record this came from instead" style={{ color: 'var(--ink-muted)' }}>
            <Lock size={15} />
          </span>
        ) : (
          <div className="row-actions">
            <button
              type="button"
              className="icon-btn"
              aria-label="Edit expense"
              title="Edit expense"
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
              aria-label="Reverse expense"
              title="Reverse expense"
              onClick={() => setDeleting(row)}
            >
              <Trash2 size={15} />
            </button>
          </div>
        ),
    },
  ]

  const reverse = async () => {
    try {
      await expensesApi.remove(deleting.id)
      toast.success('The expense was reversed.')
      setDeleting(null)
      query.reload()
      breakdown.reload()
    } catch (error) {
      toast.error(error.message)
      setDeleting(null)
    }
  }

  return (
    <>
      <PageHeader
        title="Expenses"
        subtitle="Every cost on the farm, including the entries created automatically by other modules."
      >
        <Button
          icon={Plus}
          onClick={() => {
            setEditing(null)
            setFormOpen(true)
          }}
        >
          Record expense
        </Button>
      </PageHeader>

      <div className="grid cols-3" style={{ marginBottom: 14 }}>
        <StatCard
          label="Total for this period"
          value={formatMoney(total, currency)}
          meta={`${query.meta.total} entr${query.meta.total === 1 ? 'y' : 'ies'}`}
          icon={Receipt}
          tone="gold"
        />
        <StatCard
          label="Biggest category"
          value={biggest ? biggest.category : '—'}
          meta={biggest ? `${formatMoney(biggest.amount, currency)} · ${biggest.percentage.toFixed(1)}% of spending` : 'No expenses yet'}
          small
        />
        <StatCard
          label="Categories in use"
          value={String(rows.length)}
          meta={`${categoryOptions.length} categories available`}
          small
        />
      </div>

      <Card style={{ marginBottom: 14 }}>
        <CardHead title="Where the money goes" hint="Expenses by category for the selected period" />
        <div className="card-body tight">
          <ExpenseBreakdownChart data={rows} currency={currency} />
        </div>
      </Card>

      <Card>
        <div className="toolbar">
          <SearchBox
            value={query.search}
            onChange={query.onSearch}
            placeholder="Search description, supplier or reference…"
          />
          <FilterSelect
            label="Category"
            value={query.filters.category_id}
            onChange={(value) => query.setFilter('category_id', value)}
            options={categoryOptions}
            placeholder="All categories"
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
          caption="Expenses"
          empty={
            <EmptyState
              icon={Receipt}
              title="No expenses recorded"
              message="Record what the farm spends so your budget and profit figures stay honest."
              action={
                <Button
                  icon={Plus}
                  onClick={() => {
                    setEditing(null)
                    setFormOpen(true)
                  }}
                >
                  Record first expense
                </Button>
              }
            />
          }
        />
      </Card>

      <ExpenseForm
        open={formOpen}
        expense={editing}
        categoryOptions={categoryOptions}
        currency={currency}
        onClose={() => setFormOpen(false)}
        onSaved={() => {
          setFormOpen(false)
          query.reload()
          breakdown.reload()
          reloadCategories()
        }}
      />

      <ConfirmDialog
        open={Boolean(deleting)}
        title="Reverse this expense?"
        message={`“${deleting?.description}” (${formatMoney(deleting?.amount, currency)}) will be removed from your totals. The entry stays in the audit trail.`}
        confirmLabel="Reverse expense"
        onConfirm={reverse}
        onClose={() => setDeleting(null)}
      />
    </>
  )
}

function ExpenseForm({ open, expense, categoryOptions, currency, onClose, onSaved }) {
  const toast = useToast()
  const blank = {
    expense_date: todayISO(),
    category_id: '',
    description: '',
    amount: '',
    vendor: '',
    payment_method: 'CASH',
    reference_number: '',
    receipt_url: '',
    notes: '',
  }
  const [form, setForm] = useState(blank)
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    setErrors({})
    setForm(
      expense
        ? {
            expense_date: expense.expense_date,
            category_id: String(expense.category_id),
            description: expense.description,
            amount: expense.amount,
            vendor: expense.vendor || '',
            payment_method: expense.payment_method,
            reference_number: expense.reference_number || '',
            receipt_url: expense.receipt_url || '',
            notes: expense.notes || '',
          }
        : blank,
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, expense])

  const update = (name, value) => {
    setForm((current) => ({ ...current, [name]: value }))
    setErrors((current) => ({ ...current, [name]: undefined }))
  }

  const submit = async (event) => {
    event.preventDefault()
    const next = {}
    if (!form.category_id) next.category_id = 'Choose a category.'
    if (form.description.trim().length < 2) next.description = 'Describe what the money was spent on.'
    if (toNumber(form.amount) <= 0) next.amount = 'Enter an amount greater than zero.'
    if (!form.expense_date) next.expense_date = 'Choose the date.'
    else if (form.expense_date > todayISO()) next.expense_date = 'The date cannot be in the future.'
    setErrors(next)
    if (Object.keys(next).length) return

    setSaving(true)
    try {
      const payload = {
        expense_date: form.expense_date,
        category_id: Number(form.category_id),
        description: form.description.trim(),
        amount: String(form.amount),
        vendor: form.vendor.trim() || null,
        payment_method: form.payment_method,
        reference_number: form.reference_number.trim() || null,
        receipt_url: form.receipt_url.trim() || null,
        notes: form.notes.trim() || null,
      }
      if (expense) await expensesApi.update(expense.id, payload)
      else await expensesApi.create(payload)
      toast.success(expense ? 'The expense was updated.' : 'The expense was recorded.')
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
      title={expense ? 'Edit expense' : 'Record an expense'}
      hint="Expenses reduce your remaining budget and your profit immediately."
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={submit} loading={saving}>
            {expense ? 'Save changes' : 'Record expense'}
          </Button>
        </>
      }
    >
      <form className="form-grid" onSubmit={submit} noValidate>
        <Field label="Date" error={errors.expense_date} required>
          {({ id, invalid }) => (
            <Input
              id={id}
              type="date"
              max={todayISO()}
              value={form.expense_date}
              onChange={(event) => update('expense_date', event.target.value)}
              error={invalid}
            />
          )}
        </Field>

        <Field label="Category" error={errors.category_id} required>
          {({ id, invalid }) => (
            <Select
              id={id}
              value={form.category_id}
              onChange={(event) => update('category_id', event.target.value)}
              options={categoryOptions}
              placeholder="Choose a category…"
              error={invalid}
            />
          )}
        </Field>

        <Field label="Description" error={errors.description} required span2>
          {({ id, invalid }) => (
            <Input
              id={id}
              value={form.description}
              onChange={(event) => update('description', event.target.value)}
              placeholder="Casual labour — brooding week 2"
              error={invalid}
            />
          )}
        </Field>

        <Field label="Amount" error={errors.amount} required>
          {({ id, invalid }) => (
            <Input
              id={id}
              type="number"
              min="1"
              step="1"
              prefix={currency}
              value={form.amount}
              onChange={(event) => update('amount', event.target.value)}
              placeholder="450000"
              error={invalid}
            />
          )}
        </Field>

        <Field label="Payment method">
          {({ id }) => (
            <Select
              id={id}
              value={form.payment_method}
              onChange={(event) => update('payment_method', event.target.value)}
              options={PAYMENT_METHODS}
            />
          )}
        </Field>

        <Field label="Supplier / vendor">
          {({ id }) => (
            <Input id={id} value={form.vendor} onChange={(event) => update('vendor', event.target.value)} />
          )}
        </Field>

        <Field label="Reference number" help="Receipt or transaction number, if any.">
          {({ id }) => (
            <Input
              id={id}
              value={form.reference_number}
              onChange={(event) => update('reference_number', event.target.value)}
            />
          )}
        </Field>

        <Field label="Receipt link" help="A link to a scanned or photographed receipt." span2>
          {({ id }) => (
            <Input
              id={id}
              type="url"
              value={form.receipt_url}
              onChange={(event) => update('receipt_url', event.target.value)}
              placeholder="https://…"
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
