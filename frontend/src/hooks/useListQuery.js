import { useCallback, useMemo, useState } from 'react'

import { useApi, useDebounced } from './useApi'

/**
 * The shared behaviour behind every list page: search, filters, sorting,
 * pagination and reload — so no page re-implements it.
 */
export function useListQuery(fetcher, { pageSize = 10, sort = null, order = 'desc', filters = {} } = {}) {
  const [page, setPage] = useState(1)
  const [size, setSize] = useState(pageSize)
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState(sort)
  const [sortOrder, setSortOrder] = useState(order)
  const [extraFilters, setExtraFilters] = useState(filters)

  const debouncedSearch = useDebounced(search)

  const params = useMemo(() => {
    const clean = {}
    Object.entries(extraFilters).forEach(([key, value]) => {
      if (value !== '' && value !== null && value !== undefined) clean[key] = value
    })
    return {
      page,
      page_size: size,
      ...(debouncedSearch ? { search: debouncedSearch } : {}),
      ...(sortBy ? { sort: sortBy, order: sortOrder } : {}),
      ...clean,
    }
  }, [page, size, debouncedSearch, sortBy, sortOrder, extraFilters])

  const key = JSON.stringify(params)
  const { data, loading, error, reload } = useApi(() => fetcher(params), [key])

  const setFilter = useCallback((name, value) => {
    setExtraFilters((current) => ({ ...current, [name]: value }))
    setPage(1)
  }, [])

  const setFiltersBulk = useCallback((next) => {
    setExtraFilters((current) => ({ ...current, ...next }))
    setPage(1)
  }, [])

  const toggleSort = useCallback(
    (column) => {
      if (sortBy === column) setSortOrder((current) => (current === 'asc' ? 'desc' : 'asc'))
      else {
        setSortBy(column)
        setSortOrder('asc')
      }
      setPage(1)
    },
    [sortBy],
  )

  const onSearch = useCallback((value) => {
    setSearch(value)
    setPage(1)
  }, [])

  return {
    items: data?.items ?? [],
    meta: data?.meta ?? { total: 0, page: 1, page_size: size, pages: 0 },
    loading,
    error,
    reload,
    page,
    setPage,
    pageSize: size,
    setPageSize: (value) => {
      setSize(value)
      setPage(1)
    },
    search,
    onSearch,
    sortBy,
    sortOrder,
    toggleSort,
    filters: extraFilters,
    setFilter,
    setFilters: setFiltersBulk,
  }
}
