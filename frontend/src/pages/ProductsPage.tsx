import { useEffect, useMemo, useState, type FormEvent } from 'react'

import { CategoryForm } from '../components/CategoryForm'
import { BarcodeScanner } from '../components/BarcodeScanner'
import { ProductForm } from '../components/ProductForm'
import { ProductTable } from '../components/ProductTable'
import { StockAdjustmentModal } from '../components/StockAdjustmentModal'
import { api, ApiError } from '../services/api'
import { useProducts } from '../hooks/useProducts'
import type { Category } from '../types/category'
import type { ExternalProduct, Product, ProductInput, ProductUpdateInput } from '../types/product'

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
  const [adjustingProduct, setAdjustingProduct] = useState<Product | null>(null)
  const [adjustmentError, setAdjustmentError] = useState<string | null>(null)
  const [isScannerOpen, setIsScannerOpen] = useState(false)
  const [scannerKey, setScannerKey] = useState(0)
  const [scannedBarcode, setScannedBarcode] = useState('')
  const [scannedProduct, setScannedProduct] = useState<Product | null>(null)
  const [externalProduct, setExternalProduct] = useState<ExternalProduct | null>(null)
  const [suggestedCategoryId, setSuggestedCategoryId] = useState('')
  const [scanStatus, setScanStatus] = useState<'scanning' | 'looking-up' | 'found' | 'external' | 'unknown' | 'error'>('scanning')
  const [scanError, setScanError] = useState('')

  useEffect(() => {
    api.getCategories().then(setCategories).catch((requestError: unknown) => {
      setCategoryError(requestError instanceof Error ? requestError.message : 'Could not load categories.')
    })
  }, [])

  const openCreate = (barcode = '') => { setEditingProduct(null); setFormError(null); setScannedBarcode(barcode); setIsFormOpen(true) }
  const openEdit = (product: Product) => { setEditingProduct(product); setFormError(null); setIsFormOpen(true) }
  const closeForm = () => { if (!isSaving) setIsFormOpen(false) }
  const submitSearch = (event: FormEvent) => { event.preventDefault(); setSearch(searchInput) }

  const openScanner = () => {
    setScannedBarcode(''); setScannedProduct(null); setExternalProduct(null); setSuggestedCategoryId(''); setScanStatus('scanning'); setScanError('')
    setScannerKey((key) => key + 1); setIsScannerOpen(true)
  }
  const closeScanner = () => setIsScannerOpen(false)
  const handleBarcode = async (barcode: string) => {
    setScannedBarcode(barcode); setScanStatus('looking-up'); setScanError('')
    try {
      const lookup = await api.lookupProductByBarcode(barcode)
      if (lookup.source === 'stockflow' && lookup.product) {
        setScannedProduct(lookup.product); setScanStatus('found')
      } else if (lookup.found && lookup.external_product) {
        const categoryText = lookup.external_product.category_text?.toLocaleLowerCase() ?? ''
        const suggestion = categories.find((category) => {
          const name = category.name.toLocaleLowerCase()
          return categoryText.split(',').some((item) => item.trim() === name) || categoryText.includes(name)
        })
        setExternalProduct(lookup.external_product); setSuggestedCategoryId(suggestion?.id ?? ''); setScanStatus('external')
      } else setScanStatus('unknown')
    } catch (requestError) {
      setScannedProduct(null)
      if (requestError instanceof ApiError && requestError.status === 404) setScanStatus('unknown')
      else { setScanStatus('error'); setScanError(requestError instanceof Error ? requestError.message : 'Could not look up this barcode.') }
    }
  }
  const retryScanner = () => {
    setScannedBarcode(''); setScannedProduct(null); setExternalProduct(null); setSuggestedCategoryId(''); setScanStatus('scanning'); setScanError('')
    setScannerKey((key) => key + 1)
  }
  const addScannedProduct = () => { setIsScannerOpen(false); setEditingProduct(null); setFormError(null); setIsFormOpen(true) }
  const editScannedProduct = () => { if (scannedProduct) { setIsScannerOpen(false); openEdit(scannedProduct) } }

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

  const adjustStock = async (value: import('../types/inventory').StockAdjustmentInput) => {
    if (!adjustingProduct) return
    setIsSaving(true); setAdjustmentError(null)
    try { await api.adjustStock(adjustingProduct.id, value); setAdjustingProduct(null); refresh() }
    catch (requestError) { setAdjustmentError(requestError instanceof Error ? requestError.message : 'Stock adjustment could not be completed.') }
    finally { setIsSaving(false) }
  }

  return (
    <section aria-labelledby="products-heading">
      <div className="page-heading"><div><span className="eyebrow">Inventory catalog</span><h1 id="products-heading">Products</h1><p>Manage product details, pricing, barcodes, and stock thresholds.</p></div><div className="heading-actions"><button className="button secondary" onClick={openScanner}>Scan barcode</button><button className="button primary" onClick={() => openCreate()}>+ New product</button></div></div>
      <div className="management-layout" aria-label="Product catalog workspace">
        <div className="card product-list-card">
          <form className="filters" onSubmit={submitSearch}>
            <label className="search-field"><span className="sr-only">Search products</span><input placeholder="Search name, SKU, or barcode" value={searchInput} onChange={(event) => setSearchInput(event.target.value)} /><button className="button secondary">Search</button></label>
            <label><span className="sr-only">Filter by category</span><select value={categoryId} onChange={(event) => setCategoryId(event.target.value)}><option value="">All categories</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>
            <label className="checkbox"><input type="checkbox" checked={showInactive} onChange={(event) => setShowInactive(event.target.checked)} /> Include inactive</label>
          </form>
          <div className="list-summary"><strong>{products.length} products</strong>{search && <button className="text-button" onClick={() => { setSearch(''); setSearchInput('') }}>Clear search</button>}</div>
          {isLoading && <p role="status" className="loading">Loading products…</p>}
          {error && <p className="error" role="alert">{error} <button className="text-button" onClick={refresh}>Retry</button></p>}
          {!isLoading && !error && <ProductTable products={products} categories={categories} onEdit={openEdit} onDeactivate={setConfirmingProduct} onAdjustStock={(product) => { setAdjustmentError(null); setAdjustingProduct(product) }} />}
        </div>
        <aside className="card categories-card"><div><span className="eyebrow">Organization</span><h2>Categories</h2></div><ul className="category-list">{categories.map((category) => <li key={category.id}><strong>{category.name}</strong><span>{category.description || 'No description'}</span></li>)}</ul>{categories.length === 0 && !categoryError && <p className="muted">Create your first category before adding products.</p>}<CategoryForm isSaving={isCategorySaving} error={categoryError} onSubmit={createCategory} /></aside>
      </div>
      {isFormOpen && <div className="modal-backdrop" role="presentation"><section className="modal" role="dialog" aria-modal="true" aria-labelledby="product-form-title"><div className="modal-heading"><div><span className="eyebrow">{editingProduct ? 'Update catalog' : 'Catalog setup'}</span><h2 id="product-form-title">{editingProduct ? 'Edit product' : 'Create product'}</h2></div><button className="icon-button" aria-label="Close" onClick={closeForm}>×</button></div>{categories.length === 0 && <p className="notice">Create a category before adding a product.</p>}<ProductForm categories={categories} product={editingProduct} initialBarcode={editingProduct ? '' : scannedBarcode} initialName={editingProduct ? '' : externalProduct?.product_name ?? ''} initialCategoryId={editingProduct ? '' : suggestedCategoryId} isSaving={isSaving} error={formError} onCancel={closeForm} onSubmit={saveProduct} /></section></div>}
      {isScannerOpen && <div className="modal-backdrop scanner-backdrop" role="presentation"><section className="modal scanner-modal" role="dialog" aria-modal="true" aria-labelledby="scanner-title"><div className="modal-heading"><div><span className="eyebrow">Camera scanner</span><h2 id="scanner-title">Scan barcode</h2></div><button className="icon-button" aria-label="Close scanner" onClick={closeScanner}>×</button></div>
        {scanStatus === 'scanning' && <BarcodeScanner key={scannerKey} onDetected={handleBarcode} />}
        {scanStatus === 'looking-up' && <div className="scan-result" role="status"><span className="success-mark">✓</span><h3>Barcode detected</h3><code>{scannedBarcode}</code><p>Searching product information...</p></div>}
        {scanStatus === 'found' && scannedProduct && <div className="scan-result"><span className="success-mark">✓</span><p className="success-copy">Scan successful</p><h3>{scannedProduct.name}</h3><dl><div><dt>SKU</dt><dd>{scannedProduct.sku}</dd></div><div><dt>Barcode</dt><dd>{scannedProduct.barcode}</dd></div><div><dt>Category</dt><dd>{categories.find((item) => item.id === scannedProduct.category_id)?.name ?? 'Uncategorized'}</dd></div><div><dt>Selling price</dt><dd>${Number(scannedProduct.selling_price).toFixed(2)}</dd></div><div><dt>Current stock</dt><dd>{scannedProduct.current_stock}</dd></div><div><dt>Minimum stock</dt><dd>{scannedProduct.minimum_stock}</dd></div><div><dt>Stock status</dt><dd>{scannedProduct.current_stock === 0 ? 'Out of stock' : scannedProduct.current_stock <= scannedProduct.minimum_stock ? 'Low stock' : 'In stock'}</dd></div></dl><div className="form-actions"><button className="button secondary" onClick={retryScanner}>Retry scanning</button><button className="button primary" onClick={editScannedProduct}>Edit Product</button></div></div>}
        {scanStatus === 'external' && externalProduct && <div className="scan-result external-result"><p className="external-copy">Found from external product database</p>{externalProduct.image_url && <img className="external-product-image" src={externalProduct.image_url} alt="External product preview" />}<h3>{externalProduct.product_name ?? 'Name unavailable'}</h3><dl><div><dt>Barcode</dt><dd>{externalProduct.barcode}</dd></div>{externalProduct.brand && <div><dt>Brand</dt><dd>{externalProduct.brand}</dd></div>}{externalProduct.category_text && <div><dt>Category information</dt><dd>{externalProduct.category_text}</dd></div>}{externalProduct.package_size && <div><dt>Package size</dt><dd>{externalProduct.package_size}</dd></div>}</dl><p className="muted">Review all details and enter SKU, prices, and stock before saving.</p><div className="form-actions"><button className="button secondary" onClick={retryScanner}>Retry scanning</button><button className="button primary" onClick={addScannedProduct}>Add to Inventory</button></div></div>}
        {scanStatus === 'unknown' && <div className="scan-result"><h3>Product information not found</h3><p>No StockFlow or external product information was found for barcode <strong>{scannedBarcode}</strong>.</p><div className="form-actions"><button className="button secondary" onClick={retryScanner}>Retry scanning</button><button className="button primary" onClick={addScannedProduct}>Add Product</button></div></div>}
        {scanStatus === 'error' && <div className="scan-result"><p className="error" role="alert">{scanError}</p><button className="button secondary" onClick={retryScanner}>Retry scanning</button></div>}
        <button className="button scanner-close" onClick={closeScanner}>Close scanner</button>
      </section></div>}
      {adjustingProduct && <StockAdjustmentModal product={adjustingProduct} saving={isSaving} error={adjustmentError} onCancel={() => !isSaving && setAdjustingProduct(null)} onConfirm={adjustStock} />}
      {confirmingProduct && <div className="modal-backdrop" role="presentation"><section className="modal confirm-modal" role="alertdialog" aria-modal="true" aria-labelledby="deactivate-title"><h2 id="deactivate-title">Deactivate {confirmingProduct.name}?</h2><p>The product will no longer appear in active product searches, but its record will remain available for business history.</p>{formError && <p className="error">{formError}</p>}<div className="form-actions"><button className="button secondary" disabled={isSaving} onClick={() => setConfirmingProduct(null)}>Cancel</button><button className="button danger-button" disabled={isSaving} onClick={deactivate}>{isSaving ? 'Deactivating…' : 'Deactivate product'}</button></div></section></div>}
    </section>
  )
}
