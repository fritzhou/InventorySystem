import { ProductTable } from '../components/ProductTable'
import { useProducts } from '../hooks/useProducts'

export function ProductsPage() {
  const { products, isLoading, error } = useProducts()
  return (
    <section className="card" aria-labelledby="products-heading">
      <div className="section-heading"><div><span className="eyebrow">Foundation preview</span><h2 id="products-heading">Products</h2></div><span className="count">{products.length} items</span></div>
      {isLoading && <p role="status">Loading products…</p>}
      {error && <p className="error" role="alert">{error}</p>}
      {!isLoading && !error && <ProductTable products={products} />}
    </section>
  )
}
