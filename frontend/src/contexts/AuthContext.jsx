import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { tokenStore } from '../api/client'
import { authApi } from '../api/endpoints'

const AuthContext = createContext(null)

/** Role capabilities, mirroring the backend's `require_roles` dependencies. */
const CAPABILITIES = {
  ADMIN: ['*'],
  MANAGER: [
    'birds.manage',
    'feed.manage',
    'health.manage',
    'mortality.manage',
    'sales.manage',
    'expenses.manage',
    'finance.view',
    'reports.view',
  ],
  STAFF: ['birds.record', 'feed.record', 'health.record', 'mortality.record'],
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => tokenStore.user)
  const [loading, setLoading] = useState(() => Boolean(tokenStore.access))

  // Revalidate the stored session on boot: a token in localStorage proves
  // nothing until the server agrees.
  useEffect(() => {
    let cancelled = false
    if (!tokenStore.access) {
      setLoading(false)
      return undefined
    }
    authApi
      .me()
      .then((profile) => {
        if (cancelled) return
        setUser(profile)
        tokenStore.saveUser(profile)
      })
      .catch(() => {
        if (cancelled) return
        tokenStore.clear()
        setUser(null)
      })
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [])

  // The API client raises this when a refresh fails.
  useEffect(() => {
    const onExpired = () => setUser(null)
    window.addEventListener('ejc:session-expired', onExpired)
    return () => window.removeEventListener('ejc:session-expired', onExpired)
  }, [])

  const login = useCallback(async (credentials) => {
    const response = await authApi.login(credentials)
    tokenStore.save(response.tokens, response.user)
    setUser(response.user)
    return response.user
  }, [])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } catch {
      /* signing out locally matters more than the server acknowledging it */
    }
    tokenStore.clear()
    setUser(null)
  }, [])

  const refreshUser = useCallback(async () => {
    const profile = await authApi.me()
    setUser(profile)
    tokenStore.saveUser(profile)
    return profile
  }, [])

  const value = useMemo(() => {
    const role = user?.role
    const abilities = CAPABILITIES[role] || []
    const can = (capability) => abilities.includes('*') || abilities.includes(capability)
    return {
      user,
      loading,
      login,
      logout,
      refreshUser,
      setUser,
      role,
      isAdmin: role === 'ADMIN',
      isManager: role === 'ADMIN' || role === 'MANAGER',
      can,
    }
  }, [user, loading, login, logout, refreshUser])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside an AuthProvider')
  return context
}
