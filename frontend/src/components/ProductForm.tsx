import { useEffect, useState, type FormEvent } from 'react'

import type { Category } from '../types/category'
import type { Product, ProductInput, ProductUpdateInput } from '../types/product'

interface ProductFormProps {
  categories: Category[]
  product: Product | null
  isSaving: boolean
  error: string | null
  onCancel: () => void
  onSubmit: (value: ProductInput | ProductUpdateInput) => Promise<void>
}

const emptyProduct: ProductInput = {
  name: '', sku: '', barcode: null, category_id: '', cost_price: '', selling_price: '', current_stock: 0, minimum_stock: 0,
}

export function ProductForm({ categories, product, isSaving, error, onCancel, onSubmit }: ProductFormProps) {
  const [values, setValues] = useState<ProductInput>(emptyProduct)

  useEffect(() => {
    setValues(product ? {
      name: product.name, sku: product.sku, barcode: product.barcode, category_id: product.category_id,
      cost_price: product.cost_price, selling_price: product.selling_price,
      current_stock: product.current_stock, minimum_stock: product.minimum_stock,
    } : emptyProduct)
  }, [product])

  const update = (field: keyof ProductInput, value: string | number | null) => setValues((current) => ({ ...current, [field]: value }))
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const normalized = { ...values, name: values.name.trim(), sku: values.sku.trim(), barcode: values.barcode?.trim() || null }
    if (product) {
      await onSubmit({
        name: normalized.name, sku: normalized.sku, barcode: normalized.barcode, category_id: normalized.category_id,
        cost_price: normalized.cost_price, selling_price: normalized.selling_price, minimum_stock: normalized.minimum_stock,
      })
    } else {
      await onSubmit(normalized)
    }
  }

  return (
    <form className="product-form" onSubmit={submit}>
      <div className="form-grid">
        <label className="wide">Product name<input required maxLength={160} value={values.name} onChange={(event) => update('name', event.target.value)} /></label>
        <label>SKU<input required maxLength={64} value={values.sku} onChange={(event) => update('sku', event.target.value)} /></label>
        <label>Barcode <span className="optional">optional</span><input maxLength={64} value={values.barcode ?? ''} onChange={(event) => update('barcode', event.target.value)} /></label>
        <label className="wide">Category<select required value={values.category_id} onChange={(event) => update('category_id', event.target.value)}><option value="">Select a category</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>
        <label>Cost price<input required min="0" step="0.01" inputMode="decimal" type="number" value={values.cost_price} onChange={(event) => update('cost_price', event.target.value)} /></label>
        <label>Selling price<input required min="0" step="0.01" inputMode="decimal" type="number" value={values.selling_price} onChange={(event) => update('selling_price', event.target.value)} /></label>
        {!product && <label>Opening stock<input required min="0" step="1" inputMode="numeric" type="number" value={values.current_stock} onChange={(event) => update('current_stock', Number(event.target.value))} /></label>}
        <label>Low-stock threshold<input required min="0" step="1" inputMode="numeric" type="number" value={values.minimum_stock} onChange={(event) => update('minimum_stock', Number(event.target.value))} /></label>
      </div>
      {product && <p className="form-note">Stock is read-only here. Inventory changes will use audited stock movements in the Inventory phase.</p>}
      {error && <p className="error" role="alert">{error}</p>}
      <div className="form-actions"><button type="button" className="button secondary" onClick={onCancel}>Cancel</button><button className="button primary" disabled={isSaving || categories.length === 0}>{isSaving ? 'Saving…' : product ? 'Save changes' : 'Create product'}</button></div>
    </form>
  )
}
