import { useCallback, useEffect, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'

import Sidebar from './Sidebar'
import Topbar from './Topbar'
import { notificationsApi } from '../api/endpoints'
import { useAuth } from '../contexts/AuthContext'

export default function AppLayout() {
  const { user } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem('ejc.sidebar') === 'collapsed',
  )
  const [mobileOpen, setMobileOpen] = useState(false)
  const [unread, setUnread] = useState(0)

  useEffect(() => {
    localStorage.setItem('ejc.sidebar', collapsed ? 'collapsed' : 'expanded')
  }, [collapsed])

  useEffect(() => setMobileOpen(false), [location.pathname])

  const loadUnread = useCallback(() => {
    if (!user) return
    notificationsApi
      .count()
      .then((data) => setUnread(data.unread))
      .catch(() => {})
  }, [user])

  // Refresh the badge on navigation and on a slow poll, so alerts raised by
  // another user still surface without a page reload.
  useEffect(() => {
    loadUnread()
  }, [loadUnread, location.pathname])

  useEffect(() => {
    const timer = setInterval(loadUnread, 60_000)
    return () => clearInterval(timer)
  }, [loadUnread])

  return (
    <div className="app-shell">
      <Sidebar
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed((value) => !value)}
        mobileOpen={mobileOpen}
        onNavigate={() => setMobileOpen(false)}
        unreadCount={unread}
      />
      {mobileOpen && (
        <button
          type="button"
          className="scrim"
          aria-label="Close navigation menu"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <div className={`main-area ${collapsed ? 'collapsed' : ''}`.trim()}>
        <Topbar
          onOpenMobileNav={() => setMobileOpen(true)}
          unreadCount={unread}
          onSearch={(query) => {
            if (query.trim()) navigate(`/birds?q=${encodeURIComponent(query.trim())}`)
          }}
        />
        <main className="page">
          <Outlet context={{ refreshNotifications: loadUnread }} />
        </main>
      </div>
    </div>
  )
}
