import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import App from './App'

const summary = { id: 'sale-1', receipt_number: 'SF-A12BC34D', created_at: '2026-08-27T12:42:00Z', payment_method: 'cash', total: '70.00', item_count: 3 }
const page = { items: [summary], page: 1, page_size: 20, total_items: 21, total_pages: 2 }
const detail = { ...summary, subtotal: '70.00', amount_tendered: '100.00', change_due: '30.00', items: [{ id: 'item-1', product_id: 'product-1', product_name: 'Coca-Cola', sku: 'COKE', unit_price: '25.00', quantity: 2, line_total: '50.00' }, { id: 'item-2', product_id: 'product-2', product_name: 'Water', sku: 'WATER', unit_price: '20.00', quantity: 1, line_total: '20.00' }] }
const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

beforeEach(() => { window.history.pushState({}, '', '/sales'); vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => String(input).includes('/api/sales/sale-1') ? response(detail) : response(page)) })
afterEach(() => { cleanup(); vi.restoreAllMocks(); window.history.pushState({}, '', '/') })

test('renders sales history and opens a historical snapshot receipt', async () => {
  render(<App />); expect(await screen.findByText('SF-A12BC34D')).toBeInTheDocument(); expect(screen.getByText('3 items')).toBeInTheDocument(); expect(screen.getByText('₱70.00')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'View Receipt' })); expect(await screen.findByText('Coca-Cola')).toBeInTheDocument(); expect(screen.getByText((_, node) => node?.tagName === 'SMALL' && node.textContent?.includes('2 × ₱25.00') === true)).toBeInTheDocument()
  expect(screen.getAllByText('₱70.00')).toHaveLength(2); expect(screen.getByText('₱100.00')).toBeInTheDocument(); expect(screen.getByText('₱30.00')).toBeInTheDocument(); expect(screen.getByRole('button', { name: 'Print Receipt' })).toBeInTheDocument()
})

test('shows the empty sales state', async () => { vi.mocked(fetch).mockResolvedValue(response({ ...page, items: [], total_items: 0, total_pages: 0 })); render(<App />); expect(await screen.findByText('No sales found.')).toBeInTheDocument() })

test('applies receipt search and date filters and resets pagination', async () => {
  render(<App />); await screen.findByText('SF-A12BC34D'); fireEvent.change(screen.getByLabelText('Search receipt'), { target: { value: 'SF-A12' } }); fireEvent.change(screen.getByLabelText('From date'), { target: { value: '2026-08-01' } }); fireEvent.change(screen.getByLabelText('To date'), { target: { value: '2026-08-27' } }); fireEvent.click(screen.getByRole('button', { name: 'Apply Filters' }))
  await waitFor(() => expect(String(vi.mocked(fetch).mock.calls.at(-1)?.[0])).toContain('search=SF-A12')); const url = String(vi.mocked(fetch).mock.calls.at(-1)?.[0]); expect(url).toContain('start_date=2026-08-01'); expect(url).toContain('end_date=2026-08-27'); expect(url).toContain('page=1')
})

test('validates dates and paginates using the backend page', async () => {
  render(<App />); await screen.findByText('SF-A12BC34D'); fireEvent.click(screen.getByRole('button', { name: 'Next' })); await waitFor(() => expect(String(vi.mocked(fetch).mock.calls.at(-1)?.[0])).toContain('page=2'))
  fireEvent.change(screen.getByLabelText('From date'), { target: { value: '2026-08-28' } }); fireEvent.change(screen.getByLabelText('To date'), { target: { value: '2026-08-01' } }); fireEvent.click(screen.getByRole('button', { name: 'Apply Filters' })); expect(screen.getByRole('alert')).toHaveTextContent('From date cannot be after To date')
})

test('handles history and receipt load errors safely', async () => {
  vi.mocked(fetch).mockResolvedValue(response({ detail: 'internal details' }, 500)); render(<App />); expect(await screen.findByRole('alert')).toHaveTextContent('Sales history could not be loaded.')
  cleanup(); vi.mocked(fetch).mockImplementation(async (input) => String(input).includes('/sale-1') ? response({ detail: 'gone' }, 404) : response(page)); render(<App />); await screen.findByText('SF-A12BC34D'); fireEvent.click(screen.getByRole('button', { name: 'View Receipt' })); expect(await screen.findByRole('alert')).toHaveTextContent('Receipt not found.')
})
