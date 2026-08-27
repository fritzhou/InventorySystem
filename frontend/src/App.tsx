import { ProductsPage } from './pages/ProductsPage'
import { PosPage } from './pages/PosPage'
import './styles.css'

export default function App() {
  const isPos = window.location.pathname === '/pos'
  return (
    <div className="app-shell">
      <header><a className="brand" href="/" aria-label="StockFlow home"><span>SF</span>StockFlow</a><nav aria-label="Main navigation"><a className={!isPos ? 'active' : ''} href="/">Products</a><a className={isPos ? 'active' : ''} href="/pos">Point of Sale</a></nav><div className="api-badge"><i /> {isPos ? 'Cashier ready' : 'Product management'}</div></header>
      <main>{isPos ? <PosPage /> : <ProductsPage />}</main>
    </div>
  )
}
