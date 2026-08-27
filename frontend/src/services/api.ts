import type { Category, CategoryInput } from '../types/category'
import type { Product, ProductInput, ProductLookup, ProductUpdateInput } from '../types/product'
import type { CheckoutInput, Sale, SaleReturn, SalesPage, ReturnsPage } from '../types/sale'
import type { InventoryMovement, InventoryMovementPage, MovementType, StockAdjustmentInput } from '../types/inventory'
import type { InventoryStatus, ReportSummary, TopProduct, TrendPoint } from '../types/report'
import type { POInput, POPage, PurchaseOrder, Supplier, SupplierInput, SupplierPage } from '../types/purchasing'
import type { Expense, ExpenseCategory, ExpenseInput, ExpensePage, ExpenseStatus, ExpenseSummary } from '../types/expense'
import type { AuthUser, Role } from '../auth'

const API_URL = import.meta.env.VITE_API_URL ?? ''

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  headers.set('Accept', 'application/json')
  if (init?.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const response = await fetch(`${API_URL}${path}`, { ...init, headers, credentials: 'include' })
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string | Array<{ msg: string }> } | null
    const detail = Array.isArray(body?.detail) ? body.detail.map((issue) => issue.msg).join(', ') : body?.detail
    if (response.status === 401 && path !== '/api/auth/login' && path !== '/api/auth/me') {
      window.dispatchEvent(new CustomEvent('stockflow:session-expired'))
    }
    throw new ApiError(detail ?? `StockFlow API request failed (${response.status})`, response.status)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export interface ProductFilters {
  search?: string
  categoryId?: string
  activeOnly?: boolean
}

export interface SaleFilters {
  search?: string
  startDate?: string
  endDate?: string
  page?: number
  pageSize?: number
}
export interface ReturnFilters { search?: string; startDate?: string; endDate?: string; page?: number; pageSize?: number }
export interface MovementFilters { productId?: string; movementType?: MovementType | ''; search?: string; startDate?: string; endDate?: string; page?: number; pageSize?: number }
export interface PurchaseOrderFilters { search?: string; supplierId?: string; status?: string; fromDate?: string; toDate?: string; page?: number; pageSize?: number }
export interface ExpenseFilters { search?:string; categoryId?:string; status?:ExpenseStatus|''; startDate?:string; endDate?:string; page?:number; pageSize?:number }
export interface AuditEvent {id:string;actor_user_id:string|null;actor_email:string|null;actor_display_name:string|null;action:string;entity_type:string;entity_id:string|null;event_metadata:Record<string,unknown>|null;created_at:string}

