import { useState } from 'react'
import { Download, FileBarChart, FileSpreadsheet, FileText } from 'lucide-react'

import { reportsApi } from '../api/endpoints'
import { ExpenseBreakdownChart, ProfitTrendChart } from '../components/charts'
import { FilterSelect, PeriodFilter, periodParams } from '../components/Filters'
import StatCard from '../components/StatCard'
import {
  Badge,
  Button,
  Card,
  CardHead,
  EmptyState,
  ErrorState,
  PageHeader,
  SkeletonRows,
} from '../components/ui'
import { useSettings } from '../contexts/SettingsContext'
import { useToast } from '../contexts/ToastContext'
import { useApi } from '../hooks/useApi'
import { useBatchOptions } from '../hooks/useOptions'
import {
  formatDate,
  formatMoney,
  formatNumber,
  formatPercent,
  formatQuantity,
  titleCase,
  toNumber,
} from '../utils/format'

const REPORTS = [
  { id: 'birds', label: 'Bird report', exportable: true, batchFilter: true },
  { id: 'feed', label: 'Feed report', exportable: true },
  { id: 'expenses', label: 'Expense report', exportable: true },
  { id: 'sales', label: 'Sales report', exportable: true, batchFilter: true },
  { id: 'profit-loss', label: 'Profit & loss', exportable: true },
  { id: 'performance', label: 'Farm performance', exportable: false },
]

const LOADERS = {
  birds: reportsApi.birds,
  feed: reportsApi.feed,
  expenses: reportsApi.expenses,
  sales: reportsApi.sales,
  'profit-loss': reportsApi.profitLoss,
  performance: reportsApi.performance,
}

export default function Reports() {
  const { currency } = useSettings()
  const toast = useToast()
  const { options: batchOptions } = useBatchOptions()

  const [report, setReport] = useState('birds')
  const [period, setPeriod] = useState({ preset: 'all_time', start_date: '', end_date: '' })
  const [batchId, setBatchId] = useState('')
  const [downloading, setDownloading] = useState('')

  const active = REPORTS.find((item) => item.id === report)
  const params = { ...periodParams(period), ...(active?.batchFilter && batchId ? { batch_id: batchId } : {}) }
  const key = `${report}:${JSON.stringify(params)}`

  const { data, loading, error, reload } = useApi(() => LOADERS[report](params), [key])

  const download = async (format) => {
    setDownloading(format)
    try {
      await reportsApi.download(report, { ...params, format })
      toast.success(`The ${active.label.toLowerCase()} was downloaded as ${format.toUpperCase()}.`)
    } catch (caught) {
      toast.error(caught.message)
    } finally {
      setDownloading('')
    }
  }

  return (
    <>
      <PageHeader title="Reports" subtitle="Everything the farm has recorded, summarised and ready to share.">
        {active?.exportable && (
          <>
            <Button
              variant="secondary"
              icon={FileSpreadsheet}
              onClick={() => download('csv')}
              loading={downloading === 'csv'}
            >
              CSV
            </Button>
            <Button
              variant="secondary"
              icon={FileText}
              onClick={() => download('pdf')}
              loading={downloading === 'pdf'}
            >
              PDF
            </Button>
          </>
        )}
      </PageHeader>

      <Card style={{ marginBottom: 14 }}>
        <div className="tabs" role="tablist">
          {REPORTS.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={report === item.id}
              className={`tab ${report === item.id ? 'active' : ''}`}
              onClick={() => setReport(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <div className="toolbar" style={{ borderBottom: 0 }}>
          <PeriodFilter value={period} onChange={setPeriod} />
          {active?.batchFilter && (
            <FilterSelect
              label="Batch"
              value={batchId}
              onChange={setBatchId}
              options={batchOptions}
              placeholder="All batches"
            />
          )}
        </div>
      </Card>

      {error ? (
        <ErrorState error={error} onRetry={reload} />
      ) : loading && !data ? (
        <Card>
          <SkeletonRows rows={8} />
        </Card>
      ) : (
        data && (
          <>
            {report === 'birds' && <BirdReport data={data} currency={currency} />}
            {report === 'feed' && <FeedReport data={data} currency={currency} />}
            {report === 'expenses' && <ExpenseReport data={data} currency={currency} />}
            {report === 'sales' && <SalesReport data={data} currency={currency} />}
            {report === 'profit-loss' && <ProfitLossReport data={data} currency={currency} />}
            {report === 'performance' && <PerformanceReport data={data} currency={currency} />}
          </>
        )
      )}
    </>
  )
}

function ReportTable({ headers, children, caption }) {
  return (
    <div className="table-wrap">
      <table className="data">
        <caption className="visually-hidden">{caption}</caption>
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header.label} scope="col" className={header.align === 'right' ? 'num' : ''}>
                {header.label}
              </th>
            ))}
          </tr>
        </thead>
        {children}
      </table>
    </div>
  )
}

