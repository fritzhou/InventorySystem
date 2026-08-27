import { useEffect, useMemo, useState, type FormEvent } from 'react'

import { CategoryForm } from '../components/CategoryForm'
import { ProductForm } from '../components/ProductForm'
import { ProductTable } from '../components/ProductTable'
import { api } from '../services/api'
import { useProducts } from '../hooks/useProducts'
import type { Category } from '../types/category'
import type { Product, ProductInput, ProductUpdateInput } from '../types/product'

export function ProductsPage() {
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [showInactive, setShowInactive] = useState(false)
  const filters = useMemo(() => ({ search, categoryId, activeOnly: !showInactive }), [search, categoryId, showInactive])
  const { products, isLoading, error, refresh } = useProducts(filters)
  const [categories, setCategories] = useState<Category[]>([])
  const [categoryError, setCategoryError] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isCategorySaving, setIsCategorySaving] = useState(false)
  const [editingProduct, setEditingProduct] = useState<Product | null>(null)
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [confirmingProduct, setConfirmingProduct] = useState<Product | null>(null)

  useEffect(() => {
    api.getCategories().then(setCategories).catch((requestError: unknown) => {
      setCategoryError(requestError instanceof Error ? requestError.message : 'Could not load categories.')
    })
  }, [])

  const openCreate = () => { setEditingProduct(null); setFormError(null); setIsFormOpen(true) }
  const openEdit = (product: Product) => { setEditingProduct(product); setFormError(null); setIsFormOpen(true) }
  const closeForm = () => { if (!isSaving) setIsFormOpen(false) }
  const submitSearch = (event: FormEvent) => { event.preventDefault(); setSearch(searchInput) }

  const saveProduct = async (values: ProductInput | ProductUpdateInput) => {
    setIsSaving(true); setFormError(null)
    try {
      if (editingProduct) await api.updateProduct(editingProduct.id, values as ProductUpdateInput)
      else await api.createProduct(values as ProductInput)
      setIsFormOpen(false); refresh()
    } catch (requestError) {
      setFormError(requestError instanceof Error ? requestError.message : 'Could not save the product.')
    } finally { setIsSaving(false) }
  }

  const createCategory = async (name: string, description: string) => {
    setIsCategorySaving(true); setCategoryError(null)
    try {
      const category = await api.createCategory({ name, description: description || null })
      setCategories((current) => [...current, category].sort((a, b) => a.name.localeCompare(b.name)))
      return true
    } catch (requestError) {
      setCategoryError(requestError instanceof Error ? requestError.message : 'Could not create the category.')
      return false
    } finally { setIsCategorySaving(false) }
  }

  const deactivate = async () => {
    if (!confirmingProduct) return
    setIsSaving(true); setFormError(null)
    try {
      await api.deactivateProduct(confirmingProduct.id)
      setConfirmingProduct(null); refresh()
    } catch (requestError) {
      setFormError(requestError instanceof Error ? requestError.message : 'Could not deactivate the product.')
    } finally { setIsSaving(false) }
  }

  return (
    <section aria-labelledby="products-heading">
      <div className="page-heading"><div><span className="eyebrow">Inventory catalog</span><h1 id="products-heading">Products</h1><p>Manage product details, pricing, barcodes, and stock thresholds.</p></div><button className="button primary" onClick={openCreate}>+ New product</button></div>
      <div className="management-layout">
        <div className="card product-list-card">
          <form className="filters" onSubmit={submitSearch}>
            <label className="search-field"><span className="sr-only">Search products</span><input placeholder="Search name, SKU, or barcode" value={searchInput} onChange={(event) => setSearchInput(event.target.value)} /><button className="button secondary">Search</button></label>
            <label><span className="sr-only">Filter by category</span><select value={categoryId} onChange={(event) => setCategoryId(event.target.value)}><option value="">All categories</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>
            <label className="checkbox"><input type="checkbox" checked={showInactive} onChange={(event) => setShowInactive(event.target.checked)} /> Include inactive</label>
          </form>
          <div className="list-summary"><strong>{products.length} products</strong>{search && <button className="text-button" onClick={() => { setSearch(''); setSearchInput('') }}>Clear search</button>}</div>
          {isLoading && <p role="status" className="loading">Loading products…</p>}
          {error && <p className="error" role="alert">{error} <button className="text-button" onClick={refresh}>Retry</button></p>}
          {!isLoading && !error && <ProductTable products={products} categories={categories} onEdit={openEdit} onDeactivate={setConfirmingProduct} />}
        </div>
        <aside className="card categories-card"><div><span className="eyebrow">Organization</span><h2>Categories</h2></div><ul className="category-list">{categories.map((category) => <li key={category.id}><strong>{category.name}</strong><span>{category.description || 'No description'}</span></li>)}</ul>{categories.length === 0 && !categoryError && <p className="muted">Create your first category before adding products.</p>}<CategoryForm isSaving={isCategorySaving} error={categoryError} onSubmit={createCategory} /></aside>
      </div>
      {isFormOpen && <div className="modal-backdrop" role="presentation"><section className="modal" role="dialog" aria-modal="true" aria-labelledby="product-form-title"><div className="modal-heading"><div><span className="eyebrow">{editingProduct ? 'Update catalog' : 'Catalog setup'}</span><h2 id="product-form-title">{editingProduct ? 'Edit product' : 'Create product'}</h2></div><button className="icon-button" aria-label="Close" onClick={closeForm}>×</button></div>{categories.length === 0 && <p className="notice">Create a category before adding a product.</p>}<ProductForm categories={categories} product={editingProduct} isSaving={isSaving} error={formError} onCancel={closeForm} onSubmit={saveProduct} /></section></div>}
      {confirmingProduct && <div className="modal-backdrop" role="presentation"><section className="modal confirm-modal" role="alertdialog" aria-modal="true" aria-labelledby="deactivate-title"><h2 id="deactivate-title">Deactivate {confirmingProduct.name}?</h2><p>The product will no longer appear in active product searches, but its record will remain available for business history.</p>{formError && <p className="error">{formError}</p>}<div className="form-actions"><button className="button secondary" disabled={isSaving} onClick={() => setConfirmingProduct(null)}>Cancel</button><button className="button danger-button" disabled={isSaving} onClick={deactivate}>{isSaving ? 'Deactivating…' : 'Deactivate product'}</button></div></section></div>}
    </section>
  )
}
