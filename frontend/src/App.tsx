import { ProductsPage } from './pages/ProductsPage'
import { PosPage } from './pages/PosPage'
import { SalesHistoryPage } from './pages/SalesHistoryPage'
import { InventoryHistoryPage } from './pages/InventoryHistoryPage'
import { DashboardPage } from './pages/DashboardPage'
import { ReportsPage } from './pages/ReportsPage'
import { SuppliersPage } from './pages/SuppliersPage'
import { PurchaseOrdersPage } from './pages/PurchaseOrdersPage'
import './styles.css'

export default function App() {
  const path = window.location.pathname
  const isPos = path === '/pos'
  const isHistory = path === '/sales'
  const isInventoryHistory = path === '/inventory'
  const isDashboard = path === '/dashboard'
  const isReports = path === '/reports'
  const isSuppliers = path === '/suppliers'
  const isPurchasing = path.startsWith('/purchase-orders')
  return (
    <div className="app-shell">
      <header><a className="brand" href="/dashboard" aria-label="StockFlow home"><span>SF</span>StockFlow</a><nav aria-label="Main navigation"><a href="/dashboard">Dashboard</a><a href="/">Products</a><a href="/pos">POS</a><a href="/sales">Sales</a><a href="/inventory">Inventory</a><a href="/reports">Reports</a><a className={isPurchasing?'active':''} href="/purchase-orders">Purchase Orders</a><a className={isSuppliers?'active':''} href="/suppliers">Suppliers</a></nav></header>
      <main>{isSuppliers?<SuppliersPage/>:isPurchasing?<PurchaseOrdersPage/>:isDashboard ? <DashboardPage /> : isReports ? <ReportsPage /> : isPos ? <PosPage /> : isHistory ? <SalesHistoryPage /> : isInventoryHistory ? <InventoryHistoryPage /> : <ProductsPage />}</main>
    </div>
  )
}
