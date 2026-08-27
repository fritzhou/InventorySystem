import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import App from './App'

const coke = { id: '4c7003a8-8cf3-4b57-a4ba-4f40ec23e1ef', name: 'Coke', sku: 'COKE', barcode: '480001', category_id: 'cat', cost_price: '10.00', selling_price: '25.00', current_stock: 2, minimum_stock: 0, is_active: true, created_at: '2026-08-27T00:00:00Z', updated_at: '2026-08-27T00:00:00Z' }
const water = { ...coke, id: 'af07eeca-f1b3-450a-a68c-460e35ae77e7', name: 'Water', sku: 'WATER', barcode: '480002', selling_price: '20.00', current_stock: 4 }
const completedSale = { id: 'sale', receipt_number: 'SF-ABC123', subtotal: '70.00', total: '70.00', amount_tendered: '100.00', change_due: '30.00', payment_method: 'cash', created_at: '2026-08-27T10:30:00Z', items: [{ id: 'i1', product_id: coke.id, product_name: 'Coke', sku: 'COKE', unit_price: '25.00', quantity: 2, line_total: '50.00' }, { id: 'i2', product_id: water.id, product_name: 'Water', sku: 'WATER', unit_price: '20.00', quantity: 1, line_total: '20.00' }] }

const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

beforeEach(() => {
  window.history.pushState({}, '', '/pos')
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.includes('/api/products/barcode/480001')) return response(coke)
    if (url.includes('/api/products')) return response([coke, water])
    if (url.endsWith('/api/sales') && init?.method === 'POST') return response(completedSale, 201)
    return response({ detail: 'Not found' }, 404)
  })
})
afterEach(() => { cleanup(); vi.restoreAllMocks(); window.history.pushState({}, '', '/') })

test('adds products, adjusts quantities without exceeding stock, removes, and calculates totals', async () => {
  render(<App />)
  await screen.findByText('Coke')
  fireEvent.click(screen.getAllByRole('button', { name: 'Add' })[0])
  expect(screen.getByText('₱25.00', { selector: '.cart-line > strong' })).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Increase Coke' }))
  expect(screen.getByLabelText('Coke quantity')).toHaveValue(2)
  expect(screen.getAllByText('₱50.00')).toHaveLength(3)
  expect(screen.getByRole('button', { name: 'Increase Coke' })).toBeDisabled()
  fireEvent.change(screen.getByLabelText('Coke quantity'), { target: { value: '5' } })
  expect(screen.getByLabelText('Coke quantity')).toHaveValue(2)
  expect(screen.getByRole('alert')).toHaveTextContent('Only 2 available')
  fireEvent.click(screen.getByRole('button', { name: 'Remove Coke' }))
  expect(screen.queryByLabelText('Coke quantity')).not.toBeInTheDocument()
})

test('scanning the same product adds one to the existing cart line', async () => {
  render(<App />); await screen.findByText('Coke')
  for (let i = 0; i < 2; i += 1) {
    fireEvent.click(screen.getByRole('button', { name: /Scan Barcode/ }))
    fireEvent.change(screen.getByLabelText('Enter barcode manually'), { target: { value: '480001' } })
    fireEvent.click(screen.getByRole('button', { name: 'Look up' }))
    await waitFor(() => expect(screen.queryByLabelText('Enter barcode manually')).not.toBeInTheDocument())
  }
  expect(screen.getByLabelText('Coke quantity')).toHaveValue(2)
  expect(screen.getAllByText('Coke')).toHaveLength(2)
})

test('shows cash change, sends only item identities and quantities, and renders completed sale', async () => {
  const fetchMock = vi.mocked(fetch)
  render(<App />); await screen.findByText('Coke')
  fireEvent.click(screen.getAllByRole('button', { name: 'Add' })[0]); fireEvent.click(screen.getByRole('button', { name: 'Increase Coke' })); fireEvent.click(screen.getAllByRole('button', { name: 'Add' })[1])
  expect(screen.getByRole('button', { name: 'Checkout' })).toBeDisabled()
  fireEvent.change(screen.getByLabelText('Cash received'), { target: { value: '100' } })
  expect(screen.getByText('₱30.00')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Checkout' }))
  expect(await screen.findByLabelText('Sale complete')).toBeInTheDocument()
  expect(screen.getByText('Receipt SF-ABC123')).toBeInTheDocument()
  const call = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/api/sales'))
  expect(JSON.parse(String(call?.[1]?.body))).toEqual({ items: [{ product_id: coke.id, quantity: 2 }, { product_id: water.id, quantity: 1 }], amount_tendered: '100.00' })
})

test('keeps the cart and displays a safe checkout error', async () => {
  vi.mocked(fetch).mockImplementation(async (input) => String(input).includes('/api/products') ? response([coke, water]) : response({ detail: 'Insufficient stock for Coke. Available: 1' }, 409))
  render(<App />); await screen.findByText('Coke')
  fireEvent.click(screen.getAllByRole('button', { name: 'Add' })[0]); fireEvent.change(screen.getByLabelText('Cash received'), { target: { value: '25' } }); fireEvent.click(screen.getByRole('button', { name: 'Checkout' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Insufficient stock for Coke. Available: 1')
  expect(screen.getByLabelText('Coke quantity')).toHaveValue(1)
})
