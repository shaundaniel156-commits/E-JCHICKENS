import { useEffect, useState } from 'react'
import { AlertTriangle, Package, Pencil, Plus, Trash2, Wheat } from 'lucide-react'

import { feedApi } from '../api/endpoints'
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
  SkeletonCards,
  TextArea,
} from '../components/ui'
import { useAuth } from '../contexts/AuthContext'
import { useSettings } from '../contexts/SettingsContext'
import { useToast } from '../contexts/ToastContext'
import { useApi } from '../hooks/useApi'
import { useListQuery } from '../hooks/useListQuery'
import { useBatchOptions, useFeedTypeOptions } from '../hooks/useOptions'
import { formatDate, formatMoney, formatQuantity, todayISO, toNumber } from '../utils/format'

export default function Feed() {
  const { isManager } = useAuth()
  const { currency } = useSettings()
  const toast = useToast()

  const stock = useApi(() => feedApi.stock(), [])
  const { options: feedTypeOptions, types, reload: reloadTypes } = useFeedTypeOptions()
  const { options: batchOptions } = useBatchOptions()

  const [tab, setTab] = useState('purchases')
  const [period, setPeriod] = useState({ preset: 'all_time', start_date: '', end_date: '' })
  const [purchaseOpen, setPurchaseOpen] = useState(false)
  const [consumptionOpen, setConsumptionOpen] = useState(false)
  const [typeOpen, setTypeOpen] = useState(false)
  const [editingPurchase, setEditingPurchase] = useState(null)
  const [editingConsumption, setEditingConsumption] = useState(null)
  const [deleting, setDeleting] = useState(null)

  const purchases = useListQuery(feedApi.purchases, { pageSize: 10, sort: 'purchase_date', order: 'desc' })
  const consumption = useListQuery(feedApi.consumption, {
    pageSize: 10,
    sort: 'consumption_date',
    order: 'desc',
  })

  useEffect(() => {
    purchases.setFilters(periodParams(period))
    consumption.setFilters(periodParams(period))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period])

  const refreshAll = () => {
    stock.reload()
    reloadTypes()
    purchases.reload()
    consumption.reload()
  }

  const summary = stock.data

  const purchaseColumns = [
    { key: 'purchase_date', header: 'Date', sortable: true, render: (row) => formatDate(row.purchase_date) },
    { key: 'feed_type_name', header: 'Feed type' },
    { key: 'brand', header: 'Brand', render: (row) => row.brand || '—' },
    {
      key: 'quantity_bags',
      header: 'Bags',
      align: 'right',
      sortable: true,
      render: (row) => formatQuantity(row.quantity_bags),
    },
    { key: 'bag_weight_kg', header: 'Bag weight', align: 'right', render: (row) => formatQuantity(row.bag_weight_kg, 'kg') },
    { key: 'quantity_kg', header: 'Total', align: 'right', render: (row) => formatQuantity(row.quantity_kg, 'kg') },
    { key: 'cost_per_bag', header: 'Cost / bag', align: 'right', render: (row) => formatMoney(row.cost_per_bag, currency) },
    {
      key: 'total_cost',
      header: 'Total cost',
      align: 'right',
      sortable: true,
      render: (row) => <strong>{formatMoney(row.total_cost, currency)}</strong>,
    },
    { key: 'supplier', header: 'Supplier', render: (row) => row.supplier || '—' },
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
              aria-label="Edit purchase"
              title="Edit purchase"
              onClick={() => {
                setEditingPurchase(row)
                setPurchaseOpen(true)
              }}
            >
              <Pencil size={15} />
            </button>
            <button
              type="button"
              className="icon-btn"
              aria-label="Reverse purchase"
              title="Reverse purchase"
              onClick={() => setDeleting({ kind: 'purchase', row })}
            >
              <Trash2 size={15} />
            </button>
          </div>
        ) : null,
    },
  ]

  const consumptionColumns = [
    { key: 'consumption_date', header: 'Date', sortable: true, render: (row) => formatDate(row.consumption_date) },
    { key: 'feed_type_name', header: 'Feed type' },
    { key: 'batch_code', header: 'Batch', render: (row) => row.batch_code || 'Whole farm' },
    { key: 'quantity_bags', header: 'Bags', align: 'right', render: (row) => formatQuantity(row.quantity_bags) },
    {
      key: 'quantity_kg',
      header: 'Kilograms',
      align: 'right',
      sortable: true,
      render: (row) => <strong>{formatQuantity(row.quantity_kg, 'kg')}</strong>,
    },
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
                setEditingConsumption(row)
                setConsumptionOpen(true)
              }}
            >
              <Pencil size={15} />
            </button>
            <button
              type="button"
              className="icon-btn"
              aria-label="Reverse record"
              title="Reverse record"
              onClick={() => setDeleting({ kind: 'consumption', row })}
            >
              <Trash2 size={15} />
            </button>
          </div>
        ) : null,
    },
  ]

  const confirmDelete = async () => {
    try {
      if (deleting.kind === 'purchase') await feedApi.removePurchase(deleting.row.id)
      else await feedApi.removeConsumption(deleting.row.id)
      toast.success('The record was reversed and the feed stock recalculated.')
      setDeleting(null)
      refreshAll()
    } catch (error) {
      toast.error(error.message)
      setDeleting(null)
    }
  }

  return (
    <>
      <PageHeader title="Feed" subtitle="Purchases, consumption and what is left in the store.">
        <Button
          variant="secondary"
          icon={Package}
          onClick={() => {
            setEditingConsumption(null)
            setConsumptionOpen(true)
          }}
        >
          Record consumption
        </Button>
        {isManager && (
          <Button
            icon={Plus}
            onClick={() => {
              setEditingPurchase(null)
              setPurchaseOpen(true)
            }}
          >
            Record purchase
          </Button>
        )}
      </PageHeader>

      {stock.loading && !summary ? (
        <SkeletonCards count={4} />
      ) : summary ? (
        <div className="grid cols-4" style={{ marginBottom: 14 }}>
          <StatCard
            label="Feed in stock"
            value={formatQuantity(summary.total_stock_bags, 'bags')}
            meta={formatQuantity(summary.total_stock_kg, 'kg')}
            icon={Wheat}
            tone={summary.low_stock_types > 0 ? 'warning' : 'gold'}
            footer={
              summary.low_stock_types > 0 ? (
                <Badge tone="warning" icon={AlertTriangle}>
                  {summary.low_stock_types} type(s) low
                </Badge>
              ) : null
            }
          />
          <StatCard
            label="Purchased"
            value={formatQuantity(summary.total_purchased_kg, 'kg')}
            meta="Total ever brought in"
            icon={Plus}
            tone="info"
          />
          <StatCard
            label="Consumed"
            value={formatQuantity(summary.total_consumed_kg, 'kg')}
            meta="Total fed to the birds"
            icon={Package}
          />
          <StatCard
            label="Feed expenditure"
            value={formatMoney(summary.total_feed_cost, currency)}
            meta="Recorded automatically as Feed expenses"
            small
          />
        </div>
      ) : null}

      <Card style={{ marginBottom: 14 }}>
        <CardHead title="Stock by feed type" hint="Purchased less consumed, per type">
          {isManager && (
            <Button variant="secondary" size="sm" icon={Plus} onClick={() => setTypeOpen(true)}>
              Add feed type
            </Button>
          )}
        </CardHead>
        <div className="card-body">
          {types.length === 0 ? (
            <EmptyState icon={Wheat} title="No feed types configured" message="Add a feed type to start recording purchases." />
          ) : (
            <div className="table-wrap">
              <table className="data">
                <caption className="visually-hidden">Feed stock by type</caption>
                <thead>
                  <tr>
                    <th scope="col">Feed type</th>
                    <th scope="col" className="num">Bag weight</th>
                    <th scope="col" className="num">Purchased</th>
                    <th scope="col" className="num">Consumed</th>
                    <th scope="col" className="num">In stock</th>
                    <th scope="col" className="num">Bags left</th>
                    <th scope="col">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {types.map((type) => (
                    <tr key={type.id}>
                      <td>
                        <div style={{ fontWeight: 600 }}>{type.name}</div>
                        {type.description && (
                          <div style={{ fontSize: '0.75rem', color: 'var(--ink-muted)' }}>{type.description}</div>
                        )}
                      </td>
                      <td className="num">{formatQuantity(type.default_bag_weight_kg, 'kg')}</td>
                      <td className="num">{formatQuantity(type.purchased_kg, 'kg')}</td>
                      <td className="num">{formatQuantity(type.consumed_kg, 'kg')}</td>
                      <td className="num">
                        <strong>{formatQuantity(type.stock_kg, 'kg')}</strong>
                      </td>
                      <td className="num">{formatQuantity(type.stock_bags)}</td>
                      <td>
                        {type.is_low_stock ? (
                          <Badge tone="warning" icon={AlertTriangle}>
                            Low stock
                          </Badge>
                        ) : (
                          <Badge tone="good">In stock</Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Card>

      <Card>
        <div className="tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'purchases'}
            className={`tab ${tab === 'purchases' ? 'active' : ''}`}
            onClick={() => setTab('purchases')}
          >
            Purchases ({purchases.meta.total})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'consumption'}
            className={`tab ${tab === 'consumption' ? 'active' : ''}`}
            onClick={() => setTab('consumption')}
          >
            Consumption ({consumption.meta.total})
          </button>
        </div>

        <div className="toolbar">
          {tab === 'purchases' && (
            <SearchBox
              value={purchases.search}
              onChange={purchases.onSearch}
              placeholder="Search brand, supplier or lot…"
            />
          )}
          <FilterSelect
            label="Feed type"
            value={tab === 'purchases' ? purchases.filters.feed_type_id : consumption.filters.feed_type_id}
            onChange={(value) =>
              tab === 'purchases'
                ? purchases.setFilter('feed_type_id', value)
                : consumption.setFilter('feed_type_id', value)
            }
            options={feedTypeOptions}
            placeholder="All types"
          />
          {tab === 'consumption' && (
            <FilterSelect
              label="Batch"
              value={consumption.filters.batch_id}
              onChange={(value) => consumption.setFilter('batch_id', value)}
              options={batchOptions}
              placeholder="All batches"
            />
          )}
          <PeriodFilter value={period} onChange={setPeriod} />
        </div>

        {tab === 'purchases' ? (
          <DataTable
            columns={purchaseColumns}
            rows={purchases.items}
            loading={purchases.loading}
            error={purchases.error}
            onRetry={purchases.reload}
            sortBy={purchases.sortBy}
            sortOrder={purchases.sortOrder}
            onSort={purchases.toggleSort}
            meta={purchases.meta}
            page={purchases.page}
            onPage={purchases.setPage}
            pageSize={purchases.pageSize}
            onPageSize={purchases.setPageSize}
            caption="Feed purchases"
            empty={
              <EmptyState
                icon={Wheat}
                title="No feed purchases recorded"
                message="Record a purchase to build up your feed stock. The cost is added to your expenses automatically."
                action={
                  isManager ? (
                    <Button
                      icon={Plus}
                      onClick={() => {
                        setEditingPurchase(null)
                        setPurchaseOpen(true)
                      }}
                    >
                      Record first purchase
                    </Button>
                  ) : null
                }
              />
            }
          />
        ) : (
          <DataTable
            columns={consumptionColumns}
            rows={consumption.items}
            loading={consumption.loading}
            error={consumption.error}
            onRetry={consumption.reload}
            sortBy={consumption.sortBy}
            sortOrder={consumption.sortOrder}
            onSort={consumption.toggleSort}
            meta={consumption.meta}
            page={consumption.page}
            onPage={consumption.setPage}
            pageSize={consumption.pageSize}
            onPageSize={consumption.setPageSize}
            caption="Feed consumption"
            empty={
              <EmptyState
                icon={Package}
                title="No consumption recorded"
                message="Record what the birds eat so the feed stock stays accurate."
                action={
                  <Button
                    icon={Plus}
                    onClick={() => {
                      setEditingConsumption(null)
                      setConsumptionOpen(true)
                    }}
                  >
                    Record consumption
                  </Button>
                }
              />
            }
          />
        )}
      </Card>

      <PurchaseForm
        open={purchaseOpen}
        purchase={editingPurchase}
        feedTypeOptions={feedTypeOptions}
        types={types}
        currency={currency}
        onClose={() => setPurchaseOpen(false)}
        onSaved={() => {
          setPurchaseOpen(false)
          refreshAll()
        }}
      />

      <ConsumptionForm
        open={consumptionOpen}
        record={editingConsumption}
        feedTypeOptions={feedTypeOptions}
        types={types}
        batchOptions={batchOptions}
        onClose={() => setConsumptionOpen(false)}
        onSaved={() => {
          setConsumptionOpen(false)
          refreshAll()
        }}
      />

      <FeedTypeForm
        open={typeOpen}
        onClose={() => setTypeOpen(false)}
        onSaved={() => {
          setTypeOpen(false)
          refreshAll()
        }}
      />

      <ConfirmDialog
        open={Boolean(deleting)}
        title={deleting?.kind === 'purchase' ? 'Reverse this purchase?' : 'Reverse this consumption record?'}
        message={
          deleting?.kind === 'purchase'
            ? 'The feed stock and the matching Feed expense will both be reversed. A purchase whose feed has already been consumed cannot be removed.'
            : 'The feed will be returned to stock. The record stays in the audit trail.'
        }
        confirmLabel="Reverse"
        onConfirm={confirmDelete}
        onClose={() => setDeleting(null)}
      />
    </>
  )
}

function PurchaseForm({ open, purchase, feedTypeOptions, types, currency, onClose, onSaved }) {
  const toast = useToast()
  const blank = {
    feed_type_id: '',
    purchase_date: todayISO(),
    brand: '',
    quantity_bags: '',
    bag_weight_kg: '50',
    cost_per_bag: '',
    supplier: '',
    lot_number: '',
    notes: '',
  }
  const [form, setForm] = useState(blank)
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    setErrors({})
    setForm(
      purchase
        ? {
            feed_type_id: String(purchase.feed_type_id),
            purchase_date: purchase.purchase_date,
            brand: purchase.brand || '',
            quantity_bags: purchase.quantity_bags,
            bag_weight_kg: purchase.bag_weight_kg,
            cost_per_bag: purchase.cost_per_bag,
            supplier: purchase.supplier || '',
            lot_number: purchase.lot_number || '',
            notes: purchase.notes || '',
          }
        : blank,
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, purchase])

  const update = (name, value) => {
    setForm((current) => {
      const next = { ...current, [name]: value }
      // Adopt the feed type's usual bag weight when it is chosen.
      if (name === 'feed_type_id' && !purchase) {
        const type = types.find((item) => String(item.id) === value)
        if (type) next.bag_weight_kg = type.default_bag_weight_kg
      }
      return next
    })
    setErrors((current) => ({ ...current, [name]: undefined }))
  }

  const total = toNumber(form.quantity_bags) * toNumber(form.cost_per_bag)

  const submit = async (event) => {
    event.preventDefault()
    const next = {}
    if (!purchase && !form.feed_type_id) next.feed_type_id = 'Choose the feed type.'
    if (toNumber(form.quantity_bags) <= 0) next.quantity_bags = 'Enter a quantity greater than zero.'
    if (toNumber(form.bag_weight_kg) <= 0) next.bag_weight_kg = 'Enter the weight of one bag.'
    if (toNumber(form.cost_per_bag) < 0) next.cost_per_bag = 'Cost cannot be negative.'
    if (!form.purchase_date) next.purchase_date = 'Choose the purchase date.'
    else if (form.purchase_date > todayISO()) next.purchase_date = 'The date cannot be in the future.'
    setErrors(next)
    if (Object.keys(next).length) return

    setSaving(true)
    try {
      const payload = {
        purchase_date: form.purchase_date,
        brand: form.brand.trim() || null,
        quantity_bags: String(form.quantity_bags),
        bag_weight_kg: String(form.bag_weight_kg),
        cost_per_bag: String(form.cost_per_bag || 0),
        supplier: form.supplier.trim() || null,
        lot_number: form.lot_number.trim() || null,
        notes: form.notes.trim() || null,
      }
      if (purchase) await feedApi.updatePurchase(purchase.id, payload)
      else await feedApi.createPurchase({ ...payload, feed_type_id: Number(form.feed_type_id) })
      toast.success(
        purchase ? 'The purchase was updated.' : 'Feed added to stock and recorded as an expense.',
      )
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
      title={purchase ? 'Edit feed purchase' : 'Record a feed purchase'}
      hint="The total cost is recorded as a Feed expense automatically."
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={submit} loading={saving}>
            {purchase ? 'Save changes' : 'Record purchase'}
          </Button>
        </>
      }
    >
      <form className="form-grid" onSubmit={submit} noValidate>
        <Field label="Feed type" error={errors.feed_type_id} required>
          {({ id, invalid }) => (
            <Select
              id={id}
              value={form.feed_type_id}
              onChange={(event) => update('feed_type_id', event.target.value)}
              options={feedTypeOptions}
              placeholder="Choose a feed type…"
              disabled={Boolean(purchase)}
              error={invalid}
            />
          )}
        </Field>

        <Field label="Purchase date" error={errors.purchase_date} required>
          {({ id, invalid }) => (
            <Input
              id={id}
              type="date"
              max={todayISO()}
              value={form.purchase_date}
              onChange={(event) => update('purchase_date', event.target.value)}
              error={invalid}
            />
          )}
        </Field>

        <Field label="Number of bags" error={errors.quantity_bags} required>
          {({ id, invalid }) => (
            <Input
              id={id}
              type="number"
              min="0.01"
              step="0.01"
              value={form.quantity_bags}
              onChange={(event) => update('quantity_bags', event.target.value)}
              placeholder="10"
              error={invalid}
            />
          )}
        </Field>

        <Field label="Weight per bag (kg)" error={errors.bag_weight_kg} required>
          {({ id, invalid }) => (
            <Input
              id={id}
              type="number"
              min="0.01"
              step="0.5"
              value={form.bag_weight_kg}
              onChange={(event) => update('bag_weight_kg', event.target.value)}
              error={invalid}
            />
          )}
        </Field>

        <Field
          label="Cost per bag"
          error={errors.cost_per_bag}
          required
          help={total > 0 ? `Total: ${formatMoney(total, currency)}` : undefined}
        >
          {({ id, invalid }) => (
            <Input
              id={id}
              type="number"
              min="0"
              step="1"
              prefix={currency}
              value={form.cost_per_bag}
              onChange={(event) => update('cost_per_bag', event.target.value)}
              placeholder="125000"
              error={invalid}
            />
          )}
        </Field>

        <Field label="Brand">
          {({ id }) => (
            <Input id={id} value={form.brand} onChange={(event) => update('brand', event.target.value)} placeholder="Ugachick" />
          )}
        </Field>

        <Field label="Supplier">
          {({ id }) => (
            <Input
              id={id}
              value={form.supplier}
              onChange={(event) => update('supplier', event.target.value)}
              placeholder="Ugachick Feeds"
            />
          )}
        </Field>

        <Field label="Lot / batch number">
          {({ id }) => (
            <Input id={id} value={form.lot_number} onChange={(event) => update('lot_number', event.target.value)} />
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

function ConsumptionForm({ open, record, feedTypeOptions, types, batchOptions, onClose, onSaved }) {
  const toast = useToast()
  const blank = { feed_type_id: '', batch_id: '', consumption_date: todayISO(), unit: 'bags', quantity: '', notes: '' }
  const [form, setForm] = useState(blank)
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    setErrors({})
    setForm(
      record
        ? {
            feed_type_id: String(record.feed_type_id),
            batch_id: record.batch_id ? String(record.batch_id) : '',
            consumption_date: record.consumption_date,
            unit: 'kg',
            quantity: record.quantity_kg,
            notes: record.notes || '',
          }
        : blank,
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, record])

  const selectedType = types.find((type) => String(type.id) === form.feed_type_id)
  const bagWeight = toNumber(selectedType?.default_bag_weight_kg) || 50
  const asKg = form.unit === 'bags' ? toNumber(form.quantity) * bagWeight : toNumber(form.quantity)
  const available = toNumber(selectedType?.stock_kg)

  const update = (name, value) => {
    setForm((current) => ({ ...current, [name]: value }))
    setErrors((current) => ({ ...current, [name]: undefined }))
  }

  const submit = async (event) => {
    event.preventDefault()
    const next = {}
    if (!record && !form.feed_type_id) next.feed_type_id = 'Choose the feed type.'
    if (toNumber(form.quantity) <= 0) next.quantity = 'Enter a quantity greater than zero.'
    else if (selectedType && !record && asKg > available) {
      next.quantity = `Only ${formatQuantity(available, 'kg')} of ${selectedType.name} is in stock.`
    }
    if (!form.consumption_date) next.consumption_date = 'Choose the date.'
    else if (form.consumption_date > todayISO()) next.consumption_date = 'The date cannot be in the future.'
    setErrors(next)
    if (Object.keys(next).length) return

    setSaving(true)
    try {
      const quantityFields =
        form.unit === 'bags' ? { quantity_bags: String(form.quantity) } : { quantity_kg: String(form.quantity) }
      const payload = {
        consumption_date: form.consumption_date,
        batch_id: form.batch_id ? Number(form.batch_id) : null,
        notes: form.notes.trim() || null,
        ...quantityFields,
      }
      if (record) await feedApi.updateConsumption(record.id, payload)
      else await feedApi.createConsumption({ ...payload, feed_type_id: Number(form.feed_type_id) })
      toast.success(record ? 'The record was updated.' : 'Feed consumption recorded and stock reduced.')
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
      title={record ? 'Edit consumption record' : 'Record feed consumption'}
      hint="Feed stock is reduced immediately and can never go below zero."
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={submit} loading={saving}>
            {record ? 'Save changes' : 'Record consumption'}
          </Button>
        </>
      }
    >
      <form className="form-grid" onSubmit={submit} noValidate>
        <Field label="Feed type" error={errors.feed_type_id} required>
          {({ id, invalid }) => (
            <Select
              id={id}
              value={form.feed_type_id}
              onChange={(event) => update('feed_type_id', event.target.value)}
              options={feedTypeOptions}
              placeholder="Choose a feed type…"
              disabled={Boolean(record)}
              error={invalid}
            />
          )}
        </Field>

        <Field label="Date" error={errors.consumption_date} required>
          {({ id, invalid }) => (
            <Input
              id={id}
              type="date"
              max={todayISO()}
              value={form.consumption_date}
              onChange={(event) => update('consumption_date', event.target.value)}
              error={invalid}
            />
          )}
        </Field>

        <Field label="Measured in">
          {({ id }) => (
            <Select
              id={id}
              value={form.unit}
              onChange={(event) => update('unit', event.target.value)}
              options={[
                { value: 'bags', label: 'Bags' },
                { value: 'kg', label: 'Kilograms' },
              ]}
            />
          )}
        </Field>

        <Field
          label={`Quantity consumed (${form.unit})`}
          error={errors.quantity}
          required
          help={
            selectedType
              ? `${formatQuantity(available, 'kg')} in stock. This entry is ${formatQuantity(asKg, 'kg')}.`
              : undefined
          }
        >
          {({ id, invalid }) => (
            <Input
              id={id}
              type="number"
              min="0.01"
              step="0.01"
              value={form.quantity}
              onChange={(event) => update('quantity', event.target.value)}
              error={invalid}
            />
          )}
        </Field>

        <Field label="Batch fed" help="Optional — leave blank if the feed went to the whole farm.">
          {({ id }) => (
            <Select
              id={id}
              value={form.batch_id}
              onChange={(event) => update('batch_id', event.target.value)}
              options={batchOptions}
              placeholder="Whole farm"
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

function FeedTypeForm({ open, onClose, onSaved }) {
  const toast = useToast()
  const [form, setForm] = useState({ name: '', description: '', default_bag_weight_kg: '50' })
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (open) {
      setForm({ name: '', description: '', default_bag_weight_kg: '50' })
      setErrors({})
    }
  }, [open])

  const submit = async () => {
    const next = {}
    if (form.name.trim().length < 2) next.name = 'Give the feed type a name.'
    if (toNumber(form.default_bag_weight_kg) <= 0) next.default_bag_weight_kg = 'Enter the usual bag weight.'
    setErrors(next)
    if (Object.keys(next).length) return

    setSaving(true)
    try {
      await feedApi.createType({
        name: form.name.trim(),
        description: form.description.trim() || null,
        default_bag_weight_kg: String(form.default_bag_weight_kg),
      })
      toast.success('The feed type was added.')
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
      title="Add a feed type"
      size="sm"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={submit} loading={saving}>
            Add feed type
          </Button>
        </>
      }
    >
      <div className="stack" style={{ gap: 12 }}>
        <Field label="Name" error={errors.name} required>
          {({ id, invalid }) => (
            <Input
              id={id}
              value={form.name}
              onChange={(event) => setForm((c) => ({ ...c, name: event.target.value }))}
              placeholder="Broiler Finisher"
              error={invalid}
            />
          )}
        </Field>
        <Field label="Usual bag weight (kg)" error={errors.default_bag_weight_kg} required>
          {({ id, invalid }) => (
            <Input
              id={id}
              type="number"
              min="1"
              step="0.5"
              value={form.default_bag_weight_kg}
              onChange={(event) => setForm((c) => ({ ...c, default_bag_weight_kg: event.target.value }))}
              error={invalid}
            />
          )}
        </Field>
        <Field label="Description">
          {({ id }) => (
            <Input
              id={id}
              value={form.description}
              onChange={(event) => setForm((c) => ({ ...c, description: event.target.value }))}
              placeholder="Fed from week 5 until sale"
            />
          )}
        </Field>
      </div>
    </Modal>
  )
}
