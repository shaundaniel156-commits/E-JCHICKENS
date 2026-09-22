import { useEffect, useState } from 'react'
import { Pencil, Plus, ShoppingCart, Trash2, Users } from 'lucide-react'

import { salesApi } from '../api/endpoints'
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
import { useSettings } from '../contexts/SettingsContext'
import { useToast } from '../contexts/ToastContext'
import { useListQuery } from '../hooks/useListQuery'
import { useBatchOptions, useCustomerOptions } from '../hooks/useOptions'
import { formatDate, formatMoney, formatNumber, titleCase, toNumber, todayISO } from '../utils/format'

const PAYMENT_STATUSES = [
  { value: 'PAID', label: 'Paid in full' },
  { value: 'PARTIAL', label: 'Part payment' },
  { value: 'UNPAID', label: 'Not yet paid' },
]

const PAYMENT_METHODS = [
  { value: 'CASH', label: 'Cash' },
  { value: 'MOBILE_MONEY', label: 'Mobile money' },
  { value: 'BANK_TRANSFER', label: 'Bank transfer' },
  { value: 'CHEQUE', label: 'Cheque' },
  { value: 'CREDIT', label: 'Credit' },
  { value: 'OTHER', label: 'Other' },
]

export default function Sales() {
  const { currency } = useSettings()
  const toast = useToast()
  const { options: batchOptions, reload: reloadBatches } = useBatchOptions()
  const { options: customerOptions, reload: reloadCustomers } = useCustomerOptions()

  const [tab, setTab] = useState('sales')
  const [period, setPeriod] = useState({ preset: 'all_time', start_date: '', end_date: '' })
  const [formOpen, setFormOpen] = useState(false)
  const [customerOpen, setCustomerOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [deleting, setDeleting] = useState(null)

  const sales = useListQuery(salesApi.list, { pageSize: 10, sort: 'sale_date', order: 'desc' })
  const customers = useListQuery(salesApi.customers, { pageSize: 10 })

  useEffect(() => {
    sales.setFilters(periodParams(period))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period])

  const totals = sales.items.reduce(
    (accumulator, row) => ({
      birds: accumulator.birds + row.quantity,
      revenue: accumulator.revenue + toNumber(row.total_amount),
      collected: accumulator.collected + toNumber(row.amount_paid),
      due: accumulator.due + toNumber(row.balance_due),
    }),
    { birds: 0, revenue: 0, collected: 0, due: 0 },
  )

  const salesColumns = [
    { key: 'reference', header: 'Reference', sortable: true, render: (row) => <strong>{row.reference}</strong> },
    { key: 'sale_date', header: 'Date', sortable: true, render: (row) => formatDate(row.sale_date) },
    { key: 'batch_code', header: 'Batch', render: (row) => row.batch_code || '—' },
    { key: 'customer_name', header: 'Customer', className: 'wrap', render: (row) => row.customer_name || 'Walk-in' },
    { key: 'quantity', header: 'Birds', align: 'right', sortable: true, render: (row) => formatNumber(row.quantity) },
    { key: 'unit_price', header: 'Price / bird', align: 'right', render: (row) => formatMoney(row.unit_price, currency) },
    {
      key: 'total_amount',
      header: 'Total',
      align: 'right',
      sortable: true,
      render: (row) => <strong>{formatMoney(row.total_amount, currency)}</strong>,
    },
    { key: 'amount_paid', header: 'Paid', align: 'right', render: (row) => formatMoney(row.amount_paid, currency) },
    {
      key: 'balance_due',
      header: 'Balance',
      align: 'right',
      render: (row) =>
        toNumber(row.balance_due) > 0 ? (
          <span style={{ color: 'var(--critical)' }}>{formatMoney(row.balance_due, currency)}</span>
        ) : (
          '—'
        ),
    },
    {
      key: 'payment_status',
      header: 'Payment',
      render: (row) => <Badge status={row.payment_status}>{titleCase(row.payment_status)}</Badge>,
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
            aria-label="Edit sale"
            title="Edit sale"
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
            aria-label="Reverse sale"
            title="Reverse sale"
            onClick={() => setDeleting(row)}
          >
            <Trash2 size={15} />
          </button>
        </div>
      ),
    },
  ]

  const customerColumns = [
    { key: 'name', header: 'Customer', render: (row) => <strong>{row.name}</strong> },
    { key: 'phone', header: 'Phone', render: (row) => row.phone || '—' },
    { key: 'email', header: 'Email', render: (row) => row.email || '—' },
    { key: 'address', header: 'Address', className: 'wrap', render: (row) => row.address || '—' },
    { key: 'birds_bought', header: 'Birds bought', align: 'right', render: (row) => formatNumber(row.birds_bought) },
    {
      key: 'total_purchases',
      header: 'Total spent',
      align: 'right',
      render: (row) => <strong>{formatMoney(row.total_purchases, currency)}</strong>,
    },
  ]

  const reverseSale = async () => {
    try {
      await salesApi.remove(deleting.id)
      toast.success('The sale was reversed and the birds returned to the batch.')
      setDeleting(null)
      sales.reload()
      reloadBatches()
      customers.reload()
    } catch (error) {
      toast.error(error.message)
      setDeleting(null)
    }
  }

  return (
    <>
      <PageHeader title="Sales" subtitle="Bird sales, revenue and who bought what.">
        <Button variant="secondary" icon={Users} onClick={() => setCustomerOpen(true)}>
          Add customer
        </Button>
        <Button
          icon={Plus}
          onClick={() => {
            setEditing(null)
            setFormOpen(true)
          }}
        >
          Record sale
        </Button>
      </PageHeader>

      <div className="grid cols-4" style={{ marginBottom: 14 }}>
        <StatCard label="Birds sold (this view)" value={formatNumber(totals.birds)} icon={ShoppingCart} tone="brand" />
        <StatCard label="Revenue" value={formatMoney(totals.revenue, currency)} tone="info" small />
        <StatCard label="Cash collected" value={formatMoney(totals.collected, currency)} tone="good" small />
        <StatCard
          label="Outstanding"
          value={formatMoney(totals.due, currency)}
          tone={totals.due > 0 ? 'warning' : ''}
          valueTone={totals.due > 0 ? 'negative' : ''}
          small
        />
      </div>

      <Card>
        <div className="tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'sales'}
            className={`tab ${tab === 'sales' ? 'active' : ''}`}
            onClick={() => setTab('sales')}
          >
            Sales ({sales.meta.total})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'customers'}
            className={`tab ${tab === 'customers' ? 'active' : ''}`}
            onClick={() => setTab('customers')}
          >
            Customers ({customers.meta.total})
          </button>
        </div>

        {tab === 'sales' ? (
          <>
            <div className="toolbar">
              <SearchBox value={sales.search} onChange={sales.onSearch} placeholder="Search reference or customer…" />
              <FilterSelect
                label="Batch"
                value={sales.filters.batch_id}
                onChange={(value) => sales.setFilter('batch_id', value)}
                options={batchOptions}
                placeholder="All batches"
              />
              <FilterSelect
                label="Payment"
                value={sales.filters.payment_status}
                onChange={(value) => sales.setFilter('payment_status', value)}
                options={[...PAYMENT_STATUSES, { value: 'CANCELLED', label: 'Cancelled' }]}
                placeholder="All"
              />
              <PeriodFilter value={period} onChange={setPeriod} />
            </div>

            <DataTable
              columns={salesColumns}
              rows={sales.items}
              loading={sales.loading}
              error={sales.error}
              onRetry={sales.reload}
              sortBy={sales.sortBy}
              sortOrder={sales.sortOrder}
              onSort={sales.toggleSort}
              meta={sales.meta}
              page={sales.page}
              onPage={sales.setPage}
              pageSize={sales.pageSize}
              onPageSize={sales.setPageSize}
              caption="Sales"
              empty={
                <EmptyState
                  icon={ShoppingCart}
                  title="No sales recorded yet"
                  message="Record a sale and the birds leave the batch, revenue rises and the profit figures update by themselves."
                  action={
                    <Button
                      icon={Plus}
                      onClick={() => {
                        setEditing(null)
                        setFormOpen(true)
                      }}
                    >
                      Record sale
                    </Button>
                  }
                />
              }
            />
          </>
        ) : (
          <>
            <div className="toolbar">
              <SearchBox value={customers.search} onChange={customers.onSearch} placeholder="Search customers…" />
            </div>
            <DataTable
              columns={customerColumns}
              rows={customers.items}
              loading={customers.loading}
              error={customers.error}
              onRetry={customers.reload}
              meta={customers.meta}
              page={customers.page}
              onPage={customers.setPage}
              pageSize={customers.pageSize}
              onPageSize={customers.setPageSize}
              caption="Customers"
              empty={
                <EmptyState
                  icon={Users}
                  title="No customers yet"
                  message="Customers are created automatically when you record a sale, or you can add them here."
                  action={
                    <Button icon={Plus} onClick={() => setCustomerOpen(true)}>
                      Add customer
                    </Button>
                  }
                />
              }
            />
          </>
        )}
      </Card>

      <SaleForm
        open={formOpen}
        sale={editing}
        batchOptions={batchOptions}
        customerOptions={customerOptions}
        currency={currency}
        onClose={() => setFormOpen(false)}
        onSaved={() => {
          setFormOpen(false)
          sales.reload()
          customers.reload()
          reloadBatches()
          reloadCustomers()
        }}
      />

      <CustomerForm
        open={customerOpen}
        onClose={() => setCustomerOpen(false)}
        onSaved={() => {
          setCustomerOpen(false)
          customers.reload()
          reloadCustomers()
        }}
      />

      <ConfirmDialog
        open={Boolean(deleting)}
        title={`Reverse sale ${deleting?.reference}?`}
        message={`${deleting?.quantity} bird(s) will return to batch ${deleting?.batch_code} and the revenue will be removed from your figures. The sale stays in the audit trail.`}
        confirmLabel="Reverse sale"
        onConfirm={reverseSale}
        onClose={() => setDeleting(null)}
      />
    </>
  )
}

