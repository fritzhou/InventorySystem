import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../services/api'
import type { InventoryMovement, InventoryMovementPage, MovementType } from '../types/inventory'

const empty: InventoryMovementPage = { items: [], page: 1, page_size: 20, total_items: 0, total_pages: 0 }
export function InventoryHistoryPage() {
  const params = new URLSearchParams(window.location.search)
  const initialProduct = params.get('product_id') ?? ''
  const [draft, setDraft] = useState({ search: '', movementType: '' as MovementType | '', startDate: '', endDate: '' })
  const [filters, setFilters] = useState({ ...draft, productId: initialProduct })
  const [page, setPage] = useState(1); const [data, setData] = useState(empty); const [loading, setLoading] = useState(true); const [error, setError] = useState('')
  useEffect(() => { setLoading(true); setError(''); api.getInventoryMovements({ ...filters, page }).then(setData).catch((e: unknown) => setError(e instanceof Error ? e.message : 'Inventory history could not be loaded.')).finally(() => setLoading(false)) }, [filters, page])
  const apply = (e: FormEvent) => { e.preventDefault(); setPage(1); setFilters({ ...draft, productId: initialProduct }) }
  const clear = () => { const reset = { search: '', movementType: '' as MovementType | '', startDate: '', endDate: '' }; setDraft(reset); setPage(1); setFilters({ ...reset, productId: initialProduct }) }
  return <section><div className="page-heading"><div><span className="eyebrow">Audit trail</span><h1>Inventory History</h1><p>Review every recorded stock increase and decrease.</p></div></div>
    <form className="card history-filters" onSubmit={apply}><label className="history-search">Product<input placeholder="Product name or SKU" value={draft.search} onChange={(e) => setDraft({ ...draft, search: e.target.value })} /></label><label>Movement Type<select value={draft.movementType} onChange={(e) => setDraft({ ...draft, movementType: e.target.value as MovementType | '' })}><option value="">All types</option>{['RESTOCK','SALE','DAMAGE','CORRECTION'].map(x => <option key={x}>{x}</option>)}</select></label><label>From Date<input type="date" value={draft.startDate} onChange={(e) => setDraft({ ...draft, startDate: e.target.value })} /></label><label>To Date<input type="date" value={draft.endDate} onChange={(e) => setDraft({ ...draft, endDate: e.target.value })} /></label><button className="button primary">Apply Filters</button><button type="button" className="button secondary" onClick={clear}>Clear Filters</button></form>
    {error && <p className="error history-error" role="alert">{error}</p>}{loading ? <p className="loading">Loading inventory history…</p> : <div className="card movement-list">{data.items.length ? data.items.map((m: InventoryMovement) => <article className="movement-row" key={m.id}><div><strong>{m.product.name}</strong><small>{m.product.sku}{!m.product.is_active ? ' · Inactive' : ''}</small></div><span className={`movement-type ${m.movement_type.toLowerCase()}`}>{m.movement_type}</span><strong className={m.quantity_change >= 0 ? 'positive' : 'negative'}>{m.quantity_change >= 0 ? '+' : ''}{m.quantity_change} units</strong><span>{m.stock_before} → {m.stock_after}</span><div><time>{new Date(m.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</time>{m.receipt_number && <small>Receipt {m.receipt_number}</small>}{m.po_number && <small>Purchase Order: {m.po_number}</small>}{m.note && <small>{m.note}</small>}</div></article>) : <div className="empty">No inventory movements match these filters.</div>}</div>}
    {data.total_pages > 1 && <div className="pagination"><button className="button secondary" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous</button><span>Page {page} of {data.total_pages}</span><button className="button secondary" disabled={page >= data.total_pages} onClick={() => setPage(p => p + 1)}>Next</button></div>}
  </section>
}
