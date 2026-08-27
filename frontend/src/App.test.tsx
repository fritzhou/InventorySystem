import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import App from './App'

const category = { id: '782ec92d-49f7-45d8-8f0e-770666e83f77', name: 'Drinks', description: 'Beverages', created_at: '2026-08-27T00:00:00Z' }
const product = {
  id: '4c7003a8-8cf3-4b57-a4ba-4f40ec23e1ef', name: 'Sparkling Water', sku: 'DRINK-001', barcode: '4801234567890',
  category_id: category.id, cost_price: '12.50', selling_price: '20.00', current_stock: 3, minimum_stock: 5,
  is_active: true, created_at: '2026-08-27T00:00:00Z', updated_at: '2026-08-27T00:00:00Z',
}

function jsonResponse(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } })
}

function mockApi() {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.endsWith('/api/categories')) return jsonResponse(init?.method === 'POST' ? category : [category], init?.method === 'POST' ? 201 : 200)
    if (url.includes('/api/products')) return jsonResponse(init?.method === 'DELETE' ? { ...product, is_active: false } : [product])
    return jsonResponse({ detail: 'Not found' }, 404)
  })
}

afterEach(() => vi.restoreAllMocks())

test('requests products and categories and displays stock status', async () => {
  const fetchMock = mockApi()
  render(<App />)
  expect(await screen.findByText('Sparkling Water')).toBeInTheDocument()
  expect(screen.getByText('Low stock')).toBeInTheDocument()
  expect(screen.getByText('4801234567890')).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/products?active_only=true'), expect.any(Object))
  expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/categories', expect.any(Object))
})

test('sends search and category filters to FastAPI', async () => {
  const fetchMock = mockApi()
  render(<App />)
  await screen.findByText('Sparkling Water')
  fireEvent.change(screen.getByPlaceholderText('Search name, SKU, or barcode'), { target: { value: 'water' } })
  fireEvent.click(screen.getByRole('button', { name: 'Search' }))
  fireEvent.change(screen.getByRole('combobox', { name: 'Filter by category' }), { target: { value: category.id } })
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining(`search=water&category_id=${category.id}`), expect.any(Object),
  ))
})