function SaleForm({ open, sale, batchOptions, customerOptions, currency, onClose, onSaved }) {
  const toast = useToast()
  const blank = {
    sale_date: todayISO(),
    batch_id: '',
    customer_id: '',
    customer_name: '',
    quantity: '',
    unit_price: '',
    payment_status: 'PAID',
    amount_paid: '',
    payment_method: 'CASH',
    notes: '',
  }
  const [form, setForm] = useState(blank)
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    setErrors({})
    setForm(
      sale
        ? {
            sale_date: sale.sale_date,
            batch_id: String(sale.batch_id),
            customer_id: sale.customer_id ? String(sale.customer_id) : '',
            customer_name: '',
            quantity: String(sale.quantity),
            unit_price: sale.unit_price,
            payment_status: sale.payment_status === 'CANCELLED' ? 'UNPAID' : sale.payment_status,
            amount_paid: sale.amount_paid,
            payment_method: sale.payment_method,
            notes: sale.notes || '',
          }
        : blank,
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, sale])

  const selectedBatch = batchOptions.find((option) => option.value === form.batch_id)
  const total = toNumber(form.quantity) * toNumber(form.unit_price)

  const update = (name, value) => {
    setForm((current) => {
      const next = { ...current, [name]: value }
      // Keep the amount paid consistent with the chosen payment status.
      if (name === 'payment_status') {
        if (value === 'PAID') next.amount_paid = ''
        if (value === 'UNPAID') next.amount_paid = '0'
      }
      return next
    })
    setErrors((current) => ({ ...current, [name]: undefined }))
  }

  const submit = async (event) => {
    event.preventDefault()
    const next = {}
    if (!sale && !form.batch_id) next.batch_id = 'Choose the batch the birds come from.'
    const quantity = Number(form.quantity)
    if (!Number.isInteger(quantity) || quantity <= 0) next.quantity = 'Enter a whole number greater than zero.'
    else if (selectedBatch && !sale && quantity > selectedBatch.available) {
      next.quantity = `That batch only has ${selectedBatch.available} bird(s) available.`
    }
    if (toNumber(form.unit_price) < 0) next.unit_price = 'Price cannot be negative.'
    if (!form.sale_date) next.sale_date = 'Choose the sale date.'
    else if (form.sale_date > todayISO()) next.sale_date = 'The date cannot be in the future.'
    if (form.payment_status === 'PARTIAL') {
      const paid = toNumber(form.amount_paid)
      if (paid <= 0) next.amount_paid = 'Enter how much was paid.'
      else if (paid > total) next.amount_paid = 'The amount paid cannot exceed the sale total.'
    }
    setErrors(next)
    if (Object.keys(next).length) return

    setSaving(true)
    try {
      const payload = {
        sale_date: form.sale_date,
        quantity,
        unit_price: String(form.unit_price || 0),
        payment_status: form.payment_status,
        payment_method: form.payment_method,
        notes: form.notes.trim() || null,
      }
      if (form.payment_status === 'PARTIAL') payload.amount_paid = String(form.amount_paid)
      if (form.customer_id) payload.customer_id = Number(form.customer_id)

      if (sale) {
        await salesApi.update(sale.id, payload)
        toast.success(`Sale ${sale.reference} was updated.`)
      } else {
        if (!form.customer_id && form.customer_name.trim()) {
          payload.customer_name = form.customer_name.trim()
        }
        const created = await salesApi.create({ ...payload, batch_id: Number(form.batch_id) })
        toast.success(`Sale ${created.reference} recorded — ${quantity} bird(s) left the batch.`)
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
      title={sale ? `Edit sale ${sale.reference}` : 'Record a sale'}
      hint="Saving reduces the batch, raises revenue and updates every financial figure."
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={submit} loading={saving}>
            {sale ? 'Save changes' : 'Record sale'}
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
              disabled={Boolean(sale)}
              error={invalid}
            />
          )}
        </Field>

        <Field label="Sale date" error={errors.sale_date} required>
          {({ id, invalid }) => (
            <Input
              id={id}
              type="date"
              max={todayISO()}
              value={form.sale_date}
              onChange={(event) => update('sale_date', event.target.value)}
              error={invalid}
            />
          )}
        </Field>

        <Field
          label="Number of birds"
          error={errors.quantity}
          required
          help={selectedBatch ? `${selectedBatch.available} bird(s) available.` : undefined}
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

        <Field
          label="Price per bird"
          error={errors.unit_price}
          required
          help={total > 0 ? `Sale total: ${formatMoney(total, currency)}` : undefined}
        >
          {({ id, invalid }) => (
            <Input
              id={id}
              type="number"
              min="0"
              step="1"
              prefix={currency}
              value={form.unit_price}
              onChange={(event) => update('unit_price', event.target.value)}
              placeholder="26000"
              error={invalid}
            />
          )}
        </Field>

        <Field label="Customer" error={errors.customer_id}>
          {({ id }) => (
            <Select
              id={id}
              value={form.customer_id}
              onChange={(event) => update('customer_id', event.target.value)}
              options={customerOptions}
              placeholder={sale ? 'Walk-in customer' : 'Existing customer…'}
            />
          )}
        </Field>

        {!sale && !form.customer_id && (
          <Field label="…or a new customer name" help="A customer record is created automatically.">
            {({ id }) => (
              <Input
                id={id}
                value={form.customer_name}
                onChange={(event) => update('customer_name', event.target.value)}
                placeholder="Nakawa Market Traders"
              />
            )}
          </Field>
        )}

        <Field label="Payment status" error={errors.payment_status} required>
          {({ id }) => (
            <Select
              id={id}
              value={form.payment_status}
              onChange={(event) => update('payment_status', event.target.value)}
              options={PAYMENT_STATUSES}
            />
          )}
        </Field>

        {form.payment_status === 'PARTIAL' && (
          <Field label="Amount paid so far" error={errors.amount_paid} required>
            {({ id, invalid }) => (
              <Input
                id={id}
                type="number"
                min="0"
                step="1"
                prefix={currency}
                value={form.amount_paid}
                onChange={(event) => update('amount_paid', event.target.value)}
                error={invalid}
              />
            )}
          </Field>
        )}

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

        <Field label="Notes" span2>
          {({ id }) => (
            <TextArea id={id} value={form.notes} onChange={(event) => update('notes', event.target.value)} />
          )}
        </Field>
      </form>
    </Modal>
  )
}

