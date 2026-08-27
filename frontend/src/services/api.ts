import type { Category, CategoryInput } from '../types/category'
import type { Product, ProductInput, ProductLookup, ProductUpdateInput } from '../types/product'
import type { CheckoutInput, Sale } from '../types/sale'

const API_URL = import.meta.env.VITE_API_URL ?? ''

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  headers.set('Accept', 'application/json')
  if (init?.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const response = await fetch(`${API_URL}${path}`, { ...init, headers })
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string | Array<{ msg: string }> } | null
    const detail = Array.isArray(body?.detail) ? body.detail.map((issue) => issue.msg).join(', ') : body?.detail
    throw new ApiError(detail ?? `StockFlow API request failed (${response.status})`, response.status)
  }
  return response.json() as Promise<T>
}

export interface ProductFilters {
  search?: string
  categoryId?: string
  activeOnly?: boolean
}

export const api = {
  getHealth: () => request<{ status: string; service: string }>('/health'),
  getProducts: ({ search = '', categoryId = '', activeOnly = true }: ProductFilters = {}) => {
    const params = new URLSearchParams({ active_only: String(activeOnly) })
    if (search.trim()) params.set('search', search.trim())
    if (categoryId) params.set('category_id', categoryId)
    return request<Product[]>(`/api/products?${params}`)
  },
  getProductByBarcode: (barcode: string) => request<Product>(`/api/products/barcode/${encodeURIComponent(barcode)}`),
  lookupProductByBarcode: (barcode: string) => request<ProductLookup>(`/api/products/barcode/${encodeURIComponent(barcode)}/lookup`),
  createProduct: (product: ProductInput) => request<Product>('/api/products', { method: 'POST', body: JSON.stringify(product) }),
  updateProduct: (id: string, product: ProductUpdateInput) => request<Product>(`/api/products/${id}`, { method: 'PATCH', body: JSON.stringify(product) }),
  deactivateProduct: (id: string) => request<Product>(`/api/products/${id}`, { method: 'DELETE' }),
  getCategories: () => request<Category[]>('/api/categories'),
  createCategory: (category: CategoryInput) => request<Category>('/api/categories', { method: 'POST', body: JSON.stringify(category) }),
  checkout: (sale: CheckoutInput) => request<Sale>('/api/sales', { method: 'POST', body: JSON.stringify(sale) }),
}
