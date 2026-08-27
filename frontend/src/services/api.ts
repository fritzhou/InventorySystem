import type { Product } from '../types/product'

const API_URL = import.meta.env.VITE_API_URL ?? ''

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { Accept: 'application/json' },
  })
  if (!response.ok) {
    throw new Error(`StockFlow API request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export const api = {
  getHealth: () => request<{ status: string; service: string }>('/health'),
  getProducts: () => request<Product[]>('/api/products'),
}
cd /workspaces/InventorySystem
git add .gitignore frontend/vite.config.ts frontend/src/services/api.ts frontend/package-lock.json
git commit -m "Fix Codespaces API connection"
git push origin main
