import { useCallback, useEffect, useState, type FormEvent } from 'react'

import { Receipt } from '../components/Receipt'
import { ReturnModal } from '../components/ReturnModal'
import { ReturnReceipt } from '../components/ReturnReceipt'
import { ApiError, api } from '../services/api'
import type { Sale, SaleReturn, SalesPage } from '../types/sale'
import { formatMoney } from '../utils/money'

const emptyPage: SalesPage = { items: [], page: 1, page_size: 20, total_items: 0, total_pages: 0 }

export function SalesHistoryPage() {
  const [search, setSearch] = useState('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [filters, setFilters] = useState({ search: '', from: '', to: '' })
  const [page, setPage] = useState(1)
  const [data, setData] = useState(emptyPage)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [sale, setSale] = useState<Sale | null>(null)
  const [detailError, setDetailError] = useState('')
  const [returning, setReturning] = useState(false)
  const [completedReturn, setCompletedReturn] = useState<SaleReturn | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try { setData(await api.getSales({ search: filters.search, startDate: filters.from, endDate: filters.to, page })) }
    catch { setError('Sales history could not be loaded.') }
    finally { setLoading(false) }
  }, [filters, page])

  useEffect(() => { void load() }, [load])

  const apply = (event: FormEvent) => {
    event.preventDefault()
    if (from && to && from > to) { setError('From date cannot be after To date'); return }
    setError(''); setPage(1); setFilters({ search, from, to })
  }
  const clear = () => { setSearch(''); setFrom(''); setTo(''); setError(''); setPage(1); setFilters({ search: '', from: '', to: '' }) }
  const openReceipt = async (id: string) => {
    setDetailError('')
    try { setSale(await api.getSale(id)) }
    catch (err) { setDetailError(err instanceof ApiError && err.status === 404 ? 'Receipt not found.' : 'Sale could not be loaded.') }
  }

  if (completedReturn) return <><button className="text-button back-button" onClick={() => { setCompletedReturn(null); setSale(null) }}>← Back to Sales History</button><ReturnReceipt value={completedReturn} /></>
  if (sale) { const available = sale.items.reduce((sum,item)=>sum+(item.returnable_quantity ?? item.quantity),0); return <><button className="text-button back-button" onClick={() => setSale(null)}>← Back to Sales History</button><Receipt sale={sale} /><section className="card return-summary"><h2>Return eligibility {available === 0 && <span className="fully-returned">FULLY RETURNED</span>}</h2>{sale.items.map(item=><div key={item.id}><span>{item.product_name}: Sold {item.quantity} · Returned {item.returned_quantity ?? 0} · Returnable {item.returnable_quantity ?? item.quantity}</span></div>)}{available>0&&<button className="button primary" onClick={()=>setReturning(true)}>Process Return</button>}</section>{returning&&<ReturnModal sale={sale} onCancel={()=>setReturning(false)} onComplete={setCompletedReturn}/>}</> }
  return <>
    <div className="page-heading"><div><span className="eyebrow">Transactions</span><h1>Sales History</h1><p>Find completed sales and reprint their receipts.</p></div></div>
    <form className="card history-filters" onSubmit={apply}>
      <label className="history-search">Search receipt<input aria-label="Search receipt" placeholder="Search receipt..." value={search} onChange={(e) => setSearch(e.target.value)} /></label>
      <label>From date<input aria-label="From date" type="date" value={from} onChange={(e) => setFrom(e.target.value)} /></label>
      <label>To date<input aria-label="To date" type="date" value={to} onChange={(e) => setTo(e.target.value)} /></label>
      <button className="button primary">Apply Filters</button><button type="button" className="button secondary" onClick={clear}>Clear Filters</button>
    </form>
    {error && <div className="error history-error" role="alert">{error}</div>}
    {detailError && <div className="error history-error" role="alert">{detailError}</div>}
    <section className="card history-list" aria-label="Completed sales history">
      {loading ? <p className="loading">Loading sales…</p> : data.items.length === 0 ? <p className="empty">No sales found.</p> : data.items.map((item) => <article className="sale-row" key={item.id}>
        <div><strong>{item.receipt_number}</strong><time>{new Date(item.created_at).toLocaleString()}</time></div>
        <span>{item.item_count} {item.item_count === 1 ? 'item' : 'items'}</span><strong>{formatMoney(item.total)}</strong><span>{item.payment_method.charAt(0).toUpperCase() + item.payment_method.slice(1)}</span>
        <button className="button secondary" onClick={() => void openReceipt(item.id)}>View Receipt</button>
      </article>)}
    </section>
    {!loading && data.items.length > 0 && <div className="pagination"><button className="button secondary" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>Previous</button><span>Page {data.page} of {data.total_pages}</span><button className="button secondary" disabled={page >= data.total_pages} onClick={() => setPage((p) => p + 1)}>Next</button></div>}
  </>
}
