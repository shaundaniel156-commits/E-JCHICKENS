import { NavLink } from 'react-router-dom'
import {
  Activity as ActivityIcon,
  Bell,
  ChevronLeft,
  ChevronRight,
  Coins,
  Egg,
  FileBarChart,
  HeartPulse,
  LayoutDashboard,
  Receipt,
  Settings as SettingsIcon,
  ShoppingCart,
  Skull,
  Users as UsersIcon,
  Wheat,
} from 'lucide-react'

import Logo from '../components/Logo'
import { useAuth } from '../contexts/AuthContext'

const NAV = [
  {
    section: 'Overview',
    items: [{ to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true }],
  },
  {
    section: 'Farm',
    items: [
      { to: '/birds', label: 'Birds', icon: Egg },
      { to: '/feed', label: 'Feed', icon: Wheat },
      { to: '/health', label: 'Health', icon: HeartPulse },
      { to: '/mortality', label: 'Mortality', icon: Skull },
    ],
  },
  {
    section: 'Money',
    items: [
      { to: '/sales', label: 'Sales', icon: ShoppingCart, roles: ['ADMIN', 'MANAGER'] },
      { to: '/expenses', label: 'Expenses', icon: Receipt, roles: ['ADMIN', 'MANAGER'] },
      { to: '/finance', label: 'Finance', icon: Coins, roles: ['ADMIN', 'MANAGER'] },
      { to: '/reports', label: 'Reports', icon: FileBarChart, roles: ['ADMIN', 'MANAGER'] },
    ],
  },
  {
    section: 'Administration',
    items: [
      { to: '/notifications', label: 'Notifications', icon: Bell, badge: 'notifications' },
      { to: '/users', label: 'Users', icon: UsersIcon, roles: ['ADMIN'] },
      { to: '/activity', label: 'Activity log', icon: ActivityIcon, roles: ['ADMIN'] },
      { to: '/settings', label: 'Settings', icon: SettingsIcon },
    ],
  },
]

export default function Sidebar({ collapsed, onToggleCollapse, mobileOpen, onNavigate, unreadCount }) {
  const { user } = useAuth()

  const visible = NAV.map((group) => ({
    ...group,
    items: group.items.filter((item) => !item.roles || item.roles.includes(user?.role)),
  })).filter((group) => group.items.length > 0)

  return (
    <aside
      className={`sidebar ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`.trim()}
      aria-label="Main navigation"
    >
      <div className="sidebar-brand">
        <Logo size={30} />
        {!collapsed && (
          <span className="sidebar-brand-text">
            <strong>E&amp;J&apos;s CHICKENS</strong>
            <span>Farm management</span>
          </span>
        )}
      </div>

      <nav className="sidebar-nav">
        {visible.map((group) => (
          <div key={group.section}>
            <div className="sidebar-section">{collapsed ? '•' : group.section}</div>
            {group.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                onClick={onNavigate}
                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                title={collapsed ? item.label : undefined}
              >
                <item.icon size={18} aria-hidden="true" />
                <span>{item.label}</span>
                {item.badge === 'notifications' && unreadCount > 0 && (
                  <span className="nav-badge">{unreadCount > 99 ? '99+' : unreadCount}</span>
                )}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <button type="button" className="sidebar-collapse-btn" onClick={onToggleCollapse}>
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          {!collapsed && <span>Collapse menu</span>}
        </button>
      </div>
    </aside>
  )
}
