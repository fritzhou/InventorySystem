export interface Product {
  id: string
  name: string
  sku: string
  barcode: string | null
  category_id: string
  cost_price: string
  selling_price: string
  current_stock: number
  minimum_stock: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ProductInput {
  name: string
  sku: string
  barcode: string | null
  category_id: string
  cost_price: string
  selling_price: string
  current_stock: number
  minimum_stock: number
}

export type ProductUpdateInput = Omit<ProductInput, 'current_stock'>
