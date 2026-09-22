import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { AlertTriangle, Bell, CheckCheck, CheckCircle2, Info, Trash2 } from 'lucide-react'

import { notificationsApi } from '../api/endpoints'
import { FilterSelect } from '../components/Filters'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  PageHeader,
  Pagination,
  SkeletonRows,
} from '../components/ui'
import { useToast } from '../contexts/ToastContext'
import { useListQuery } from '../hooks/useListQuery'
import { formatRelative, titleCase } from '../utils/format'

const ICONS = { CRITICAL: AlertTriangle, WARNING: AlertTriangle, SUCCESS: CheckCircle2, INFO: Info }
const TONES = { CRITICAL: 'critical', WARNING: 'warning', SUCCESS: 'good', INFO: 'info' }

const TYPES = [
  { value: 'FEED_LOW', label: 'Feed running low' },
  { value: 'FEED_UPDATED', label: 'Feed stock updated' },
  { value: 'MORTALITY_HIGH', label: 'High mortality' },
  { value: 'BUDGET_WARNING', label: 'Budget warning' },
  { value: 'BUDGET_EXCEEDED', label: 'Budget exceeded' },
  { value: 'HEALTH_ALERT', label: 'Birds need attention' },
  { value: 'SALE_COMPLETED', label: 'Sale completed' },
  { value: 'BIRDS_ADDED', label: 'Birds added' },
]

export default function Notifications() {
  const toast = useToast()
  const outlet = useOutletContext()
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [busy, setBusy] = useState(false)

  const query = useListQuery(
    (params) => notificationsApi.list({ ...params, unread_only: unreadOnly || undefined }),
    { pageSize: 20 },
  )

  const refresh = () => {
    query.reload()
    outlet?.refreshNotifications?.()
  }

  const markRead = async (id) => {
    try {
      await notificationsApi.markRead(id)
      refresh()
    } catch (error) {
      toast.error(error.message)
    }
  }

  const markAll = async () => {
    setBusy(true)
    try {
      const response = await notificationsApi.markAllRead()
      toast.success(response.message)
      refresh()
    } catch (error) {
      toast.error(error.message)
    } finally {
      setBusy(false)
    }
  }

  const dismiss = async (id) => {
    try {
      await notificationsApi.remove(id)
      refresh()
    } catch (error) {
      toast.error(error.message)
    }
  }

  return (
    <>
      <PageHeader
        title="Notifications"
        subtitle="Alerts the system raises for you — low feed, high mortality, budget limits and completed transactions."
      >
        <Button variant="secondary" icon={CheckCheck} onClick={markAll} loading={busy}>
          Mark all as read
        </Button>
      </PageHeader>

      <Card>
        <div className="toolbar">
          <FilterSelect
            label="Type"
            value={query.filters.type}
            onChange={(value) => query.setFilter('type', value)}
            options={TYPES}
            placeholder="All types"
          />
          <label className="field" style={{ minWidth: 150 }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--ink-2)' }}>Show</span>
            <select
              value={unreadOnly ? 'unread' : 'all'}
              onChange={(event) => {
                setUnreadOnly(event.target.value === 'unread')
                query.setPage(1)
                setTimeout(query.reload, 0)
              }}
            >
              <option value="all">Everything</option>
              <option value="unread">Unread only</option>
            </select>
          </label>
        </div>

        {query.error ? (
          <div style={{ padding: 14 }}>
            <ErrorState error={query.error} onRetry={query.reload} />
          </div>
        ) : query.loading && !query.items.length ? (
          <SkeletonRows rows={6} />
        ) : query.items.length === 0 ? (
          <EmptyState
            icon={Bell}
            title={unreadOnly ? 'Nothing unread' : 'No notifications yet'}
            message={
              unreadOnly
                ? 'You are all caught up.'
                : 'Alerts will appear here as the farm records build up — for example when feed runs low or a budget is nearly spent.'
            }
          />
        ) : (
          <>
            <div className="alert-list">
              {query.items.map((notification) => {
                const Icon = ICONS[notification.severity] || Info
                return (
                  <div
                    className={`alert-item ${notification.is_read ? '' : 'unread'}`}
                    key={notification.id}
                  >
                    <Icon
                      size={19}
                      className={`alert-icon ${notification.severity.toLowerCase()}`}
                      aria-hidden="true"
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div className="row" style={{ gap: 8 }}>
                        <h4>{notification.title}</h4>
                        <Badge tone={TONES[notification.severity]}>{titleCase(notification.severity)}</Badge>
                        {!notification.is_read && <Badge tone="info">New</Badge>}
                      </div>
                      <p>{notification.message}</p>
                      <time dateTime={notification.created_at}>
                        {formatRelative(notification.created_at)} · {titleCase(notification.type)}
                      </time>
                    </div>
                    <div className="row-actions">
                      {!notification.is_read && (
                        <button
                          type="button"
                          className="icon-btn"
                          title="Mark as read"
                          aria-label={`Mark “${notification.title}” as read`}
                          onClick={() => markRead(notification.id)}
                        >
                          <CheckCircle2 size={16} />
                        </button>
                      )}
                      <button
                        type="button"
                        className="icon-btn"
                        title="Dismiss"
                        aria-label={`Dismiss “${notification.title}”`}
                        onClick={() => dismiss(notification.id)}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
            <Pagination
              meta={query.meta}
              page={query.page}
              onPage={query.setPage}
              pageSize={query.pageSize}
              onPageSize={query.setPageSize}
            />
          </>
        )}
      </Card>
    </>
  )
}
