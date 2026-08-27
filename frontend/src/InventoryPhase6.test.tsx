import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { StockAdjustmentModal } from './components/StockAdjustmentModal'
import { InventoryHistoryPage } from './pages/InventoryHistoryPage'
import type { Product } from './types/product'

const product = { id: 'p1', name: 'Water', sku: 'WATER', current_stock: 38, is_active: true } as Product

test('previews adjustment types, submits a correction, and renders API errors', () => {
  const confirm = vi.fn()
  const view = render(<StockAdjustmentModal product={product} saving={false} error={null} onCancel={() => {}} onConfirm={confirm} />)
  fireEvent.change(screen.getByLabelText('Quantity'), { target: { value: '25' } })
  expect(screen.getByText('Result: 63')).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Adjustment Type'), { target: { value: 'DAMAGE' } })
  fireEvent.change(screen.getByLabelText('Quantity'), { target: { value: '3' } })
  expect(screen.getByText('Result: 35')).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Adjustment Type'), { target: { value: 'CORRECTION' } })
  fireEvent.change(screen.getByLabelText('Actual counted stock'), { target: { value: '40' } })
  expect(screen.getByText('Adjustment: +2')).toBeInTheDocument()
  fireEvent.click(screen.getByText('Confirm Adjustment'))
  expect(confirm).toHaveBeenCalledWith({ type: 'CORRECTION', actual_stock: 40, note: '' })
  view.rerender(<StockAdjustmentModal product={product} saving={false} error="Could not save" onCancel={() => {}} onConfirm={confirm} />)
  expect(screen.getByRole('alert')).toHaveTextContent('Could not save')
})

test('renders sale history and applies filters and pagination', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items: [{ id: 'm1', product_id: 'p1', movement_type: 'SALE', quantity_change: -2, stock_before: 20, stock_after: 18, reference_type: 'SALE', reference_id: 's1', receipt_number: 'SF-ABC', note: null, created_at: '2026-08-27T13:42:00Z', product: { id: 'p1', name: 'Coca-Cola', sku: 'COKE', is_active: true } }], page: 1, page_size: 20, total_items: 21, total_pages: 2 }) }))
  render(<InventoryHistoryPage />)
  expect(await screen.findByText('Coca-Cola')).toBeInTheDocument()
  expect(screen.getByText('Receipt SF-ABC')).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Movement Type'), { target: { value: 'SALE' } })
  fireEvent.click(screen.getByText('Apply Filters'))
  await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining('movement_type=SALE'), expect.anything()))
  fireEvent.click(screen.getByText('Next'))
  await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining('page=2'), expect.anything()))
})
