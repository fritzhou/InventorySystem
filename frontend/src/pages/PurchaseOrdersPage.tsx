import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../services/api'
import type { Product } from '../types/product'
import type { POInput, POPage, PurchaseOrder, Supplier } from '../types/purchasing'
import { formatMoney } from '../utils/money'

const emptyPage: POPage = { items: [], page: 1, page_size: 20, total_items: 0, total_pages: 0 }
const statuses = ['DRAFT', 'ORDERED', 'PARTIALLY_RECEIVED', 'RECEIVED', 'CANCELLED']
type Filters = { search: string; supplierId: string; status: string; fromDate: string; toDate: string }
const emptyFilters: Filters = { search: '', supplierId: '', status: '', fromDate: '', toDate: '' }

export function PurchaseOrdersPage() {
  const id = new URLSearchParams(window.location.search).get('id')
  const creating = window.location.pathname === '/purchase-orders/new'
  const editing = window.location.pathname === '/purchase-orders/edit'
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [po, setPo] = useState<PurchaseOrder | null>(null)
  const [data, setData] = useState(emptyPage)
  const [draft, setDraft] = useState(emptyFilters)
  const [filters, setFilters] = useState(emptyFilters)
  const [page, setPage] = useState(1)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getSuppliers('', true).then((x) => setSuppliers(x.items)).catch((e: Error) => setError(e.message))
    api.getProducts().then(setProducts).catch((e: Error) => setError(e.message))
  }, [])
  useEffect(() => {
    if (!id) return
    api.getPurchaseOrder(id).then(setPo).catch((e: Error) => setError(e.message))
  }, [id])
  useEffect(() => {
    if (id || creating || editing) return
    api.getPurchaseOrders({ ...filters, page }).then(setData).catch((e: Error) => setError(e.message))
  }, [id, creating, editing, filters, page])

  if (creating) return <POForm suppliers={suppliers} products={products} error={error} setError={setError} />
  if (editing && po) return <POForm suppliers={suppliers} products={products} purchaseOrder={po} error={error} setError={setError} />
  if (id && po) return <Detail po={po} reload={() => api.getPurchaseOrder(po.id).then(setPo)} error={error} setError={setError} />

  const apply = (event: FormEvent) => { event.preventDefault(); setPage(1); setFilters(draft) }
  const clear = () => { setDraft(emptyFilters); setFilters(emptyFilters); setPage(1) }
  return <section>
    <div className="page-heading"><div><span className="eyebrow">Purchasing</span><h1>Purchase Orders</h1><p>Order and receive stock with an auditable workflow.</p></div><a className="button primary button-link" href="/purchase-orders/new">New Purchase Order</a></div>
    {error && <p className="error" role="alert">{error}</p>}
    <form className="card po-filters" onSubmit={apply}>
      <label>PO Number<input aria-label="PO Number" value={draft.search} onChange={(e) => setDraft({ ...draft, search: e.target.value })} /></label>
      <label>Supplier<select aria-label="Supplier filter" value={draft.supplierId} onChange={(e) => setDraft({ ...draft, supplierId: e.target.value })}><option value="">All suppliers</option>{suppliers.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
      <label>Status<select aria-label="Status filter" value={draft.status} onChange={(e) => setDraft({ ...draft, status: e.target.value })}><option value="">All statuses</option>{statuses.map((x) => <option key={x} value={x}>{x.replaceAll('_', ' ')}</option>)}</select></label>
      <label>From<input aria-label="From date" type="date" value={draft.fromDate} onChange={(e) => setDraft({ ...draft, fromDate: e.target.value })} /></label>
      <label>To<input aria-label="To date" type="date" value={draft.toDate} onChange={(e) => setDraft({ ...draft, toDate: e.target.value })} /></label>
      <button className="button primary">Apply</button><button type="button" className="button secondary" onClick={clear}>Clear</button>
    </form>
    <div className="card movement-list">{data.items.length ? data.items.map((x) => {
      const ordered = x.items.reduce((sum, item) => sum + item.ordered_quantity, 0)
      const received = x.items.reduce((sum, item) => sum + item.received_quantity, 0)
      return <article className="po-row" key={x.id}><div><b>{x.po_number}</b><small>{x.supplier.name}</small></div><span className="movement-type">{x.status.replaceAll('_', ' ')}</span><div>Ordered: {ordered}<small>Received: {received}</small></div><b>{formatMoney(x.subtotal)}</b><a className="button secondary button-link" href={`/purchase-orders?id=${x.id}`}>View</a></article>
    }) : <p className="empty">No purchase orders match these filters.</p>}</div>
    {data.total_pages > 1 && <div className="pagination"><button className="button secondary" disabled={page <= 1} onClick={() => setPage((x) => x - 1)}>Previous</button><span>Page {page} of {data.total_pages}</span><button className="button secondary" disabled={page >= data.total_pages} onClick={() => setPage((x) => x + 1)}>Next</button></div>}
  </section>
}

