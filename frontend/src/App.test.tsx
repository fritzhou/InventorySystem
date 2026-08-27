import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import App from './App'
import { BarcodeScanner } from './components/BarcodeScanner'

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
    if (url.includes('/api/products/barcode/')) return jsonResponse(product)
    if (url.includes('/api/products')) return jsonResponse(init?.method === 'DELETE' ? { ...product, is_active: false } : [product])
    return jsonResponse({ detail: 'Not found' }, 404)
  })
}

afterEach(() => { cleanup(); vi.restoreAllMocks() })

test('requests products and categories and displays stock status', async () => {
  const fetchMock = mockApi()
  render(<App />)
  expect(await screen.findByText('Sparkling Water')).toBeInTheDocument()
  expect(screen.getByText('Low stock')).toBeInTheDocument()
  expect(screen.getByText('4801234567890')).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/products?active_only=true'), expect.any(Object))
  expect(fetchMock).toHaveBeenCalledWith('/api/categories', expect.any(Object))
})

test('looks up a manually scanned barcode and displays the product without changing stock', async () => {
  const fetchMock = mockApi()
  render(<App />)
  await screen.findByText('Sparkling Water')
  fireEvent.click(screen.getByRole('button', { name: 'Scan barcode' }))
  fireEvent.change(screen.getByLabelText('Enter barcode manually'), { target: { value: product.barcode } })
  fireEvent.click(screen.getByRole('button', { name: 'Look up' }))
  expect(await screen.findByText('Scan successful')).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: product.name })).toBeInTheDocument()
  expect(screen.getAllByText('Low stock')).toHaveLength(2)
  expect(fetchMock).toHaveBeenCalledWith(`/api/products/barcode/${product.barcode}`, expect.any(Object))
  expect(fetchMock).not.toHaveBeenCalledWith(expect.anything(), expect.objectContaining({ method: 'PATCH' }))
})

test('shows an unknown barcode and prefills it when adding a product', async () => {
  const unknown = '012345678905'
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = String(input)
    if (url.endsWith('/api/categories')) return jsonResponse([category])
    if (url.includes('/api/products/barcode/')) return jsonResponse({ detail: 'Product not found.' }, 404)
    if (url.includes('/api/products')) return jsonResponse([product])
    return jsonResponse({}, 404)
  })
  render(<App />)
  await screen.findByText('Sparkling Water')
  fireEvent.click(screen.getByRole('button', { name: 'Scan barcode' }))
  fireEvent.change(screen.getByLabelText('Enter barcode manually'), { target: { value: unknown } })
  fireEvent.click(screen.getByRole('button', { name: 'Look up' }))
  expect(await screen.findByRole('heading', { name: 'Product not registered' })).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Add Product' }))
  expect(screen.getByLabelText(/Barcode/)).toHaveValue(unknown)
})

test('stops camera tracks when the scanner unmounts', async () => {
  const stop = vi.fn()
  const stream = { getTracks: () => [{ stop }] } as unknown as MediaStream
  Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia: vi.fn().mockResolvedValue(stream) } })
  window.BarcodeDetector = class { static getSupportedFormats = async () => ['ean_13']; detect = async () => [] }
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue()
  const { unmount } = render(<BarcodeScanner onDetected={vi.fn()} />)
  await waitFor(() => expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalled())
  unmount()
  expect(stop).toHaveBeenCalled()
  delete window.BarcodeDetector
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
