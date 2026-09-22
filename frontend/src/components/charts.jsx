/**
 * Dashboard charts.
 *
 * Conventions applied throughout (and why):
 *  - one y-axis per chart, never two scales on one plot;
 *  - series colours come from CSS custom properties, so light/dark swap in one
 *    place and the palette stays the validated, colour-blind-safe set;
 *  - a legend whenever there are two or more series, none for a single series
 *    (the card title already names it);
 *  - thin marks: bars capped at 24px with a 4px rounded data-end, 2px lines,
 *    solid hairline gridlines, and a 2px surface ring on hover markers;
 *  - every chart ships a hover tooltip, and every value is also reachable in
 *    the matching table or report.
 */
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { EmptyState } from './ui'
import {
  compactAmount,
  formatMoney,
  formatNumber,
  formatQuantity,
  toNumber,
} from '../utils/format'

const AXIS = {
  stroke: 'var(--axis)',
  tick: { fill: 'var(--axis-ink)', fontSize: 11 },
  tickLine: false,
}

const GRID = { stroke: 'var(--grid)', strokeWidth: 1, vertical: false }

/** Shared frame: the height includes the x-axis band so nothing is clipped. */
function ChartFrame({ children, height = 250, legend }) {
  return (
    <div className="chart-frame">
      {legend}
      <ResponsiveContainer width="100%" height={height}>
        {children}
      </ResponsiveContainer>
    </div>
  )
}

function Legend({ items, unit }) {
  return (
    <div className="chart-legend">
      {items.map((item) => (
        <span className="key" key={item.label}>
          <span className="swatch" style={{ background: item.color }} aria-hidden="true" />
          {item.label}
        </span>
      ))}
      {unit && <span style={{ marginLeft: 'auto', color: 'var(--ink-muted)' }}>{unit}</span>}
    </div>
  )
}

function UnitNote({ children }) {
  return (
    <div className="chart-legend" style={{ justifyContent: 'flex-end' }}>
      <span style={{ color: 'var(--ink-muted)' }}>{children}</span>
    </div>
  )
}

function TooltipBox({ label, rows }) {
  return (
    <div className="chart-tooltip">
      <div className="t-label">{label}</div>
      {rows.map((row) => (
        <div className="t-row" key={row.name}>
          <span className="name">
            {row.color && (
              <span
                className="swatch"
                style={{ width: 9, height: 9, borderRadius: 2, background: row.color }}
                aria-hidden="true"
              />
            )}
            {row.name}
          </span>
          <span className="val">{row.value}</span>
        </div>
      ))}
    </div>
  )
}

function ChartEmpty({ message }) {
  return (
    <div style={{ padding: '30px 16px', textAlign: 'center', color: 'var(--ink-muted)', fontSize: '0.85rem' }}>
      {message}
    </div>
  )
}

/* ================================================================ population */

export function BirdPopulationChart({ data = [], height = 250 }) {
  if (!data.length) return <ChartEmpty message="Add a bird batch to see the flock trend." />

  return (
    <ChartFrame height={height}>
      <LineChart data={data} margin={{ top: 8, right: 14, bottom: 4, left: 4 }}>
        <CartesianGrid {...GRID} />
        <XAxis dataKey="period" {...AXIS} />
        <YAxis {...AXIS} width={52} tickFormatter={(value) => formatNumber(value)} />
        <Tooltip
          cursor={{ stroke: 'var(--axis)', strokeWidth: 1 }}
          content={({ active, payload, label }) =>
            active && payload?.length ? (
              <TooltipBox
                label={label}
                rows={[
                  { name: 'Birds on the farm', value: formatNumber(payload[0].value), color: 'var(--series-1)' },
                ]}
              />
            ) : null
          }
        />
        <Line
          type="monotone"
          dataKey="value"
          name="Birds"
          stroke="var(--series-1)"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          dot={false}
          activeDot={{ r: 5, strokeWidth: 2, stroke: 'var(--chart-surface)' }}
        />
      </LineChart>
    </ChartFrame>
  )
}

/* ================================================================= mortality */

