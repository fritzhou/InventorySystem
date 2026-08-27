import type { Category } from '../types/category'
import type { Product } from '../types/product'

interface ProductTableProps {
  products: Product[]
  categories: Category[]
  onEdit: (product: Product) => void
  onDeactivate: (product: Product) => void
}

function stockStatus(product: Product) {
  if (product.current_stock === 0) return { label: 'Out of stock', style: 'out' }
  if (product.current_stock <= product.minimum_stock) return { label: 'Low stock', style: 'low' }
  return { label: 'In stock', style: 'ok' }
}

export function ProductTable({ products, categories, onEdit, onDeactivate }: ProductTableProps) {
  const categoryNames = new Map(categories.map((category) => [category.id, category.name]))
  if (products.length === 0) return <div className="empty">No products match these filters.</div>
  return (
    <div className="table-wrap">
      <table>
        <thead><tr><th>Product</th><th>SKU / Barcode</th><th>Category</th><th>Price</th><th>Stock level</th><th><span className="sr-only">Actions</span></th></tr></thead>
        <tbody>{products.map((product) => {
          const status = stockStatus(product)
          return <tr key={product.id} className={!product.is_active ? 'inactive-row' : undefined}>
            <td><strong>{product.name}</strong>{!product.is_active && <span className="inactive-label">Inactive</span>}</td>
            <td><span>{product.sku}</span><small>{product.barcode || 'No barcode'}</small></td>
            <td>{categoryNames.get(product.category_id) ?? 'Unknown'}</td>
            <td><strong>₱{Number(product.selling_price).toFixed(2)}</strong><small>Cost ₱{Number(product.cost_price).toFixed(2)}</small></td>
            <td><strong>{product.current_stock}</strong><span className={`stock-status ${status.style}`}>{status.label}</span><small>Minimum {product.minimum_stock}</small></td>
            <td><div className="row-actions"><button className="text-button" onClick={() => onEdit(product)}>Edit</button>{product.is_active && <button className="text-button danger" onClick={() => onDeactivate(product)}>Deactivate</button>}</div></td>
          </tr>
        })}</tbody>
      </table>
    </div>
  )
}