function POForm({ suppliers, products, purchaseOrder, error, setError }: { suppliers: Supplier[]; products: Product[]; purchaseOrder?: PurchaseOrder; error: string; setError: (x: string) => void }) {
  const [supplier, setSupplier] = useState(purchaseOrder?.supplier_id ?? '')
  const [expected, setExpected] = useState(purchaseOrder?.expected_date ?? '')
  const [notes, setNotes] = useState(purchaseOrder?.notes ?? '')
  const [productSearch, setProductSearch] = useState('')
  const [selectedProduct, setSelectedProduct] = useState('')
  const [lines, setLines] = useState<POInput['items']>(purchaseOrder?.items.map((x) => ({ product_id: x.product_id, quantity: x.ordered_quantity, unit_cost: x.unit_cost })) ?? [])
  const matches = products.filter((product) => {
    const term = productSearch.trim().toLowerCase()
    return !lines.some((line) => line.product_id === product.id) && (!term || product.name.toLowerCase().includes(term) || product.sku.toLowerCase().includes(term) || product.barcode?.toLowerCase().includes(term))
  })
  const add = () => {
    const product = products.find((x) => x.id === selectedProduct) ?? matches[0]
    if (!product) return
    setLines([...lines, { product_id: product.id, quantity: 1, unit_cost: String(product.cost_price) }]); setSelectedProduct(''); setProductSearch('')
  }
  const save = async (event: FormEvent) => {
    event.preventDefault()
    const payload = { supplier_id: supplier, expected_date: expected || null, notes: notes || null, items: lines }
    try {
      const result = purchaseOrder ? await api.updatePurchaseOrder(purchaseOrder.id, payload) : await api.createPurchaseOrder(payload)
      window.location.href = `/purchase-orders?id=${result.id}`
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Purchase order could not be saved.') }
  }
  return <section><div className="page-heading"><div><span className="eyebrow">Purchasing</span><h1>{purchaseOrder ? `Edit ${purchaseOrder.po_number}` : 'New Purchase Order'}</h1></div></div>{error && <p className="error" role="alert">{error}</p>}<form className="card po-form" onSubmit={save}>
    <label>Supplier<select required value={supplier} onChange={(e) => setSupplier(e.target.value)}><option value="">Select supplier</option>{suppliers.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
    <label>Expected Delivery<input type="date" value={expected} onChange={(e) => setExpected(e.target.value)} /></label><label>Notes<input value={notes} onChange={(e) => setNotes(e.target.value)} /></label>
    <h2>Products</h2><div className="product-selector"><input aria-label="Search products" placeholder="Search name, SKU, or barcode" value={productSearch} onChange={(e) => setProductSearch(e.target.value)} /><select aria-label="Product result" value={selectedProduct} onChange={(e) => setSelectedProduct(e.target.value)}><option value="">Select product</option>{matches.map((x) => <option value={x.id} key={x.id}>{x.name} · {x.sku}{x.barcode ? ` · ${x.barcode}` : ''}</option>)}</select><button type="button" className="button secondary" disabled={!selectedProduct && !matches.length} onClick={add}>Add Product</button></div>
    {lines.map((line, index) => { const product = products.find((x) => x.id === line.product_id); return <div className="po-line" key={line.product_id}><strong>{product?.name ?? purchaseOrder?.items.find((x) => x.product_id === line.product_id)?.product_name}</strong><input aria-label={`Quantity ${index + 1}`} type="number" min="1" value={line.quantity} onChange={(e) => setLines(lines.map((x, i) => i === index ? { ...x, quantity: Number(e.target.value) } : x))} /><input aria-label={`Unit cost ${index + 1}`} type="number" min="0" step=".01" value={line.unit_cost} onChange={(e) => setLines(lines.map((x, i) => i === index ? { ...x, unit_cost: e.target.value } : x))} /><b>{formatMoney((line.quantity * Number(line.unit_cost)).toFixed(2))}</b><button type="button" className="text-button danger" onClick={() => setLines(lines.filter((_, i) => i !== index))}>Remove</button></div> })}
    <h2>PO Total {formatMoney(lines.reduce((sum, line) => sum + line.quantity * Number(line.unit_cost), 0).toFixed(2))}</h2><div className="form-actions"><a className="button secondary button-link" href={purchaseOrder ? `/purchase-orders?id=${purchaseOrder.id}` : '/purchase-orders'}>Cancel</a><button disabled={!supplier || !lines.length} className="button primary">{purchaseOrder ? 'Save Changes' : 'Save Draft'}</button></div>
  </form></section>
}

function Detail({ po, reload, error, setError }: { po: PurchaseOrder; reload: () => void; error: string; setError: (x: string) => void }) {
  const [open, setOpen] = useState(false); const [amounts, setAmounts] = useState<Record<string, number>>({})
  const action = async (work: () => Promise<unknown>) => { try { await work(); setOpen(false); reload() } catch (caught) { setError(caught instanceof Error ? caught.message : 'Action failed.') } }
  return <section><a className="button secondary button-link back-button" href="/purchase-orders">Back</a><div className="page-heading"><div><span className="eyebrow">{po.status.replaceAll('_', ' ')}</span><h1>{po.po_number}</h1><p>{po.supplier.name}</p></div></div>{error && <p className="error" role="alert">{error}</p>}<div className="card po-form"><p>Ordered {po.order_date} · Expected {po.expected_date || '—'}</p><table><thead><tr><th>Product</th><th>Ordered</th><th>Received</th><th>Remaining</th><th>Cost</th></tr></thead><tbody>{po.items.map((item) => <tr key={item.id}><td>{item.product_name}<small>{item.sku}</small></td><td>{item.ordered_quantity}</td><td>{item.received_quantity}</td><td>{item.ordered_quantity - item.received_quantity}</td><td>{formatMoney(item.unit_cost)}</td></tr>)}</tbody></table><h2>Subtotal {formatMoney(po.subtotal)}</h2><div className="form-actions">{po.status === 'DRAFT' && <><a className="button secondary button-link" href={`/purchase-orders/edit?id=${po.id}`}>Edit</a><button className="button primary" onClick={() => action(() => api.markPurchaseOrderOrdered(po.id))}>Mark as Ordered</button></>}{['DRAFT', 'ORDERED'].includes(po.status) && <button className="button secondary" onClick={() => action(() => api.cancelPurchaseOrder(po.id))}>Cancel</button>}{['ORDERED', 'PARTIALLY_RECEIVED'].includes(po.status) && <button className="button primary" onClick={() => { setAmounts(Object.fromEntries(po.items.filter((x) => x.received_quantity < x.ordered_quantity).map((x) => [x.id, x.ordered_quantity - x.received_quantity]))); setOpen(true) }}>Receive Stock</button>}</div></div>
    {open && <div className="modal-backdrop"><div className="modal"><h2>Confirm Stock Receipt</h2>{po.items.filter((x) => x.received_quantity < x.ordered_quantity).map((item) => <label key={item.id}>{item.product_name} — remaining {item.ordered_quantity - item.received_quantity}<input type="number" min="0" max={item.ordered_quantity - item.received_quantity} value={amounts[item.id]} onChange={(e) => setAmounts({ ...amounts, [item.id]: Number(e.target.value) })} /></label>)}<p className="notice">Stock, movements, costs, and PO progress update in one transaction.</p><div className="form-actions"><button className="button secondary" onClick={() => setOpen(false)}>Back</button><button className="button primary" onClick={() => action(() => api.receivePurchaseOrder(po.id, Object.entries(amounts).filter(([, quantity]) => quantity > 0).map(([item_id, quantity]) => ({ item_id, quantity }))))}>Confirm Receipt</button></div></div></div>}
  </section>
}