export function MortalityChart({ data = [], height = 250 }) {
  if (!data.length) return <ChartEmpty message="No mortality has been recorded yet." />

  return (
    <ChartFrame height={height}>
      <BarChart data={data} margin={{ top: 8, right: 14, bottom: 4, left: 4 }} barCategoryGap={2}>
        <CartesianGrid {...GRID} />
        <XAxis dataKey="period" {...AXIS} interval="preserveStartEnd" />
        <YAxis {...AXIS} width={40} allowDecimals={false} />
        <Tooltip
          cursor={{ fill: 'var(--surface-3)' }}
          content={({ active, payload, label }) =>
            active && payload?.length ? (
              <TooltipBox
                label={label}
                rows={[{ name: 'Deaths', value: formatNumber(payload[0].value), color: 'var(--critical)' }]}
              />
            ) : null
          }
        />
        <Bar dataKey="value" name="Deaths" fill="var(--critical)" radius={[4, 4, 0, 0]} maxBarSize={24} />
      </BarChart>
    </ChartFrame>
  )
}

/* ========================================================= expenses by category */

/**
 * Magnitude by named row, so bar length carries the value and the row label
 * carries identity — one colour for every bar (a colour ramp here would just
 * re-encode length).
 */
export function ExpenseBreakdownChart({ data = [], currency = 'UGX', height = 262 }) {
  if (!data.length) return <ChartEmpty message="No expenses have been recorded for this period." />

  const rows = data.slice(0, 8).map((row) => ({
    category: row.category,
    amount: toNumber(row.amount),
    percentage: row.percentage,
    count: row.count,
  }))

  return (
    <ChartFrame
      height={Math.max(height, rows.length * 34 + 30)}
      legend={<UnitNote>Amounts in {currency}</UnitNote>}
    >
      <BarChart
        data={rows}
        layout="vertical"
        margin={{ top: 4, right: 78, bottom: 4, left: 4 }}
        barCategoryGap={4}
      >
        <CartesianGrid stroke="var(--grid)" strokeWidth={1} horizontal={false} />
        <XAxis type="number" {...AXIS} tickFormatter={compactAmount} />
        <YAxis type="category" dataKey="category" {...AXIS} width={104} />
        <Tooltip
          cursor={{ fill: 'var(--surface-3)' }}
          content={({ active, payload }) =>
            active && payload?.length ? (
              <TooltipBox
                label={payload[0].payload.category}
                rows={[
                  { name: 'Amount', value: formatMoney(payload[0].value, currency), color: 'var(--series-1)' },
                  { name: 'Share', value: `${payload[0].payload.percentage.toFixed(1)}%` },
                  { name: 'Entries', value: formatNumber(payload[0].payload.count) },
                ]}
              />
            ) : null
          }
        />
        <Bar
          dataKey="amount"
          name="Expenses"
          fill="var(--series-1)"
          radius={[0, 4, 4, 0]}
          maxBarSize={22}
          // The currency is stated once above the chart, so the direct labels
          // stay short — a label carrying "UGX" wraps onto two lines on a short bar.
          label={{
            position: 'right',
            fill: 'var(--ink-2)',
            fontSize: 11,
            formatter: compactAmount,
          }}
        />
      </BarChart>
    </ChartFrame>
  )
}

/* ======================================================= revenue vs expenses */

export function RevenueExpensesChart({ data = [], currency = 'UGX', height = 268 }) {
  if (!data.length) return <ChartEmpty message="Record a sale or an expense to see this comparison." />

  return (
    <ChartFrame
      height={height}
      legend={
        <Legend
          items={[
            { label: 'Revenue', color: 'var(--series-1)' },
            { label: 'Expenses', color: 'var(--series-2)' },
          ]}
          unit={`Amounts in ${currency}`}
        />
      }
    >
      <BarChart data={data} margin={{ top: 8, right: 14, bottom: 4, left: 4 }} barGap={2}>
        <CartesianGrid {...GRID} />
        <XAxis dataKey="period" {...AXIS} />
        <YAxis {...AXIS} width={48} tickFormatter={compactAmount} />
        <Tooltip
          cursor={{ fill: 'var(--surface-3)' }}
          content={({ active, payload, label }) =>
            active && payload?.length ? (
              <TooltipBox
                label={label}
                rows={payload.map((entry) => ({
                  name: entry.name,
                  value: formatMoney(entry.value, currency),
                  color: entry.color,
                }))}
              />
            ) : null
          }
        />
        <Bar dataKey="revenue" name="Revenue" fill="var(--series-1)" radius={[4, 4, 0, 0]} maxBarSize={22} />
        <Bar dataKey="expenses" name="Expenses" fill="var(--series-2)" radius={[4, 4, 0, 0]} maxBarSize={22} />
      </BarChart>
    </ChartFrame>
  )
}

