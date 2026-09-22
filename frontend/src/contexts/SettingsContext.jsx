import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { settingsApi } from '../api/endpoints'
import { useAuth } from './AuthContext'

const SettingsContext = createContext(null)

const FALLBACK = {
  farm_name: "E&J's CHICKENS",
  currency: 'UGX',
  date_format: 'DD/MM/YYYY',
  low_feed_threshold_bags: '5',
  high_mortality_rate_percent: '5',
  budget_warning_percent: '80',
  notifications_enabled: true,
}

/** Farm settings + the colour-scheme preference, shared across every page. */
export function SettingsProvider({ children }) {
  const { user } = useAuth()
  const [settings, setSettings] = useState(FALLBACK)
  const [theme, setThemeState] = useState(() => localStorage.getItem('ejc.theme') || 'system')

  useEffect(() => {
    if (theme === 'system') document.documentElement.removeAttribute('data-theme')
    else document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('ejc.theme', theme)
  }, [theme])

  const reload = useCallback(async () => {
    const data = await settingsApi.get()
    setSettings(data)
    return data
  }, [])

  useEffect(() => {
    if (!user) return
    reload().catch(() => setSettings(FALLBACK))
  }, [user, reload])

  const value = useMemo(
    () => ({
      settings,
      currency: settings.currency || 'UGX',
      reload,
      setSettings,
      theme,
      setTheme: setThemeState,
    }),
    [settings, reload, theme],
  )

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>
}

export function useSettings() {
  const context = useContext(SettingsContext)
  if (!context) throw new Error('useSettings must be used inside a SettingsProvider')
  return context
}
