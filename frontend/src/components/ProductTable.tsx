import type { Product } from '../types/product'

interface ProductTableProps {
  products: Product[]
}

export function ProductTable({ products }: ProductTableProps) {
  if (products.length === 0) return <div className="empty">No products yet. Add one through the API to see it here.</div>
  return (
    <div className="table-wrap">
      <table>
        <thead><tr><th>Product</th><th>SKU</th><th>Price</th><th>Stock</th></tr></thead>
        <tbody>
          {products.map((product) => (
            <tr key={product.id}>
              <td>{product.name}</td><td>{product.sku}</td>
              <td>₱{Number(product.selling_price).toFixed(2)}</td><td>{product.current_stock}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
