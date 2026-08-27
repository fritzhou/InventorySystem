import { useEffect, useState } from 'react'

import { api } from '../services/api'
import type { Product } from '../types/product'

export function useProducts() {
  const [products, setProducts] = useState<Product[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    api.getProducts()
      .then((data) => active && setProducts(data))
      .catch(() => active && setError('Could not reach the StockFlow API. Check that the backend is running.'))
      .finally(() => active && setIsLoading(false))
    return () => { active = false }
  }, [])

  return { products, isLoading, error }
}
