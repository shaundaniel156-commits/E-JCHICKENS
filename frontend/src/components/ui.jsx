/**
 * The shared UI primitives. Every page composes these rather than restyling
 * buttons, cards and form fields of its own.
 */
import { useEffect, useId, useRef } from 'react'
import { AlertTriangle, Loader2, X } from 'lucide-react'

/* ------------------------------------------------------------------ card */

export function Card({ children, className = '', ...rest }) {
  return (
    <section className={`card ${className}`} {...rest}>
      {children}
    </section>
  )
}

export function CardHead({ title, hint, children, as: Heading = 'h3' }) {
  return (
    <header className="card-head">
      <div style={{ minWidth: 0 }}>
        <Heading>{title}</Heading>
        {hint && <p className="hint">{hint}</p>}
      </div>
      {children && <div className="row">{children}</div>}
    </header>
  )
}

/* ---------------------------------------------------------------- button */

export function Button({
  children,
  variant = 'primary',
  size,
  loading = false,
  icon: Icon,
  type = 'button',
  className = '',
  disabled,
  ...rest
}) {
  const variantClass = variant === 'primary' ? '' : variant
  return (
    <button
      type={type}
      className={`btn ${variantClass} ${size === 'sm' ? 'sm' : ''} ${className}`.trim()}
      disabled={disabled || loading}
      {...rest}
    >
      {loading ? (
        <Loader2 size={16} className="spin" style={{ animation: 'spin 0.7s linear infinite' }} />
      ) : (
        Icon && <Icon size={16} aria-hidden="true" />
      )}
      {children}
    </button>
  )
}

/* ----------------------------------------------------------------- badge */

const STATUS_TONES = {
  ACTIVE: 'good',
  SOLD_OUT: 'info',
  CLOSED: '',
  PAID: 'good',
  PARTIAL: 'warning',
  UNPAID: 'critical',
  CANCELLED: '',
  SICK: 'warning',
  UNDER_TREATMENT: 'info',
  RECOVERED: 'good',
  CRITICAL: 'critical',
  ADMIN: 'critical',
  MANAGER: 'info',
  STAFF: '',
}

export function Badge({ children, tone, status, icon: Icon }) {
  const resolved = tone ?? (status ? STATUS_TONES[status] ?? '' : '')
  return (
    <span className={`badge ${resolved}`}>
      {Icon && <Icon size={12} aria-hidden="true" />}
      {children}
    </span>
  )
}

/* ------------------------------------------------------------------ form */

export function Field({
  label,
  name,
  error,
  help,
  required,
  children,
  className = '',
  span2 = false,
}) {
  const generated = useId()
  const id = name || generated
  return (
    <div className={`field ${span2 ? 'span-2' : ''} ${className}`.trim()}>
      {label && (
        <label htmlFor={id}>
          {label} {required && <span className="required" aria-hidden="true">*</span>}
        </label>
      )}
      {typeof children === 'function' ? children({ id, invalid: Boolean(error) }) : children}
      {error && (
        <span className="error" role="alert">
          {error}
        </span>
      )}
      {!error && help && <span className="help">{help}</span>}
    </div>
  )
}

export function Input({ error, prefix, ...rest }) {
  if (prefix) {
    return (
      <span className="input-prefix">
        <span aria-hidden="true">{prefix}</span>
        <input aria-invalid={error ? 'true' : undefined} {...rest} />
      </span>
    )
  }
  return <input aria-invalid={error ? 'true' : undefined} {...rest} />
}

export function Select({ options = [], placeholder, error, children, ...rest }) {
  return (
    <select aria-invalid={error ? 'true' : undefined} {...rest}>
      {placeholder && <option value="">{placeholder}</option>}
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
      {children}
    </select>
  )
}

export function TextArea({ error, ...rest }) {
  return <textarea aria-invalid={error ? 'true' : undefined} {...rest} />
}

/* ----------------------------------------------------------------- modal */

export function Modal({ open, title, hint, onClose, children, footer, size = '' }) {
  const dialogRef = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    const onKeyDown = (event) => {
      if (event.key === 'Escape') onClose?.()
    }
    document.addEventListener('keydown', onKeyDown)
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    dialogRef.current?.focus()
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = previousOverflow
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose?.()
      }}
    >
      <div
        className={`modal ${size}`.trim()}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        ref={dialogRef}
        tabIndex={-1}
      >
        <header className="modal-head">
          <div style={{ minWidth: 0 }}>
            <h2 style={{ fontSize: '1.05rem' }}>{title}</h2>
            {hint && <p className="hint">{hint}</p>}
          </div>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </header>
        <div className="modal-body">{children}</div>
        {footer && <footer className="modal-foot">{footer}</footer>}
      </div>
    </div>
  )
}