function BirdReport({ data, currency }) {
  const totals = data.totals
  if (!data.rows.length) {
    return (
      <Card>
        <EmptyState icon={FileBarChart} title="No bird batches in this period" message="Choose a wider period or add a batch first." />
      </Card>
    )
  }

  return (
    <>
      <div className="grid cols-4" style={{ marginBottom: 14 }}>
        <StatCard label="Initial birds" value={formatNumber(totals.initial_quantity)} />
        <StatCard label="Current birds" value={formatNumber(totals.current_quantity)} tone="brand" />
        <StatCard label="Deaths / sold" value={`${formatNumber(totals.deaths)} / ${formatNumber(totals.sold)}`} small />
        <StatCard
          label="Mortality rate"
          value={formatPercent(totals.mortality_rate, 2)}
          valueTone={totals.mortality_rate >= 5 ? 'negative' : ''}
          tone={totals.mortality_rate >= 5 ? 'critical' : 'good'}
        />
      </div>
      <Card>
        <CardHead title="Bird report" hint="One row per batch" />
        <ReportTable
          caption="Bird report"
          headers={[
            { label: 'Batch' },
            { label: 'Breed' },
            { label: 'Acquired' },
            { label: 'Initial', align: 'right' },
            { label: 'Deaths', align: 'right' },
            { label: 'Sold', align: 'right' },
            { label: 'Other losses', align: 'right' },
            { label: 'Current', align: 'right' },
            { label: 'Sick', align: 'right' },
            { label: 'Mortality', align: 'right' },
            { label: 'Cost', align: 'right' },
          ]}
        >
          <tbody>
            {data.rows.map((row) => (
              <tr key={row.batch_id}>
                <td><strong>{row.batch_code}</strong></td>
                <td>{row.breed}</td>
                <td>{formatDate(row.acquisition_date)}</td>
                <td className="num">{formatNumber(row.initial_quantity)}</td>
                <td className="num">{formatNumber(row.deaths)}</td>
                <td className="num">{formatNumber(row.sold)}</td>
                <td className="num">{formatNumber(row.other_losses)}</td>
                <td className="num"><strong>{formatNumber(row.current_quantity)}</strong></td>
                <td className="num">{formatNumber(row.sick_count)}</td>
                <td className="num">{formatPercent(row.mortality_rate, 2)}</td>
                <td className="num">{formatMoney(row.acquisition_cost, currency)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={3}>All batches</td>
              <td className="num">{formatNumber(totals.initial_quantity)}</td>
              <td className="num">{formatNumber(totals.deaths)}</td>
              <td className="num">{formatNumber(totals.sold)}</td>
              <td className="num">{formatNumber(totals.other_losses)}</td>
              <td className="num">{formatNumber(totals.current_quantity)}</td>
              <td className="num">{formatNumber(totals.sick_count)}</td>
              <td className="num">{formatPercent(totals.mortality_rate, 2)}</td>
              <td className="num">{formatMoney(totals.acquisition_cost, currency)}</td>
            </tr>
          </tfoot>
        </ReportTable>
      </Card>
    </>
  )
}

function FeedReport({ data, currency }) {
  if (!data.rows.length) {
    return (
      <Card>
        <EmptyState icon={FileBarChart} title="No feed activity in this period" message="Record a feed purchase to populate this report." />
      </Card>
    )
  }
  return (
    <>
      <div className="grid cols-4" style={{ marginBottom: 14 }}>
        <StatCard label="Purchased" value={formatQuantity(data.total_purchased_kg, 'kg')} />
        <StatCard label="Consumed" value={formatQuantity(data.total_consumed_kg, 'kg')} />
        <StatCard label="Current stock" value={formatQuantity(data.total_stock_kg, 'kg')} tone="brand" />
        <StatCard label="Feed expenditure" value={formatMoney(data.total_cost, currency)} tone="gold" small />
      </div>
      <Card>
        <CardHead title="Feed report" hint="Stock is a running position and always reflects every record" />
        <ReportTable
          caption="Feed report"
          headers={[
            { label: 'Feed type' },
            { label: 'Purchased (bags)', align: 'right' },
            { label: 'Purchased (kg)', align: 'right' },
            { label: 'Consumed (bags)', align: 'right' },
            { label: 'Consumed (kg)', align: 'right' },
            { label: 'Stock (bags)', align: 'right' },
            { label: 'Stock (kg)', align: 'right' },
            { label: 'Cost', align: 'right' },
          ]}
        >
          <tbody>
            {data.rows.map((row) => (
              <tr key={row.feed_type_id}>
                <td><strong>{row.feed_type}</strong></td>
                <td className="num">{formatQuantity(row.purchased_bags)}</td>
                <td className="num">{formatQuantity(row.purchased_kg)}</td>
                <td className="num">{formatQuantity(row.consumed_bags)}</td>
                <td className="num">{formatQuantity(row.consumed_kg)}</td>
                <td className="num">{formatQuantity(row.stock_bags)}</td>
                <td className="num"><strong>{formatQuantity(row.stock_kg)}</strong></td>
                <td className="num">{formatMoney(row.total_cost, currency)}</td>
              </tr>
            ))}
          </tbody>
        </ReportTable>
      </Card>
    </>
  )
}

function ExpenseReport({ data, currency }) {
  if (!data.rows.length) {
    return (
      <Card>
        <EmptyState icon={FileBarChart} title="No expenses in this period" message="Widen the period or record an expense." />
      </Card>
    )
  }
  return (
    <>
      <div className="grid cols-2" style={{ marginBottom: 14 }}>
        <StatCard label="Total expenses" value={formatMoney(data.total, currency)} tone="gold" />
        <StatCard label="Categories used" value={String(data.rows.length)} small />
      </div>
      <Card style={{ marginBottom: 14 }}>
        <CardHead title="Expenses by category" />
        <div className="card-body tight">
          <ExpenseBreakdownChart data={data.rows} currency={currency} />
        </div>
      </Card>
      <Card>
        <CardHead title="Expense report" />
        <ReportTable
          caption="Expense report"
          headers={[
            { label: 'Category' },
            { label: 'Entries', align: 'right' },
            { label: 'Amount', align: 'right' },
            { label: 'Share', align: 'right' },
          ]}
        >
          <tbody>
            {data.rows.map((row) => (
              <tr key={row.category}>
                <td>{row.category}</td>
                <td className="num">{formatNumber(row.count)}</td>
                <td className="num"><strong>{formatMoney(row.amount, currency)}</strong></td>
                <td className="num">{formatPercent(row.percentage)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td>Total</td>
              <td className="num">{formatNumber(data.rows.reduce((sum, row) => sum + row.count, 0))}</td>
              <td className="num">{formatMoney(data.total, currency)}</td>
              <td className="num">100.0%</td>
            </tr>
          </tfoot>
        </ReportTable>
      </Card>
    </>
  )
}

function SalesReport({ data, currency }) {
  if (!data.rows.length) {
    return (
      <Card>
        <EmptyState icon={FileBarChart} title="No sales in this period" message="Widen the period or record a sale." />
      </Card>
    )
  }
  return (
    <>
      <div className="grid cols-4" style={{ marginBottom: 14 }}>
        <StatCard label="Birds sold" value={formatNumber(data.total_birds_sold)} tone="brand" />
        <StatCard label="Revenue" value={formatMoney(data.total_revenue, currency)} tone="info" small />
        <StatCard label="Collected" value={formatMoney(data.total_collected, currency)} tone="good" small />
        <StatCard label="Customers" value={formatNumber(data.customers)} small />
      </div>
      <Card>
        <CardHead title="Sales report" />
        <ReportTable
          caption="Sales report"
          headers={[
            { label: 'Reference' },
            { label: 'Date' },
            { label: 'Batch' },
            { label: 'Customer' },
            { label: 'Birds', align: 'right' },
            { label: 'Unit price', align: 'right' },
            { label: 'Total', align: 'right' },
            { label: 'Paid', align: 'right' },
            { label: 'Status' },
          ]}
        >
          <tbody>
            {data.rows.map((row) => (
              <tr key={row.sale_id}>
                <td><strong>{row.reference}</strong></td>
                <td>{formatDate(row.sale_date)}</td>
                <td>{row.batch_code}</td>
                <td>{row.customer || 'Walk-in'}</td>
                <td className="num">{formatNumber(row.quantity)}</td>
                <td className="num">{formatMoney(row.unit_price, currency)}</td>
                <td className="num"><strong>{formatMoney(row.total_amount, currency)}</strong></td>
                <td className="num">{formatMoney(row.amount_paid, currency)}</td>
                <td><Badge status={row.payment_status}>{titleCase(row.payment_status)}</Badge></td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={4}>Total</td>
              <td className="num">{formatNumber(data.total_birds_sold)}</td>
              <td className="num">—</td>
              <td className="num">{formatMoney(data.total_revenue, currency)}</td>
              <td className="num">{formatMoney(data.total_collected, currency)}</td>
              <td />
            </tr>
          </tfoot>
        </ReportTable>
      </Card>
    </>
  )
}

function ProfitLossReport({ data, currency }) {
  const net = toNumber(data.net_profit_or_loss)
  return (
    <>
      <div className="grid cols-3" style={{ marginBottom: 14 }}>
        <StatCard label="Revenue" value={formatMoney(data.total_revenue, currency)} tone="info" small />
        <StatCard label="Expenses" value={formatMoney(data.total_expenses, currency)} tone="gold" small />
        <StatCard
          label={data.is_profit ? 'Net profit' : 'Net loss'}
          value={formatMoney(Math.abs(net), currency)}
          meta={`Margin ${formatPercent(data.profit_margin_percent)}`}
          tone={data.is_profit ? 'good' : 'critical'}
          valueTone={data.is_profit ? 'positive' : 'negative'}
          small
        />
      </div>

      <Card style={{ marginBottom: 14 }}>
        <CardHead title="Profit and loss trend" hint="Month by month" />
        <div className="card-body tight">
          <ProfitTrendChart data={data.trend} currency={currency} />
        </div>
      </Card>

      <Card>
        <CardHead title="Profit & loss statement" />
        <ReportTable caption="Profit and loss statement" headers={[{ label: 'Item' }, { label: 'Amount', align: 'right' }]}>
          <tbody>
            <tr>
              <td><strong>Revenue from sales</strong></td>
              <td className="num"><strong>{formatMoney(data.total_revenue, currency)}</strong></td>
            </tr>
            {data.expenses_by_category.map((row) => (
              <tr key={row.category}>
                <td style={{ paddingLeft: 28 }}>Expenses — {row.category}</td>
                <td className="num">−{formatMoney(row.amount, currency)}</td>
              </tr>
            ))}
            <tr>
              <td><strong>Total expenses</strong></td>
              <td className="num"><strong>−{formatMoney(data.total_expenses, currency)}</strong></td>
            </tr>
          </tbody>
          <tfoot>
            <tr>
              <td>{data.is_profit ? 'Net profit' : 'Net loss'}</td>
              <td className="num" style={{ color: data.is_profit ? undefined : 'var(--critical)' }}>
                {formatMoney(Math.abs(net), currency)}
              </td>
            </tr>
          </tfoot>
        </ReportTable>
      </Card>
    </>
  )
}

function PerformanceReport({ data, currency }) {
  const { birds, feed, finance } = data
  const net = toNumber(finance.net_profit_or_loss)
  return (
    <>
      <div className="grid cols-4" style={{ marginBottom: 14 }}>
        <StatCard label="Birds on the farm" value={formatNumber(birds.total_birds)} tone="brand" />
        <StatCard label="Mortality rate" value={formatPercent(birds.mortality_rate, 2)} tone={birds.mortality_rate >= 5 ? 'critical' : 'good'} />
        <StatCard label="Feed in stock" value={formatQuantity(feed.stock_bags, 'bags')} tone="gold" small />
        <StatCard
          label={net >= 0 ? 'Net profit' : 'Net loss'}
          value={formatMoney(Math.abs(net), currency)}
          tone={net >= 0 ? 'good' : 'critical'}
          valueTone={net >= 0 ? 'positive' : 'negative'}
          small
        />
      </div>

      <div className="grid cols-2">
        <Card>
          <CardHead title="Efficiency" hint="Unit economics derived from your records" />
          <div className="card-body">
            <dl className="detail-list">
              <div>
                <dt>Feed cost per bird acquired</dt>
                <dd>{formatMoney(data.feed_cost_per_bird, currency)}</dd>
              </div>
              <div>
                <dt>Total cost per bird sold</dt>
                <dd>{formatMoney(data.cost_per_bird_sold, currency)}</dd>
              </div>
              <div>
                <dt>Revenue per bird sold</dt>
                <dd>{formatMoney(data.revenue_per_bird_sold, currency)}</dd>
              </div>
              <div>
                <dt>Average sale price</dt>
                <dd>{formatMoney(data.average_sale_price, currency)}</dd>
              </div>
            </dl>
          </div>
        </Card>

        <Card>
          <CardHead title="Flock and money at a glance" />
          <div className="card-body">
            <dl className="detail-list">
              <div>
                <dt>Birds acquired</dt>
                <dd>{formatNumber(birds.initial_birds)}</dd>
              </div>
              <div>
                <dt>Died / sold / other losses</dt>
                <dd>
                  {formatNumber(birds.dead_birds)} / {formatNumber(birds.sold_birds)} /{' '}
                  {formatNumber(birds.other_losses)}
                </dd>
              </div>
              <div>
                <dt>Sick right now</dt>
                <dd>{formatNumber(birds.sick_birds)}</dd>
              </div>
              <div>
                <dt>Feed consumed</dt>
                <dd>{formatQuantity(feed.consumed_kg, 'kg')}</dd>
              </div>
              <div>
                <dt>Revenue / expenses</dt>
                <dd>
                  {formatMoney(finance.total_revenue, currency)} /{' '}
                  {formatMoney(finance.total_expenses, currency)}
                </dd>
              </div>
              <div>
                <dt>Budget remaining</dt>
                <dd>{formatMoney(finance.remaining_budget, currency)}</dd>
              </div>
            </dl>
          </div>
        </Card>
      </div>
    </>
  )
}
