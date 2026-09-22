import { useEffect, useState } from 'react'
import {
  AlertTriangle,
  Banknote,
  Pencil,
  PiggyBank,
  Plus,
  Receipt,
  Trash2,
  TrendingDown,
  TrendingUp,
  Wallet,
} from 'lucide-react'

import { financeApi } from '../api/endpoints'
import { ExpenseBreakdownChart, ProfitTrendChart, RevenueExpensesChart } from '../components/charts'
import { PeriodFilter, periodParams } from '../components/Filters'
import StatCard from '../components/StatCard'
import {
  Badge,
  Button,
  Card,
  CardHead,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  Field,
  Input,
  Modal,
  PageHeader,
  Progress,
  SkeletonCards,
  TextArea,
} from '../components/ui'
import { useAuth } from '../contexts/AuthContext'
import { useSettings } from '../contexts/SettingsContext'
import { useToast } from '../contexts/ToastContext'
import { useApi } from '../hooks/useApi'
import { formatDate, formatMoney, formatPercent, toNumber, todayISO } from '../utils/format'

export default function Finance() {
  const { isAdmin } = useAuth()
  const { currency } = useSettings()
  const toast = useToast()

  const [period, setPeriod] = useState({ preset: 'all_time', start_date: '', end_date: '' })
  const [budgetOpen, setBudgetOpen] = useState(false)
  const [editingBudget, setEditingBudget] = useState(null)
  const [deletingBudget, setDeletingBudget] = useState(null)

  const summary = useApi(() => financeApi.summary(periodParams(period)), [JSON.stringify(period)])
  const budgets = useApi(() => financeApi.budgets(), [])

  const data = summary.data
  const net = toNumber(data?.net_profit_or_loss)

  const refresh = () => {
    summary.reload()
    budgets.reload()
  }

  const removeBudget = async () => {
    try {
      await financeApi.removeBudget(deletingBudget.id)
      toast.success('The budget was removed.')
      setDeletingBudget(null)
      refresh()
    } catch (error) {
      toast.error(error.message)
      setDeletingBudget(null)
    }
  }

  return (
    <>
      <PageHeader title="Finance" subtitle="Budget, revenue, expenses and what the farm is really making.">
        {isAdmin && (
          <Button
            icon={Plus}
            onClick={() => {
              setEditingBudget(null)
              setBudgetOpen(true)
            }}
          >
            New budget
          </Button>
        )}
      </PageHeader>

      <Card style={{ marginBottom: 14 }}>
        <div className="toolbar" style={{ borderBottom: 0 }}>
          <PeriodFilter value={period} onChange={setPeriod} />
          <div style={{ flex: 1 }} />
          <span style={{ fontSize: '0.8rem', color: 'var(--ink-muted)' }}>
            Revenue, expenses and profit below respect this period. Budget figures always cover the
            budget&apos;s own dates.
          </span>
        </div>
      </Card>

      {summary.error ? (
        <ErrorState error={summary.error} onRetry={summary.reload} />
      ) : summary.loading && !data ? (
        <SkeletonCards count={4} />
      ) : (
        data && (
          <>
            <div className="grid cols-4" style={{ marginBottom: 14 }}>
              <StatCard
                label="Revenue"
                value={formatMoney(data.total_revenue, currency)}
                meta={`${formatMoney(data.cash_collected, currency)} actually received`}
                icon={Banknote}
                tone="info"
                small
              />
              <StatCard
                label="Expenses"
                value={formatMoney(data.total_expenses, currency)}
                meta="Every recorded cost"
                icon={Receipt}
                tone="gold"
                small
              />
              <StatCard
                label={net >= 0 ? 'Net profit' : 'Net loss'}
                value={formatMoney(Math.abs(net), currency)}
                meta={`Margin ${formatPercent(data.profit_margin_percent)} · revenue − expenses`}
                icon={net >= 0 ? TrendingUp : TrendingDown}
                tone={net >= 0 ? 'good' : 'critical'}
                valueTone={net >= 0 ? 'positive' : 'negative'}
                small
              />
              <StatCard
                label="Net cash position"
                value={formatMoney(data.net_cash_position, currency)}
                meta={`${formatMoney(data.outstanding_receivables, currency)} still owed by customers`}
                icon={Wallet}
                tone={toNumber(data.net_cash_position) >= 0 ? 'brand' : 'critical'}
                valueTone={toNumber(data.net_cash_position) >= 0 ? '' : 'negative'}
                small
              />
            </div>

            {/* The brief's central warning, made explicit in the interface. */}
            <Card style={{ marginBottom: 14 }}>
              <CardHead
                title="Budget vs profit — two different things"
                hint="A budget balance is money you are still allowed to spend. Profit is what the farm has earned."
              />
              <div className="card-body">
                <div className="grid cols-2" style={{ gap: 20 }}>
                  <div className="stack" style={{ gap: 10 }}>
                    <div className="row between">
                      <strong style={{ fontSize: '0.9rem' }}>Budget</strong>
                      {data.active_budget ? (
                        <Badge tone={data.active_budget.is_exceeded ? 'critical' : 'info'}>
                          {data.active_budget.name}
                        </Badge>
                      ) : (
                        <Badge>No active budget</Badge>
                      )}
                    </div>
                    <dl className="detail-list">
                      <div>
                        <dt>Original budget</dt>
                        <dd>{formatMoney(data.budget_total, currency)}</dd>
                      </div>
                      <div>
                        <dt>Spent</dt>
                        <dd>{formatMoney(data.budget_spent, currency)}</dd>
                      </div>
                      <div>
                        <dt>Remaining to spend</dt>
                        <dd style={{ color: toNumber(data.budget_remaining) < 0 ? 'var(--critical)' : undefined }}>
                          {formatMoney(data.budget_remaining, currency)}
                        </dd>
                      </div>
                    </dl>
                    <Progress value={data.budget_percentage_spent} />
                    <div className="row between" style={{ fontSize: '0.78rem', color: 'var(--ink-2)' }}>
                      <span>{formatPercent(data.budget_percentage_spent)} spent</span>
                      <span>{formatPercent(Math.max(0, 100 - data.budget_percentage_spent))} remaining</span>
                    </div>
                    {data.active_budget?.is_exceeded && (
                      <Badge tone="critical" icon={AlertTriangle}>
                        Budget exceeded by{' '}
                        {formatMoney(Math.abs(toNumber(data.budget_remaining)), currency)}
                      </Badge>
                    )}
                  </div>

                  <div className="stack" style={{ gap: 10 }}>
                    <div className="row between">
                      <strong style={{ fontSize: '0.9rem' }}>Trading result</strong>
                      <Badge tone={net >= 0 ? 'good' : 'critical'}>{net >= 0 ? 'Profit' : 'Loss'}</Badge>
                    </div>
                    <dl className="detail-list">
                      <div>
                        <dt>Revenue from sales</dt>
                        <dd>{formatMoney(data.total_revenue, currency)}</dd>
                      </div>
                      <div>
                        <dt>Less: total expenses</dt>
                        <dd>−{formatMoney(data.total_expenses, currency)}</dd>
                      </div>
                      <div
                        style={{
                          borderTop: '1px solid var(--border)',
                          paddingTop: 8,
                          fontSize: '0.95rem',
                        }}
                      >
                        <dt style={{ fontWeight: 650, color: 'var(--ink)' }}>
                          {net >= 0 ? 'Net profit' : 'Net loss'}
                        </dt>
                        <dd className={net >= 0 ? 'value positive' : 'value negative'} style={{ fontSize: '1.05rem' }}>
                          {formatMoney(Math.abs(net), currency)}
                        </dd>
                      </div>
                    </dl>
                    <p style={{ fontSize: '0.78rem', color: 'var(--ink-muted)' }}>
                      Of that revenue, {formatMoney(data.cash_collected, currency)} has actually been
                      received; {formatMoney(data.outstanding_receivables, currency)} is still owed.
                    </p>
                  </div>
                </div>
              </div>
            </Card>

            <div className="grid cols-2" style={{ marginBottom: 14 }}>
              <Card>
                <CardHead title="Revenue vs expenses" hint="Month by month" />
                <div className="card-body tight">
                  <RevenueExpensesChart data={data.trend} currency={currency} />
                </div>
              </Card>
              <Card>
                <CardHead title="Profit and loss trend" hint="Green months made money, red months lost it" />
                <div className="card-body tight">
                  <ProfitTrendChart data={data.trend} currency={currency} />
                </div>
              </Card>
            </div>

            <Card style={{ marginBottom: 14 }}>
              <CardHead title="Expense breakdown" hint="Where the money went in this period" />
              <div className="card-body tight">
                <ExpenseBreakdownChart data={data.expenses_by_category} currency={currency} />
              </div>
            </Card>
          </>
        )
      )}

      <Card>
        <CardHead title="Budgets" hint="Each budget tracks the expenses recorded inside its own dates" />
        {budgets.loading && !budgets.data ? (
          <SkeletonCards count={2} height={80} />
        ) : (budgets.data ?? []).length === 0 ? (
          <EmptyState
            icon={PiggyBank}
            title="No budget has been set"
            message="Set a budget so the system can tell you how much you have left to spend and warn you before you run out."
            action={
              isAdmin ? (
                <Button
                  icon={Plus}
                  onClick={() => {
                    setEditingBudget(null)
                    setBudgetOpen(true)
                  }}
                >
                  Create first budget
                </Button>
              ) : null
            }
          />
        ) : (
          <div className="table-wrap">
            <table className="data">
              <caption className="visually-hidden">Budgets</caption>
              <thead>
                <tr>
                  <th scope="col">Budget</th>
                  <th scope="col">Period</th>
                  <th scope="col" className="num">Amount</th>
                  <th scope="col" className="num">Spent</th>
                  <th scope="col" className="num">Remaining</th>
                  <th scope="col" style={{ minWidth: 160 }}>Progress</th>
                  <th scope="col">Status</th>
                  {isAdmin && <th scope="col" />}
                </tr>
              </thead>
              <tbody>
                {budgets.data.map((budget) => (
                  <tr key={budget.id}>
                    <td>
                      <strong>{budget.name}</strong>
                      {budget.notes && (
                        <div style={{ fontSize: '0.75rem', color: 'var(--ink-muted)' }}>{budget.notes}</div>
                      )}
                    </td>
                    <td>
                      {formatDate(budget.start_date)} – {formatDate(budget.end_date)}
                    </td>
                    <td className="num">{formatMoney(budget.amount, currency)}</td>
                    <td className="num">{formatMoney(budget.spent, currency)}</td>
                    <td className="num" style={{ color: budget.is_exceeded ? 'var(--critical)' : undefined }}>
                      <strong>{formatMoney(budget.remaining, currency)}</strong>
                    </td>
                    <td>
                      <Progress value={budget.percentage_spent} />
                      <div style={{ fontSize: '0.72rem', color: 'var(--ink-muted)', marginTop: 3 }}>
                        {formatPercent(budget.percentage_spent)} spent
                      </div>
                    </td>
                    <td>
                      {budget.is_exceeded ? (
                        <Badge tone="critical" icon={AlertTriangle}>Exceeded</Badge>
                      ) : budget.percentage_spent >= 80 ? (
                        <Badge tone="warning">Nearly spent</Badge>
                      ) : budget.is_active ? (
                        <Badge tone="good">Active</Badge>
                      ) : (
                        <Badge>Inactive</Badge>
                      )}
                    </td>
                    {isAdmin && (
                      <td className="num">
                        <div className="row-actions">
                          <button
                            type="button"
                            className="icon-btn"
                            aria-label={`Edit ${budget.name}`}
                            title="Edit budget"
                            onClick={() => {
                              setEditingBudget(budget)
                              setBudgetOpen(true)
                            }}
                          >
                            <Pencil size={15} />
                          </button>
                          <button
                            type="button"
                            className="icon-btn"
                            aria-label={`Delete ${budget.name}`}
                            title="Delete budget"
                            onClick={() => setDeletingBudget(budget)}
                          >
                            <Trash2 size={15} />
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <BudgetForm
        open={budgetOpen}
        budget={editingBudget}
        currency={currency}
        onClose={() => setBudgetOpen(false)}
        onSaved={() => {
          setBudgetOpen(false)
          refresh()
        }}
      />

      <ConfirmDialog
        open={Boolean(deletingBudget)}
        title={`Delete “${deletingBudget?.name}”?`}
        message="The budget will be removed. Your expenses are not affected."
        confirmLabel="Delete budget"
        onConfirm={removeBudget}
        onClose={() => setDeletingBudget(null)}
      />
    </>
  )
}

function BudgetForm({ open, budget, currency, onClose, onSaved }) {
  const toast = useToast()
  const blank = {
    name: '',
    amount: '',
    start_date: todayISO(),
    end_date: todayISO(),
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
      budget
        ? {
            name: budget.name,
            amount: budget.amount,
            start_date: budget.start_date,
            end_date: budget.end_date,
            is_active: budget.is_active,
            notes: budget.notes || '',
          }
        : blank,
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, budget])

  const update = (name, value) => {
    setForm((current) => ({ ...current, [name]: value }))
    setErrors((current) => ({ ...current, [name]: undefined }))
  }

  const submit = async (event) => {
    event.preventDefault()
    const next = {}
    if (form.name.trim().length < 2) next.name = 'Give the budget a name.'
    if (toNumber(form.amount) <= 0) next.amount = 'Enter an amount greater than zero.'
    if (!form.start_date) next.start_date = 'Choose a start date.'
    if (!form.end_date) next.end_date = 'Choose an end date.'
    else if (form.end_date < form.start_date) next.end_date = 'The end date must be on or after the start date.'
    setErrors(next)
    if (Object.keys(next).length) return

    setSaving(true)
    try {
      const payload = {
        name: form.name.trim(),
        amount: String(form.amount),
        start_date: form.start_date,
        end_date: form.end_date,
        is_active: form.is_active,
        notes: form.notes.trim() || null,
      }
      if (budget) await financeApi.updateBudget(budget.id, payload)
      else await financeApi.createBudget(payload)
      toast.success(budget ? 'The budget was updated.' : 'The budget was created.')
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
      title={budget ? 'Edit budget' : 'Create a budget'}
      hint="Expenses dated inside this period count against the budget."
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={submit} loading={saving}>
            {budget ? 'Save changes' : 'Create budget'}
          </Button>
        </>
      }
    >
      <form className="form-grid" onSubmit={submit} noValidate>
        <Field label="Budget name" error={errors.name} required span2>
          {({ id, invalid }) => (
            <Input
              id={id}
              value={form.name}
              onChange={(event) => update('name', event.target.value)}
              placeholder="Season 1 — Broilers"
              error={invalid}
            />
          )}
        </Field>

        <Field label="Budget amount" error={errors.amount} required>
          {({ id, invalid }) => (
            <Input
              id={id}
              type="number"
              min="1"
              step="1"
              prefix={currency}
              value={form.amount}
              onChange={(event) => update('amount', event.target.value)}
              placeholder="1000000"
              error={invalid}
            />
          )}
        </Field>

        <Field label="Active" className="inline-check">
          <label className="row" style={{ gap: 8, fontSize: '0.86rem' }}>
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(event) => update('is_active', event.target.checked)}
              style={{ width: 'auto', minHeight: 0 }}
            />
            Use this budget for dashboard figures
          </label>
        </Field>

        <Field label="Start date" error={errors.start_date} required>
          {({ id, invalid }) => (
            <Input
              id={id}
              type="date"
              value={form.start_date}
              onChange={(event) => update('start_date', event.target.value)}
              error={invalid}
            />
          )}
        </Field>

        <Field label="End date" error={errors.end_date} required>
          {({ id, invalid }) => (
            <Input
              id={id}
              type="date"
              min={form.start_date}
              value={form.end_date}
              onChange={(event) => update('end_date', event.target.value)}
              error={invalid}
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
