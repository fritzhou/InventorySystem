export interface Supplier { id:string; name:string; contact_person:string|null; phone:string|null; email:string|null; address:string|null; notes:string|null; is_active:boolean; created_at:string; updated_at:string }
export interface SupplierInput { name:string; contact_person?:string|null; phone?:string|null; email?:string|null; address?:string|null; notes?:string|null }
export interface SupplierPage { items:Supplier[]; page:number; page_size:number; total_items:number; total_pages:number }
export type POStatus='DRAFT'|'ORDERED'|'PARTIALLY_RECEIVED'|'RECEIVED'|'CANCELLED'
export interface POItem { id:string; product_id:string; product_name:string; sku:string; ordered_quantity:number; received_quantity:number; unit_cost:string; line_total:string }
export interface PurchaseOrder { id:string; po_number:string; supplier_id:string; supplier:Supplier; status:POStatus; order_date:string; expected_date:string|null; notes:string|null; subtotal:string; items:POItem[]; created_at:string; updated_at:string }
export interface POPage { items:PurchaseOrder[]; page:number; page_size:number; total_items:number; total_pages:number }
export interface POInput { supplier_id:string; expected_date:string|null; notes:string|null; items:Array<{product_id:string;quantity:number;unit_cost:string}> }
