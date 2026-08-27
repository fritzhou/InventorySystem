import { ProductsPage } from './pages/ProductsPage'
import './styles.css'

export default function App() {
  return (
    <div className="app-shell">
      <header><a className="brand" href="/" aria-label="StockFlow home"><span>SF</span>StockFlow</a><div className="api-badge"><i /> API-ready foundation</div></header>
      <main>
        <div className="hero"><div><p className="eyebrow">Inventory management, made clear</p><h1>Your stock.<br />Always in flow.</h1><p className="intro">The StockFlow foundation is connected to the FastAPI product service and ready for the next feature.</p></div><div className="stat"><strong>Phase 1</strong><span>Foundation</span></div></div>
        <ProductsPage />
      </main>
    </div>
  )
}
