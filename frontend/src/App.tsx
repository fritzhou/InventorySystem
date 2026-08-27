import { ProductsPage } from './pages/ProductsPage'
import './styles.css'

export default function App() {
  return (
    <div className="app-shell">
      <header><a className="brand" href="/" aria-label="StockFlow home"><span>SF</span>StockFlow</a><nav aria-label="Main navigation"><a className="active" href="/">Products</a></nav><div className="api-badge"><i /> Product management</div></header>
      <main><ProductsPage /></main>
    </div>
  )
}
