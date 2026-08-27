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

export interface ExternalProduct {
  barcode: string
  product_name: string | null
  brand: string | null
  category_text: string | null
  package_size: string | null
  image_url: string | null
}

export interface ProductLookup {
  found: boolean
  source: 'stockflow' | 'open_food_facts' | 'none'
  product: Product | null
  external_product: ExternalProduct | null
  reason: 'not_found' | 'provider_unavailable' | null
}