/* ============================================================= profit trend */

/**
 * Profit and loss is a polarity, so the sign drives the colour: the status
 * tokens for good and critical, anchored to a zero baseline and always paired
 * with the signed value in the tooltip — never colour alone.
 */
export function ProfitTrendChart({ data = [], currency = 'UGX', height = 268 }) {
  if (!data.length) return <ChartEmpty message="Record sales and expenses to see the profit trend." />

  return (
    <ChartFrame
      height={height}
      legend={
        <Legend
          items={[
            { label: 'Profit (month in surplus)', color: 'var(--good)' },
            { label: 'Loss (month in deficit)', color: 'var(--critical)' },
          ]}
          unit={`Amounts in ${currency}`}
        />
      }
    >
      <BarChart data={data} margin={{ top: 8, right: 14, bottom: 4, left: 4 }} barCategoryGap={2}>
        <CartesianGrid {...GRID} />
        <XAxis dataKey="period" {...AXIS} />
        <YAxis {...AXIS} width={48} tickFormatter={compactAmount} />
        <ReferenceLine y={0} stroke="var(--axis)" strokeWidth={1} />
        <Tooltip
          cursor={{ fill: 'var(--surface-3)' }}
          content={({ active, payload, label }) => {
            if (!active || !payload?.length) return null
            const amount = toNumber(payload[0].value)
            return (
              <TooltipBox
                label={label}
                rows={[
                  {
                    name: amount >= 0 ? 'Profit' : 'Loss',
                    value: formatMoney(Math.abs(amount), currency),
                    color: amount >= 0 ? 'var(--good)' : 'var(--critical)',
                  },
                ]}
              />
            )
          }}
        />
        <Bar dataKey="profit" name="Profit or loss" radius={[4, 4, 0, 0]} maxBarSize={24}>
          {data.map((point, index) => (
            <Cell
              key={index}
              fill={toNumber(point.profit) >= 0 ? 'var(--good)' : 'var(--critical)'}
            />
          ))}
        </Bar>
      </BarChart>
    </ChartFrame>
  )
}

/* =============================================================== feed usage */

export function FeedUsageChart({ data = [], height = 262 }) {
  if (!data.length) return <ChartEmpty message="Record a feed purchase to see usage against stock." />

  return (
    <ChartFrame
      height={height}
      legend={
        <Legend
          items={[
            { label: 'Bags purchased', color: 'var(--series-1)' },
            { label: 'Bags consumed', color: 'var(--series-2)' },
          ]}
        />
      }
    >
      <BarChart data={data} margin={{ top: 8, right: 14, bottom: 4, left: 4 }} barGap={2}>
        <CartesianGrid {...GRID} />
        <XAxis dataKey="period" {...AXIS} />
        <YAxis {...AXIS} width={44} tickFormatter={(value) => formatNumber(value)} />
        <Tooltip
          cursor={{ fill: 'var(--surface-3)' }}
          content={({ active, payload, label }) =>
            active && payload?.length ? (
              <TooltipBox
                label={label}
                rows={payload.map((entry) => ({
                  name: entry.name,
                  value: formatQuantity(entry.value, 'bags'),
                  color: entry.color,
                }))}
              />
            ) : null
          }
        />
        <Bar dataKey="value" name="Purchased" fill="var(--series-1)" radius={[4, 4, 0, 0]} maxBarSize={22} />
        <Bar dataKey="secondary" name="Consumed" fill="var(--series-2)" radius={[4, 4, 0, 0]} maxBarSize={22} />
      </BarChart>
    </ChartFrame>
  )
}
