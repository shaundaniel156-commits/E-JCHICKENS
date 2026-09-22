import { useMemo } from 'react'

import { birdsApi, expensesApi, feedApi, salesApi } from '../api/endpoints'
import { useApi } from './useApi'

/** Bird batches for dropdowns, labelled with what is still in the batch. */
export function useBatchOptions({ activeOnly = false } = {}) {
  const { data, loading, reload } = useApi(
    () => birdsApi.options({ active_only: activeOnly }),
    [activeOnly],
  )

  const options = useMemo(
    () =>
      (data ?? []).map((batch) => ({
        value: String(batch.id),
        label: `${batch.batch_code} — ${batch.breed} (${batch.current_quantity} birds)`,
        available: batch.current_quantity,
        batch,
      })),
    [data],
  )

  return { options, batches: data ?? [], loading, reload }
}

export function useFeedTypeOptions() {
  const { data, loading, reload } = useApi(() => feedApi.types(), [])
  const options = useMemo(
    () =>
      (data ?? []).map((type) => ({
        value: String(type.id),
        label: `${type.name} (${type.stock_bags} bags in stock)`,
        type,
      })),
    [data],
  )
  return { options, types: data ?? [], loading, reload }
}

export function useCategoryOptions() {
  const { data, loading, reload } = useApi(() => expensesApi.categories(), [])
  const options = useMemo(
    () => (data ?? []).map((category) => ({ value: String(category.id), label: category.name })),
    [data],
  )
  return { options, categories: data ?? [], loading, reload }
}

export function useCustomerOptions() {
  const { data, loading, reload } = useApi(() => salesApi.customers({ page_size: 200 }), [])
  const options = useMemo(
    () => (data?.items ?? []).map((customer) => ({ value: String(customer.id), label: customer.name })),
    [data],
  )
  return { options, customers: data?.items ?? [], loading, reload }
}
