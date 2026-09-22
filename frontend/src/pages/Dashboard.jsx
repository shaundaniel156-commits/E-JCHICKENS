import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowRight,
  Bell,
  CheckCircle2,
  Egg,
  HeartPulse,
  Info,
  Receipt,
  RefreshCw,
  ShoppingCart,
  Skull,
  TrendingDown,
  TrendingUp,
  Wallet,
  Wheat,
} from 'lucide-react'

import { dashboardApi } from '../api/endpoints'
import {
  BirdPopulationChart,
  ExpenseBreakdownChart,
  FeedUsageChart,
  MortalityChart,
  ProfitTrendChart,
  RevenueExpensesChart,
} from '../components/charts'
import StatCard from '../components/StatCard'
import {
  Badge,
  Button,
  Card,
  CardHead,
  EmptyState,
  ErrorState,
  PageHeader,
  SkeletonCards,
  Spinner,
} from '../components/ui'
import { useAuth } from '../contexts/AuthContext'
import { useSettings } from '../contexts/SettingsContext'
import { useApi } from '../hooks/useApi'
import {
  formatMoney,
  formatNumber,
  formatPercent,
  formatQuantity,
  formatRelative,
  greeting,
  toNumber,
} from '../utils/format'

const ALERT_ICONS = { CRITICAL: AlertTriangle, WARNING: AlertTriangle, SUCCESS: CheckCircle2, INFO: Info }