function CustomerForm({ open, onClose, onSaved }) {
  const toast = useToast()
  const blank = { name: '', phone: '', email: '', address: '', notes: '' }
  const [form, setForm] = useState(blank)
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (open) {
      setForm(blank)
      setErrors({})
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  const submit = async () => {
    if (form.name.trim().length < 2) {
      setErrors({ name: 'Enter the customer name.' })
      return
    }
    setSaving(true)
    try {
      await salesApi.createCustomer({
        name: form.name.trim(),
        phone: form.phone.trim() || null,
        email: form.email.trim() || null,
        address: form.address.trim() || null,
        notes: form.notes.trim() || null,
      })
      toast.success('The customer was added.')
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
      title="Add a customer"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={submit} loading={saving}>
            Add customer
          </Button>
        </>
      }
    >
      <div className="form-grid">
        <Field label="Name" error={errors.name} required span2>
          {({ id, invalid }) => (
            <Input
              id={id}
              value={form.name}
              onChange={(event) => setForm((c) => ({ ...c, name: event.target.value }))}
              error={invalid}
            />
          )}
        </Field>
        <Field label="Phone" error={errors.phone}>
          {({ id }) => (
            <Input
              id={id}
              value={form.phone}
              onChange={(event) => setForm((c) => ({ ...c, phone: event.target.value }))}
              placeholder="+256 700 000 000"
            />
          )}
        </Field>
        <Field label="Email" error={errors.email}>
          {({ id }) => (
            <Input
              id={id}
              type="email"
              value={form.email}
              onChange={(event) => setForm((c) => ({ ...c, email: event.target.value }))}
            />
          )}
        </Field>
        <Field label="Address" span2>
          {({ id }) => (
            <Input
              id={id}
              value={form.address}
              onChange={(event) => setForm((c) => ({ ...c, address: event.target.value }))}
            />
          )}
        </Field>
        <Field label="Notes" span2>
          {({ id }) => (
            <TextArea
              id={id}
              value={form.notes}
              onChange={(event) => setForm((c) => ({ ...c, notes: event.target.value }))}
            />
          )}
        </Field>
      </div>
    </Modal>
  )
}
