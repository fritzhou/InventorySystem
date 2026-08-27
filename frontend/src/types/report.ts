export interface ReportSummary { sales_total: string; transaction_count: number; items_sold: number; gross_profit: string; profit_complete: boolean; operating_expenses:string; net_profit:string|null; net_profit_complete:boolean; average_transaction_value: string; total_active_products: number; total_units_in_stock: number; low_stock_count: number; out_of_stock_count: number }
export interface TrendPoint { date: string; sales: string; transactions: number; items_sold: number; gross_profit:string; expenses:string; net_profit:string|null; profit_complete:boolean }
export interface TopProduct { product_id: string | null; product_name: string; sku: string; quantity_sold: number; revenue: string }
export interface StockProduct { product_id: string; product_name: string; sku: string; current_stock: number; minimum_stock: number }
export interface InventoryStatus { total_active_products: number; total_units_in_stock: number; low_stock: StockProduct[]; out_of_stock: StockProduct[] }