export const api = {
  login: (email:string,password:string)=>request<AuthUser>('/api/auth/login',{method:'POST',body:JSON.stringify({email,password})}),
  me: ()=>request<AuthUser>('/api/auth/me'),
  logout: ()=>request<void>('/api/auth/logout',{method:'POST'}),
  changePassword:(current_password:string,new_password:string)=>request<AuthUser>('/api/auth/change-password',{method:'POST',body:JSON.stringify({current_password,new_password})}),
  getUsers:()=>request<AuthUser[]>('/api/users'),
  createUser:(value:{email:string;display_name:string;role:Role;temporary_password:string})=>request<AuthUser>('/api/users',{method:'POST',body:JSON.stringify(value)}),
  updateUser:(id:string,value:Partial<Pick<AuthUser,'email'|'display_name'|'role'|'is_active'>>)=>request<AuthUser>(`/api/users/${id}`,{method:'PATCH',body:JSON.stringify(value)}),
  resetUserPassword:(id:string,temporary_password:string)=>request<AuthUser>(`/api/users/${id}/reset-password`,{method:'POST',body:JSON.stringify({temporary_password})}),
  getAuditEvents:(action='',page=1)=>request<{items:AuditEvent[];total:number;page:number;page_size:number}>(`/api/audit-events?${new URLSearchParams({action,page:String(page)})}`),
  getHealth: () => request<{ status: string; service: string }>('/health'),
  getProducts: ({ search = '', categoryId = '', activeOnly = true }: ProductFilters = {}) => {
    const params = new URLSearchParams({ active_only: String(activeOnly) })
    if (search.trim()) params.set('search', search.trim())
    if (categoryId) params.set('category_id', categoryId)
    return request<Product[]>(`/api/products?${params}`)
  },
  getProductByBarcode: (barcode: string) => request<Product>(`/api/products/barcode/${encodeURIComponent(barcode)}`),
  lookupProductByBarcode: (barcode: string) => request<ProductLookup>(`/api/products/barcode/${encodeURIComponent(barcode)}/lookup`),
  createProduct: (product: ProductInput) => request<Product>('/api/products', { method: 'POST', body: JSON.stringify(product) }),
  updateProduct: (id: string, product: ProductUpdateInput) => request<Product>(`/api/products/${id}`, { method: 'PATCH', body: JSON.stringify(product) }),
  deactivateProduct: (id: string) => request<Product>(`/api/products/${id}`, { method: 'DELETE' }),
  getCategories: () => request<Category[]>('/api/categories'),
  createCategory: (category: CategoryInput) => request<Category>('/api/categories', { method: 'POST', body: JSON.stringify(category) }),
  checkout: (sale: CheckoutInput) => request<Sale>('/api/sales', { method: 'POST', body: JSON.stringify(sale) }),
  getSales: ({ search = '', startDate = '', endDate = '', page = 1, pageSize = 20 }: SaleFilters = {}) => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
    if (search.trim()) params.set('search', search.trim())
    if (startDate) params.set('start_date', startDate)
    if (endDate) params.set('end_date', endDate)
    return request<SalesPage>(`/api/sales?${params}`)
  },
  getSale: (id: string) => request<Sale>(`/api/sales/${encodeURIComponent(id)}`),
  createReturn: (saleId: string, value: { reason?: string; items: Array<{ sale_item_id: string; quantity: number; return_to_stock: boolean }> }) => request<SaleReturn>(`/api/sales/${encodeURIComponent(saleId)}/returns`, { method: 'POST', body: JSON.stringify(value) }),
  getReturns: ({ search = '', startDate = '', endDate = '', page = 1, pageSize = 20 }: ReturnFilters = {}) => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) }); if (search.trim()) params.set('search', search.trim()); if (startDate) params.set('start_date', startDate); if (endDate) params.set('end_date', endDate)
    return request<ReturnsPage>(`/api/returns?${params}`)
  },
  getReturn: (id: string) => request<SaleReturn>(`/api/returns/${encodeURIComponent(id)}`),
  adjustStock: (id: string, adjustment: StockAdjustmentInput) => request<InventoryMovement>(`/api/products/${id}/stock-adjustments`, { method: 'POST', body: JSON.stringify(adjustment) }),
  getInventoryMovements: ({ productId = '', movementType = '', search = '', startDate = '', endDate = '', page = 1, pageSize = 20 }: MovementFilters = {}) => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
    if (productId) params.set('product_id', productId)
    if (movementType) params.set('movement_type', movementType)
    if (search.trim()) params.set('search', search.trim())
    if (startDate) params.set('start_date', startDate)
    if (endDate) params.set('end_date', endDate)
    return request<InventoryMovementPage>(`/api/inventory/movements?${params}`)
  },
  getReportSummary: (startDate = '', endDate = '', dashboard = false) => request<ReportSummary>(`/api/reports/${dashboard ? 'dashboard' : 'summary'}${reportQuery(startDate, endDate)}`),
  getSalesTrend: (startDate = '', endDate = '') => request<TrendPoint[]>(`/api/reports/sales-trend${reportQuery(startDate, endDate)}`),
  getTopProducts: (startDate = '', endDate = '', limit = 10) => request<TopProduct[]>(`/api/reports/top-products${reportQuery(startDate, endDate, limit)}`),
  getInventoryStatus: () => request<InventoryStatus>('/api/reports/inventory-status'),
  getSuppliers: (search='', activeOnly=true, page=1) => request<SupplierPage>(`/api/suppliers?${new URLSearchParams({search,active_only:String(activeOnly),page:String(page)})}`),
  createSupplier: (value:SupplierInput) => request<Supplier>('/api/suppliers',{method:'POST',body:JSON.stringify(value)}),
  updateSupplier: (id:string,value:Partial<SupplierInput>) => request<Supplier>(`/api/suppliers/${id}`,{method:'PATCH',body:JSON.stringify(value)}),
  deactivateSupplier: (id:string) => request<Supplier>(`/api/suppliers/${id}`,{method:'DELETE'}),
  getPurchaseOrders: ({ search = '', supplierId = '', status = '', fromDate = '', toDate = '', page = 1, pageSize = 20 }: PurchaseOrderFilters = {}) => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
    if (search.trim()) params.set('search', search.trim())
    if (supplierId) params.set('supplier_id', supplierId)
    if (status) params.set('status', status)
    if (fromDate) params.set('from_date', fromDate)
    if (toDate) params.set('to_date', toDate)
    return request<POPage>(`/api/purchase-orders?${params}`)
  },
  getPurchaseOrder: (id:string) => request<PurchaseOrder>(`/api/purchase-orders/${id}`),
  createPurchaseOrder: (value:POInput) => request<PurchaseOrder>('/api/purchase-orders',{method:'POST',body:JSON.stringify(value)}),
  updatePurchaseOrder: (id:string,value:POInput) => request<PurchaseOrder>(`/api/purchase-orders/${id}`,{method:'PATCH',body:JSON.stringify(value)}),
  markPurchaseOrderOrdered: (id:string) => request<PurchaseOrder>(`/api/purchase-orders/${id}/mark-ordered`,{method:'POST'}),
  cancelPurchaseOrder: (id:string) => request<PurchaseOrder>(`/api/purchase-orders/${id}/cancel`,{method:'POST'}),
  receivePurchaseOrder: (id:string,items:Array<{item_id:string;quantity:number}>) => request<PurchaseOrder>(`/api/purchase-orders/${id}/receive`,{method:'POST',body:JSON.stringify({items})}),
  getExpenseCategories: (activeOnly=false) => request<ExpenseCategory[]>(`/api/expense-categories?active_only=${activeOnly}`),
  createExpenseCategory: (value:{name:string;description?:string|null}) => request<ExpenseCategory>('/api/expense-categories',{method:'POST',body:JSON.stringify(value)}),
  updateExpenseCategory: (id:string,value:{name?:string;description?:string|null}) => request<ExpenseCategory>(`/api/expense-categories/${id}`,{method:'PATCH',body:JSON.stringify(value)}),
  deactivateExpenseCategory: (id:string) => request<ExpenseCategory>(`/api/expense-categories/${id}`,{method:'DELETE'}),
  getExpenses: ({search='',categoryId='',status='',startDate='',endDate='',page=1,pageSize=20}:ExpenseFilters={}) => { const p=new URLSearchParams({page:String(page),page_size:String(pageSize)});if(search.trim())p.set('search',search.trim());if(categoryId)p.set('category_id',categoryId);if(status)p.set('status',status);if(startDate)p.set('start_date',startDate);if(endDate)p.set('end_date',endDate);return request<ExpensePage>(`/api/expenses?${p}`)},
  createExpense: (value:ExpenseInput) => request<Expense>('/api/expenses',{method:'POST',body:JSON.stringify(value)}),
  updateExpense: (id:string,value:Partial<ExpenseInput>) => request<Expense>(`/api/expenses/${id}`,{method:'PATCH',body:JSON.stringify(value)}),
  voidExpense: (id:string,reason:string) => request<Expense>(`/api/expenses/${id}/void`,{method:'POST',body:JSON.stringify({reason})}),
  getExpenseSummary: (startDate='',endDate='') => request<ExpenseSummary>(`/api/reports/expenses${reportQuery(startDate,endDate)}`),
}

function reportQuery(startDate: string, endDate: string, limit?: number) {
  const params = new URLSearchParams()
  if (startDate) params.set('start_date', startDate)
  if (endDate) params.set('end_date', endDate)
  if (limit) params.set('limit', String(limit))
  const query = params.toString()
  return query ? `?${query}` : ''
}
