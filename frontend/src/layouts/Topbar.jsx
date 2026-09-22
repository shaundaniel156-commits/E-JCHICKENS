import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Bell,
  LogOut,
  Menu,
  Monitor,
  Moon,
  Search,
  Settings as SettingsIcon,
  Sun,
  User as UserIcon,
} from 'lucide-react'

import { useAuth } from '../contexts/AuthContext'
import { useSettings } from '../contexts/SettingsContext'
import { initials, titleCase } from '../utils/format'

const THEME_ICONS = { system: Monitor, light: Sun, dark: Moon }
const THEME_ORDER = ['system', 'light', 'dark']

export default function Topbar({ onOpenMobileNav, unreadCount, onSearch }) {
  const { user, logout } = useAuth()
  const { theme, setTheme } = useSettings()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const [query, setQuery] = useState('')
  const menuRef = useRef(null)

  useEffect(() => {
    if (!menuOpen) return undefined
    const onClick = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [menuOpen])

  const ThemeIcon = THEME_ICONS[theme] || Monitor

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  const today = new Date().toLocaleDateString('en-GB', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })

  return (
    <header className="topbar">
      <button
        type="button"
        className="icon-btn"
        onClick={onOpenMobileNav}
        aria-label="Open navigation menu"
        style={{ display: 'none' }}
        data-mobile-only
      >
        <Menu size={20} />
      </button>
      {/* The button above is shown only on small screens via the style tag below. */}
      <style>{`@media (max-width: 860px) { [data-mobile-only] { display: inline-flex !important; } }`}</style>

      <form
        className="topbar-search"
        onSubmit={(event) => {
          event.preventDefault()
          onSearch?.(query)
        }}
        role="search"
      >
        <Search size={15} aria-hidden="true" />
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search batches, sales, expenses…"
          aria-label="Search the farm records"
        />
      </form>

      <div className="topbar-spacer" />
      <span className="topbar-date">{today}</span>

      <button
        type="button"
        className="icon-btn"
        onClick={() => setTheme(THEME_ORDER[(THEME_ORDER.indexOf(theme) + 1) % THEME_ORDER.length])}
        aria-label={`Colour theme: ${theme}. Click to change.`}
        title={`Theme: ${titleCase(theme)}`}
      >
        <ThemeIcon size={18} />
      </button>

      <Link
        to="/notifications"
        className="icon-btn"
        aria-label={`Notifications${unreadCount ? `, ${unreadCount} unread` : ''}`}
      >
        <Bell size={19} />
        {unreadCount > 0 && <span className="dot">{unreadCount > 99 ? '99+' : unreadCount}</span>}
      </Link>

      <div className="user-menu" ref={menuRef}>
        <button
          type="button"
          className="user-menu-trigger"
          onClick={() => setMenuOpen((open) => !open)}
          aria-haspopup="menu"
          aria-expanded={menuOpen}
        >
          <span className="avatar">{initials(user?.full_name)}</span>
          <span className="user-menu-text" style={{ textAlign: 'left' }}>
            <span className="user-menu-name">{user?.full_name}</span>
            <br />
            <span className="user-menu-role">{titleCase(user?.role || '')}</span>
          </span>
        </button>

        {menuOpen && (
          <div className="dropdown" role="menu">
            <div className="dropdown-header">
              <div style={{ fontWeight: 650, fontSize: '0.88rem' }}>{user?.full_name}</div>
              <div style={{ fontSize: '0.76rem', color: 'var(--ink-muted)' }}>{user?.email}</div>
            </div>
            <Link to="/profile" className="dropdown-item" role="menuitem" onClick={() => setMenuOpen(false)}>
              <UserIcon size={15} /> My profile
            </Link>
            <Link to="/settings" className="dropdown-item" role="menuitem" onClick={() => setMenuOpen(false)}>
              <SettingsIcon size={15} /> Settings
            </Link>
            <button type="button" className="dropdown-item danger" role="menuitem" onClick={handleLogout}>
              <LogOut size={15} /> Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
