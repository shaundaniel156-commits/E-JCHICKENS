import { Activity as ActivityIcon } from 'lucide-react'

import { activityApi } from '../api/endpoints'
import DataTable from '../components/DataTable'
import { FilterSelect, SearchBox } from '../components/Filters'
import { Badge, Card, EmptyState, PageHeader } from '../components/ui'
import { useListQuery } from '../hooks/useListQuery'
import { formatDateTime, titleCase } from '../utils/format'

const ACTIONS = [
  { value: 'LOGIN', label: 'Sign in' },
  { value: 'LOGOUT', label: 'Sign out' },
  { value: 'CREATE', label: 'Created' },
  { value: 'UPDATE', label: 'Updated' },
  { value: 'DELETE', label: 'Deleted / reversed' },
  { value: 'RESTORE', label: 'Restored' },
]

const MODULES = [
  { value: 'auth', label: 'Sign in / out' },
  { value: 'birds', label: 'Birds' },
  { value: 'mortality', label: 'Mortality' },
  { value: 'health', label: 'Health' },
  { value: 'feed', label: 'Feed' },
  { value: 'expenses', label: 'Expenses' },
  { value: 'sales', label: 'Sales' },
  { value: 'budgets', label: 'Budgets' },
  { value: 'users', label: 'Users' },
  { value: 'settings', label: 'Settings' },
  { value: 'profile', label: 'Profile' },
]

const ACTION_TONES = { CREATE: 'good', UPDATE: 'info', DELETE: 'critical', RESTORE: 'warning' }

export default function Activity() {
  const query = useListQuery(activityApi.list, { pageSize: 25 })

  const columns = [
    { key: 'created_at', header: 'When', render: (row) => formatDateTime(row.created_at) },
    { key: 'user_display', header: 'Who', render: (row) => row.user_display || 'System' },
    {
      key: 'action',
      header: 'Action',
      render: (row) => <Badge tone={ACTION_TONES[row.action] || ''}>{titleCase(row.action)}</Badge>,
    },
    { key: 'module', header: 'Module', render: (row) => titleCase(row.module) },
    { key: 'description', header: 'What happened', className: 'wrap' },
    { key: 'ip_address', header: 'IP address', render: (row) => row.ip_address || '—' },
  ]

  return (
    <>
      <PageHeader
        title="Activity log"
        subtitle="A record of every important action taken in the system, for administrators."
      />

      <Card>
        <div className="toolbar">
          <SearchBox value={query.search} onChange={query.onSearch} placeholder="Search the log…" />
          <FilterSelect
            label="Module"
            value={query.filters.module}
            onChange={(value) => query.setFilter('module', value)}
            options={MODULES}
            placeholder="All modules"
          />
          <FilterSelect
            label="Action"
            value={query.filters.action}
            onChange={(value) => query.setFilter('action', value)}
            options={ACTIONS}
            placeholder="All actions"
          />
        </div>

        <DataTable
          columns={columns}
          rows={query.items}
          loading={query.loading}
          error={query.error}
          onRetry={query.reload}
          meta={query.meta}
          page={query.page}
          onPage={query.setPage}
          pageSize={query.pageSize}
          onPageSize={query.setPageSize}
          caption="Activity log"
          empty={
            <EmptyState
              icon={ActivityIcon}
              title="Nothing logged yet"
              message="Actions are recorded here as your team uses the system."
            />
          }
        />
      </Card>
    </>
  )
}
