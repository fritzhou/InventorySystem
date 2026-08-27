/* eslint-disable react-refresh/only-export-components */
import { useEffect, useState } from 'react'
import { api } from '../services/api'
import type { InventoryStatus, ReportSummary, TopProduct, TrendPoint } from '../types/report'
import { formatMoney } from '../utils/money'

const zero: ReportSummary = { sales_total: '0.00', transaction_count: 0, items_sold: 0, gross_profit: '0.00', profit_complete: true, average_transaction_value: '0.00', total_active_products: 0, total_units_in_stock: 0, low_stock_count: 0, out_of_stock_count: 0 }

function TrendChart({ data }: { data: TrendPoint[] }) {
  const maxMagnitude = Math.max(...data.map((point) => Math.abs(Number(point.sales))), 0)
  return <div className="trend-chart" aria-label="Sales trend chart">{data.map((point) => { const value = Number(point.sales); return <div className="trend-column" key={point.date} title={`${point.date}: ${formatMoney(point.sales)}`}><div className={value < 0 ? 'refund-bar' : ''} style={{ height: maxMagnitude ? `${Math.max(4, Math.abs(value) / maxMagnitude * 100)}%` : '2px' }} /><small>{point.date.slice(5)}</small></div> })}</div>
}

function Metrics({ summary }: { summary: ReportSummary }) {
  return <div className="metric-grid">
    <article className="metric-card"><span>Revenue</span><strong>{formatMoney(summary.sales_total)}</strong></article>
    <article className="metric-card"><span>Transactions</span><strong>{summary.transaction_count}</strong></article>
    <article className="metric-card"><span>Items Sold</span><strong>{summary.items_sold}</strong></article>
    <article className="metric-card"><span>Gross Profit</span><strong>{formatMoney(summary.gross_profit)}</strong>{!summary.profit_complete && <small>Partial — some sales lack cost snapshots</small>}</article>
    <article className="metric-card"><span>Low Stock</span><strong>{summary.low_stock_count}</strong></article>
    <article className="metric-card"><span>Out of Stock</span><strong>{summary.out_of_stock_count}</strong></article>
  </div>
}

export function DashboardPage() {
  const [summary, setSummary] = useState(zero); const [top, setTop] = useState<TopProduct[]>([]); const [trend, setTrend] = useState<TrendPoint[]>([]); const [stock, setStock] = useState<InventoryStatus | null>(null); const [loading, setLoading] = useState(true); const [error, setError] = useState('')
  useEffect(() => { Promise.all([api.getReportSummary('', '', true), api.getSalesTrend(), api.getTopProducts('', '', 5), api.getInventoryStatus()]).then(([s, t, p, i]) => { setSummary(s); setTrend(t); setTop(p); setStock(i) }).catch(() => setError('Dashboard could not be loaded.')).finally(() => setLoading(false)) }, [])
  return <><div className="page-heading"><div><span className="eyebrow">Business overview</span><h1>Dashboard</h1><p>Today’s performance and current inventory health.</p></div><a className="button primary button-link" href="/reports">View Reports</a></div>
    {error && <div className="error history-error" role="alert">{error}</div>}{loading ? <p className="loading">Loading dashboard…</p> : <><Metrics summary={summary} />
      <div className="report-grid"><section className="card report-card wide"><h2>Sales over time</h2><TrendChart data={trend} /></section><section className="card report-card"><h2>Top Products</h2>{top.length ? top.map((p, i) => <div className="rank-row" key={`${p.product_id}-${p.sku}`}><b>{i + 1}</b><span><strong>{p.product_name}</strong><small>{p.quantity_sold} sold · {p.sku}</small></span><strong>{formatMoney(p.revenue)}</strong></div>) : <p className="empty compact">No sales in this period.</p>}</section>
      <section className="card report-card"><h2>Stock alerts</h2>{stock && [...stock.out_of_stock, ...stock.low_stock].slice(0, 6).map((p) => <div className="stock-row" key={p.product_id}><span><strong>{p.product_name}</strong><small>{p.sku}</small></span><b>{p.current_stock} / min {p.minimum_stock}</b></div>)}{stock && !stock.out_of_stock.length && !stock.low_stock.length && <p className="empty compact">Stock levels look healthy.</p>}<a className="text-button report-link" href="/">Manage products →</a></section></div></>}
  </>
}

export { Metrics, TrendChart, zero }
