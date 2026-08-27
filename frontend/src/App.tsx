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
  const isProducts = path === '/'
  return (
    <div className="app-shell">
      <header><a className="brand" href="/dashboard" aria-label="StockFlow home"><span>SF</span>StockFlow</a><nav aria-label="Main navigation"><a className={isDashboard ? 'active' : ''} href="/dashboard">Dashboard</a><a className={isProducts ? 'active' : ''} href="/">Products</a><a className={isPos ? 'active' : ''} href="/pos">Point of Sale</a><a className={isHistory ? 'active' : ''} href="/sales">Sales History</a><a className={isInventoryHistory ? 'active' : ''} href="/inventory">Inventory History</a><a className={isReports ? 'active' : ''} href="/reports">Reports</a><a className={isPurchasing ? 'active' : ''} href="/purchase-orders">Purchase Orders</a><a className={isSuppliers ? 'active' : ''} href="/suppliers">Suppliers</a></nav><div className="api-badge"><i /> StockFlow</div></header>
      <main>{isSuppliers?<SuppliersPage/>:isPurchasing?<PurchaseOrdersPage/>:isDashboard ? <DashboardPage /> : isReports ? <ReportsPage /> : isPos ? <PosPage /> : isHistory ? <SalesHistoryPage /> : isInventoryHistory ? <InventoryHistoryPage /> : <ProductsPage />}</main>
    </div>
  )
}
