export type MovementType = 'RESTOCK' | 'SALE' | 'DAMAGE' | 'CORRECTION'
export interface StockAdjustmentInput { type: Exclude<MovementType, 'SALE'>; quantity?: number; actual_stock?: number; note?: string }
export interface InventoryMovement {
  id: string; product_id: string; movement_type: MovementType; quantity_change: number
  stock_before: number; stock_after: number; reference_type: string | null; reference_id: string | null
  receipt_number: string | null; note: string | null; created_at: string
  product: { id: string; name: string; sku: string; is_active: boolean }
}
export interface InventoryMovementPage { items: InventoryMovement[]; page: number; page_size: number; total_items: number; total_pages: number }