export default function Dashboard() {
  const { user, isManager } = useAuth()
  const { currency } = useSettings()
  const { data, loading, error, reload } = useApi(() => dashboardApi.summary(), [])

  if (loading && !data) {
    return (
      <>
        <PageHeader title={greeting(user?.full_name)} subtitle="Loading your farm overview…" />
        <div className="stack">
          <SkeletonCards count={4} />
          <SkeletonCards count={4} />
        </div>
      </>
    )
  }

  if (error && !data) {
    return (
      <>
        <PageHeader title="Dashboard" />
        <ErrorState error={error} onRetry={reload} />
      </>
    )
  }

  const { birds, feed, finance, charts, recent_activity: activity, alerts, has_data: hasData } = data
  const netAmount = toNumber(finance.net_profit_or_loss)

  return (
    <>
      <PageHeader
        title={greeting(user?.full_name)}
        subtitle={`Here is how ${data.farm_name} is doing today.`}
      >
        <Button variant="secondary" icon={RefreshCw} onClick={reload} loading={loading}>
          Refresh
        </Button>
      </PageHeader>

      {!hasData && (
        <Card style={{ marginBottom: 16 }}>
          <EmptyState
            icon={Egg}
            title="Your farm has no records yet"
            message="Start by adding a bird batch. Once birds, feed, expenses and sales are recorded, every figure on this page fills in automatically."
            action={
              <Link to="/birds" className="btn">
                Add your first batch <ArrowRight size={16} />
              </Link>
            }
          />
        </Card>
      )}

      {/* ---------------------------------------------------------- flock */}
      <section aria-labelledby="flock-heading" className="stack" style={{ marginBottom: 18 }}>
        <h2 id="flock-heading" style={{ fontSize: '0.86rem', color: 'var(--ink-2)' }}>
          Flock &amp; feed
        </h2>
        <div className="grid cols-4">
          <StatCard
            label="Birds on the farm"
            value={formatNumber(birds.total_birds)}
            meta={`${formatNumber(birds.initial_birds)} acquired across ${birds.total_batches} batch${
              birds.total_batches === 1 ? '' : 'es'
            }`}
            icon={Egg}
            tone="brand"
          />
          <StatCard
            label="Sick birds"
            value={formatNumber(birds.sick_birds)}
            meta={`${formatNumber(birds.healthy_birds)} healthy and available`}
            icon={HeartPulse}
            tone={birds.sick_birds > 0 ? 'warning' : 'good'}
          />
          <StatCard
            label="Dead birds"
            value={formatNumber(birds.dead_birds)}
            meta={`Mortality rate ${formatPercent(birds.mortality_rate, 2)}`}
            icon={Skull}
            tone={birds.mortality_rate >= 5 ? 'critical' : ''}
            valueTone={birds.mortality_rate >= 5 ? 'negative' : ''}
          />
          <StatCard
            label="Feed in stock"
            value={formatQuantity(feed.stock_bags, 'bags')}
            meta={`${formatQuantity(feed.stock_kg, 'kg')} · ${formatQuantity(
              feed.consumed_bags,
              'bags',
            )} consumed`}
            icon={Wheat}
            tone={feed.low_stock ? 'warning' : 'gold'}
            footer={
              feed.low_stock ? (
                <Badge tone="warning" icon={AlertTriangle}>
                  Below {formatQuantity(feed.low_stock_threshold_bags)} bags
                </Badge>
              ) : null
            }
          />
        </div>
      </section>

      {/* --------------------------------------------------------- money */}
      <section aria-labelledby="money-heading" className="stack" style={{ marginBottom: 18 }}>
        <h2 id="money-heading" style={{ fontSize: '0.86rem', color: 'var(--ink-2)' }}>
          Money
        </h2>
        <div className="grid cols-4">
          <StatCard
            label="Revenue"
            value={formatMoney(finance.total_revenue, currency)}
            meta={`${formatMoney(finance.cash_collected, currency)} collected · ${formatNumber(
              birds.sold_birds,
            )} birds sold`}
            icon={ShoppingCart}
            tone="info"
            small
          />
          <StatCard
            label="Expenses"
            value={formatMoney(finance.total_expenses, currency)}
            meta="Every cost recorded, including automatic entries"
            icon={Receipt}
            tone="gold"
            small
          />
          <StatCard
            label={netAmount >= 0 ? 'Net profit' : 'Net loss'}
            value={formatMoney(Math.abs(netAmount), currency)}
            meta="Revenue − expenses"
            icon={netAmount >= 0 ? TrendingUp : TrendingDown}
            tone={netAmount >= 0 ? 'good' : 'critical'}
            valueTone={netAmount >= 0 ? 'positive' : 'negative'}
            small
          />
          <StatCard
            label="Budget remaining"
            value={formatMoney(finance.remaining_budget, currency)}
            meta={
              toNumber(finance.initial_budget) > 0
                ? `${formatPercent(finance.budget_percentage_spent)} of ${formatMoney(
                    finance.initial_budget,
                    currency,
                  )} spent`
                : 'No active budget set'
            }
            icon={Wallet}
            tone={toNumber(finance.remaining_budget) < 0 ? 'critical' : 'brand'}
            valueTone={toNumber(finance.remaining_budget) < 0 ? 'negative' : ''}
            progress={toNumber(finance.initial_budget) > 0 ? finance.budget_percentage_spent : undefined}
            small
          />
        </div>
        <p style={{ fontSize: '0.78rem', color: 'var(--ink-muted)' }}>
          Budget remaining is a spending allowance, not profit. Net cash position (money actually
          received less money spent) is{' '}
          <strong style={{ color: toNumber(finance.net_cash_position) >= 0 ? 'inherit' : 'var(--critical)' }}>
            {formatMoney(finance.net_cash_position, currency)}
          </strong>
          .
        </p>
      </section>

      {/* -------------------------------------------------------- charts */}
      <div className="grid cols-2" style={{ marginBottom: 14 }}>
        <Card>
          <CardHead title="Bird population" hint="Birds on the farm at each month end" />
          <div className="card-body tight">
            <BirdPopulationChart data={charts.bird_population} />
          </div>
        </Card>
        <Card>
          <CardHead title="Mortality" hint="Deaths recorded over the last 30 days" />
          <div className="card-body tight">
            <MortalityChart data={charts.mortality} />
          </div>
        </Card>
      </div>

      {isManager && (
        <div className="grid cols-2" style={{ marginBottom: 14 }}>
          <Card>
            <CardHead title="Revenue vs expenses" hint={`By month, in ${currency}`} />
            <div className="card-body tight">
              <RevenueExpensesChart data={charts.revenue_vs_expenses} currency={currency} />
            </div>
          </Card>
          <Card>
            <CardHead title="Profit and loss trend" hint="Revenue less expenses, month by month" />
            <div className="card-body tight">
              <ProfitTrendChart data={charts.profit_trend} currency={currency} />
            </div>
          </Card>
        </div>
      )}

      <div className="grid cols-2" style={{ marginBottom: 14 }}>
        {isManager && (
          <Card>
            <CardHead title="Where the money goes" hint="Expenses by category">
              <Link to="/expenses" className="btn ghost sm">
                All expenses <ArrowRight size={14} />
              </Link>
            </CardHead>
            <div className="card-body tight">
              <ExpenseBreakdownChart data={charts.expenses_by_category} currency={currency} />
            </div>
          </Card>
        )}
        <Card>
          <CardHead title="Feed purchased vs consumed" hint="Bags per month" />
          <div className="card-body tight">
            <FeedUsageChart data={charts.feed_usage} />
          </div>
        </Card>
      </div>

      {/* ------------------------------------------- activity and alerts */}
      <div className="grid cols-2">
        <Card>
          <CardHead title="Recent farm activity" hint="The last actions recorded by your team" />
          {activity.length === 0 ? (
            <EmptyState icon={Bell} title="Nothing recorded yet" message="Actions will appear here as your team uses the system." />
          ) : (
            <div className="table-wrap">
              <table className="data">
                <caption className="visually-hidden">Recent farm activity</caption>
                <thead>
                  <tr>
                    <th scope="col">What happened</th>
                    <th scope="col">Who</th>
                    <th scope="col">When</th>
                  </tr>
                </thead>
                <tbody>
                  {activity.map((entry) => (
                    <tr key={entry.id}>
                      <td className="wrap">{entry.description}</td>
                      <td>{entry.user_display || 'System'}</td>
                      <td>{formatRelative(entry.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card>
          <CardHead title="Alerts needing attention" hint="Unread warnings raised automatically">
            <Link to="/notifications" className="btn ghost sm">
              All notifications <ArrowRight size={14} />
            </Link>
          </CardHead>
          {alerts.length === 0 ? (
            <EmptyState
              icon={CheckCircle2}
              title="Nothing needs your attention"
              message="Feed stock, mortality and budget levels are all within their thresholds."
            />
          ) : (
            <div className="alert-list">
              {alerts.map((alert) => {
                const Icon = ALERT_ICONS[alert.severity] || Info
                return (
                  <div className="alert-item" key={alert.id}>
                    <Icon
                      size={18}
                      className={`alert-icon ${alert.severity.toLowerCase()}`}
                      aria-hidden="true"
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <h4>{alert.title}</h4>
                      <p>{alert.message}</p>
                      <time dateTime={alert.created_at}>{formatRelative(alert.created_at)}</time>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </Card>
      </div>
    </>
  )
}
