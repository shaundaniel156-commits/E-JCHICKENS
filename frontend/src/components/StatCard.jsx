import { Progress } from './ui'

/**
 * A stat tile: when the story is one number, the number is the chart.
 * `tone` drives the icon chip and the value colour (green = good, red = bad).
 */
export default function StatCard({
  label,
  value,
  meta,
  icon: Icon,
  tone = '',
  valueTone = '',
  progress,
  progressTone,
  small = false,
  footer,
}) {
  return (
    <article className="card stat-card">
      <div className="top">
        <span className="label">{label}</span>
        {Icon && (
          <span className={`stat-icon ${tone}`.trim()} aria-hidden="true">
            <Icon size={18} />
          </span>
        )}
      </div>
      <div className={`value ${small ? 'sm' : ''} ${valueTone}`.trim()}>{value}</div>
      {progress !== undefined && <Progress value={progress} tone={progressTone} />}
      {meta && <div className="meta">{meta}</div>}
      {footer}
    </article>
  )
}
