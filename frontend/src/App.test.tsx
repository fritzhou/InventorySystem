import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import App from './App'

afterEach(() => vi.restoreAllMocks())

test('requests products from FastAPI and renders the result', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify([{
    id: '4c7003a8-8cf3-4b57-a4ba-4f40ec23e1ef', name: 'Sparkling Water', sku: 'DRINK-001', barcode: null,
    category_id: '782ec92d-49f7-45d8-8f0e-770666e83f77', cost_price: '12.50', selling_price: '20.00',
    current_stock: 24, minimum_stock: 5, is_active: true, created_at: '2026-08-27T00:00:00Z', updated_at: '2026-08-27T00:00:00Z',
  }])))
  render(<App />)
  expect(await screen.findByText('Sparkling Water')).toBeInTheDocument()
  expect(screen.getByText('₱20.00')).toBeInTheDocument()
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/products', expect.any(Object)))
})
