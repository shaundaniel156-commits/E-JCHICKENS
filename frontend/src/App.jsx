import { Navigate, Route, Routes, useLocation } from 'react-router-dom'

import AppLayout from './layouts/AppLayout'
import { Spinner } from './components/ui'
import { useAuth } from './contexts/AuthContext'
import Activity from './pages/Activity'
import Birds from './pages/Birds'
import Dashboard from './pages/Dashboard'
import Expenses from './pages/Expenses'
import Feed from './pages/Feed'
import Finance from './pages/Finance'
import Health from './pages/Health'
import Login from './pages/Login'
import Mortality from './pages/Mortality'
import NotFound from './pages/NotFound'
import Notifications from './pages/Notifications'
import Profile from './pages/Profile'
import Reports from './pages/Reports'
import Sales from './pages/Sales'
import Settings from './pages/Settings'
import Users from './pages/Users'

/** Blocks a route until the user is signed in, and optionally checks the role. */
function Protected({ children, roles }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) return <Spinner label="Checking your session…" />
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />
  return children
}

const MANAGEMENT = ['ADMIN', 'MANAGER']
const ADMIN_ONLY = ['ADMIN']

export default function App() {
  const { user, loading } = useAuth()

  return (
    <Routes>
      <Route
        path="/login"
        element={loading ? <Spinner /> : user ? <Navigate to="/" replace /> : <Login />}
      />

      <Route
        element={
          <Protected>
            <AppLayout />
          </Protected>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="birds" element={<Birds />} />
        <Route path="feed" element={<Feed />} />
        <Route path="health" element={<Health />} />
        <Route path="mortality" element={<Mortality />} />
        <Route
          path="sales"
          element={
            <Protected roles={MANAGEMENT}>
              <Sales />
            </Protected>
          }
        />
        <Route
          path="expenses"
          element={
            <Protected roles={MANAGEMENT}>
              <Expenses />
            </Protected>
          }
        />
        <Route
          path="finance"
          element={
            <Protected roles={MANAGEMENT}>
              <Finance />
            </Protected>
          }
        />
        <Route
          path="reports"
          element={
            <Protected roles={MANAGEMENT}>
              <Reports />
            </Protected>
          }
        />
        <Route path="notifications" element={<Notifications />} />
        <Route
          path="users"
          element={
            <Protected roles={ADMIN_ONLY}>
              <Users />
            </Protected>
          }
        />
        <Route
          path="activity"
          element={
            <Protected roles={ADMIN_ONLY}>
              <Activity />
            </Protected>
          }
        />
        <Route path="settings" element={<Settings />} />
        <Route path="profile" element={<Profile />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
