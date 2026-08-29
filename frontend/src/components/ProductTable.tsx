import type { Category } from '../types/category'
import type { Product } from '../types/product'
import { EmptyState } from './ui'

interface ProductTableProps {
  products: Product[]
  categories: Category[]
  onEdit: (product: Product) => void
  onDeactivate: (product: Product) => void
  onAdjustStock: (product: Product) => void
}

function stockStatus(product: Product) {
  if (product.current_stock === 0) return { label: 'Out of stock', style: 'out' }
  if (product.current_stock <= product.minimum_stock) return { label: 'Low stock', style: 'low' }
  return { label: 'In stock', style: 'ok' }
}

export function ProductTable({ products, categories, onEdit, onDeactivate, onAdjustStock }: ProductTableProps) {
  const categoryNames = new Map(categories.map((category) => [category.id, category.name]))
  if (products.length === 0) return <EmptyState title="No products found" description="Try changing the search or filters, or add a new product to the catalog." />
  return (
    <div className="table-wrap">
      <table>
        <thead><tr><th>Product</th><th>SKU / Barcode</th><th>Category</th><th>Price</th><th>Stock level</th><th><span className="sr-only">Actions</span></th></tr></thead>
        <tbody>{products.map((product) => {
          const status = stockStatus(product)
          return <tr key={product.id} className={!product.is_active ? 'inactive-row' : undefined}>
            <td data-label="Product"><strong>{product.name}</strong>{!product.is_active && <span className="inactive-label">Inactive</span>}</td>
            <td data-label="SKU / Barcode"><code className="sku-code">{product.sku}</code><small>{product.barcode || 'No barcode assigned'}</small></td>
            <td data-label="Category">{categoryNames.get(product.category_id) ?? 'Unknown'}</td>
            <td data-label="Price"><strong>₱{Number(product.selling_price).toFixed(2)}</strong><small>Cost ₱{Number(product.cost_price).toFixed(2)}</small></td>
            <td data-label="Stock"><div className="stock-cell"><strong>{product.current_stock}</strong><span className={`stock-status ${status.style}`}>{status.label}</span></div><small>Minimum stock: {product.minimum_stock}</small></td>
            <td data-label="Actions"><div className="row-actions"><button className="text-button" onClick={() => onEdit(product)}>Edit</button>{product.is_active && <button className="text-button" onClick={() => onAdjustStock(product)}>Adjust</button>}<a className="text-button" href={`/inventory?product_id=${product.id}`}>History</a>{product.is_active && <button className="text-button danger" onClick={() => onDeactivate(product)}>Deactivate</button>}</div></td>
          </tr>
        })}</tbody>
      </table>
    </div>
  )
}