export function ConfirmDialog({
  open,
  title = 'Are you sure?',
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  destructive = true,
  loading = false,
  onConfirm,
  onClose,
}) {
  return (
    <Modal
      open={open}
      title={title}
      onClose={onClose}
      size="sm"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button variant={destructive ? 'danger' : 'primary'} onClick={onConfirm} loading={loading}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      <div className="row" style={{ alignItems: 'flex-start', flexWrap: 'nowrap', gap: 12 }}>
        <AlertTriangle
          size={22}
          style={{ color: 'var(--warning)', flexShrink: 0, marginTop: 2 }}
          aria-hidden="true"
        />
        <p style={{ fontSize: '0.9rem', color: 'var(--ink-2)' }}>{message}</p>
      </div>
    </Modal>
  )
}

/* ---------------------------------------------------------------- states */

export function EmptyState({ icon: Icon, title, message, action }) {
  return (
    <div className="empty-state">
      {Icon && (
        <div className="icon">
          <Icon size={26} aria-hidden="true" />
        </div>
      )}
      <h3>{title}</h3>
      {message && <p>{message}</p>}
      {action}
    </div>
  )
}

export function ErrorState({ error, onRetry, compact = false }) {
  const message =
    error?.message || 'Something went wrong while loading this page. Please try again.'
  return (
    <div className="error-state" role="alert">
      <AlertTriangle size={20} style={{ color: 'var(--critical)', flexShrink: 0 }} aria-hidden="true" />
      <div style={{ flex: 1 }}>
        {!compact && <h4>We could not load this</h4>}
        <p>{message}</p>
      </div>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  )
}

export function Spinner({ label = 'Loading…' }) {
  return (
    <div className="loading-page">
      <span className="spinner" aria-hidden="true" />
      <span style={{ fontSize: '0.88rem' }}>{label}</span>
    </div>
  )
}

export function SkeletonRows({ rows = 5, height = 38 }) {
  return (
    <div className="stack" style={{ gap: 8, padding: 14 }} aria-hidden="true">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="skeleton" style={{ height }} />
      ))}
    </div>
  )
}

export function SkeletonCards({ count = 4, height = 104 }) {
  return (
    <div className="grid cols-4" aria-hidden="true">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="skeleton" style={{ height, borderRadius: 'var(--radius-lg)' }} />
      ))}
    </div>
  )
}

/* ------------------------------------------------------------ page header */

export function PageHeader({ title, subtitle, children }) {
  return (
    <div className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="subtitle">{subtitle}</p>}
      </div>
      {children && <div className="page-header-actions">{children}</div>}
    </div>
  )
}

/* ------------------------------------------------------------- pagination */

export function Pagination({ meta, page, onPage, pageSize, onPageSize }) {
  const pages = meta?.pages ?? 0
  const total = meta?.total ?? 0
  if (!total) return null

  const from = (page - 1) * pageSize + 1
  const to = Math.min(page * pageSize, total)

  const windowed = []
  const start = Math.max(1, Math.min(page - 2, pages - 4))
  for (let index = start; index < start + 5 && index <= pages; index += 1) windowed.push(index)

  return (
    <div className="pagination">
      <span>
        Showing <strong>{from}</strong>–<strong>{to}</strong> of <strong>{total}</strong>
      </span>
      <div className="row" style={{ gap: 12 }}>
        {onPageSize && (
          <label className="row" style={{ gap: 6, fontSize: '0.8rem' }}>
            Rows
            <select
              value={pageSize}
              onChange={(event) => onPageSize(Number(event.target.value))}
              style={{
                padding: '4px 6px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-strong)',
                background: 'var(--surface)',
                color: 'var(--ink)',
              }}
              aria-label="Rows per page"
            >
              {[10, 20, 50, 100].map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
        )}
        <div className="pagination-controls">
          <button
            type="button"
            className="page-btn"
            onClick={() => onPage(page - 1)}
            disabled={page <= 1}
          >
            Prev
          </button>
          {windowed.map((number) => (
            <button
              key={number}
              type="button"
              className={`page-btn ${number === page ? 'active' : ''}`}
              onClick={() => onPage(number)}
              aria-current={number === page ? 'page' : undefined}
            >
              {number}
            </button>
          ))}
          <button
            type="button"
            className="page-btn"
            onClick={() => onPage(page + 1)}
            disabled={page >= pages}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  )
}

/* -------------------------------------------------------------- progress */

export function Progress({ value, tone }) {
  const clamped = Math.max(0, Math.min(100, Number(value) || 0))
  const resolved = tone || (clamped >= 100 ? 'critical' : clamped >= 80 ? 'warning' : '')
  return (
    <div
      className={`progress ${resolved}`}
      role="progressbar"
      aria-valuenow={Math.round(clamped)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div style={{ width: `${clamped}%` }} />
    </div>
  )
}
