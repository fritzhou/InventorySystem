import { ProductsPage } from './pages/ProductsPage'
import { PosPage } from './pages/PosPage'
import { SalesHistoryPage } from './pages/SalesHistoryPage'
import { InventoryHistoryPage } from './pages/InventoryHistoryPage'
import './styles.css'

export default function App() {
  const path = window.location.pathname
  const isPos = path === '/pos'
  const isHistory = path === '/sales'
  const isInventoryHistory = path === '/inventory'
  return (
    <div className="app-shell">
      <header><a className="brand" href="/" aria-label="StockFlow home"><span>SF</span>StockFlow</a><nav aria-label="Main navigation"><a className={!isPos && !isHistory && !isInventoryHistory ? 'active' : ''} href="/">Products</a><a className={isPos ? 'active' : ''} href="/pos">Point of Sale</a><a className={isHistory ? 'active' : ''} href="/sales">Sales History</a><a className={isInventoryHistory ? 'active' : ''} href="/inventory">Inventory History</a></nav><div className="api-badge"><i /> {isPos ? 'Cashier ready' : isHistory ? 'Completed sales' : isInventoryHistory ? 'Stock audit trail' : 'Product management'}</div></header>
      <main>{isPos ? <PosPage /> : isHistory ? <SalesHistoryPage /> : isInventoryHistory ? <InventoryHistoryPage /> : <ProductsPage />}</main>
    </div>
  )
}
