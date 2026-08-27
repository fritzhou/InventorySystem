export interface CheckoutInput {
  items: Array<{ product_id: string; quantity: number }>
  amount_tendered: string
}

export interface SaleItem {
  id: string
  product_id: string
  product_name: string
  sku: string
  unit_price: string
  quantity: number
  line_total: string
}

export interface Sale {
  id: string
  receipt_number: string
  subtotal: string
  total: string
  amount_tendered: string
  change_due: string
  payment_method: 'cash'
  created_at: string
  items: SaleItem[]
}

export interface SaleSummary {
  id: string
  receipt_number: string
  created_at: string
  payment_method: string
  total: string
  item_count: number
}

export interface SalesPage {
  items: SaleSummary[]
  page: number
  page_size: number
  total_items: number
  total_pages: number
}
