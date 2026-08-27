import { useCallback, useEffect, useState } from 'react'

import { api, type ProductFilters } from '../services/api'
import type { Product } from '../types/product'

export function useProducts({ search, categoryId, activeOnly }: ProductFilters) {
  const [products, setProducts] = useState<Product[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  const refresh = useCallback(() => setRefreshKey((key) => key + 1), [])

  useEffect(() => {
    const controller = new AbortController()
    setIsLoading(true)
    setError(null)
    api.getProducts({ search, categoryId, activeOnly })
      .then(setProducts)
      .catch((requestError: unknown) => {
        if (!controller.signal.aborted) {
          setError(requestError instanceof Error ? requestError.message : 'Could not load products.')
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false)
      })
    return () => controller.abort()
  }, [search, categoryId, activeOnly, refreshKey])

  return { products, isLoading, error, refresh }
}
