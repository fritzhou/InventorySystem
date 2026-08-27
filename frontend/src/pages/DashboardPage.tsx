/* eslint-disable react-refresh/only-export-components */
import { useEffect, useState } from 'react'
import { api } from '../services/api'
import type { InventoryStatus, ReportSummary, TopProduct, TrendPoint } from '../types/report'
import { formatMoney } from '../utils/money'
import { EmptyState, LoadingState, PageHeader, StatCard } from '../components/ui'

const zero: ReportSummary = { sales_total: '0.00', transaction_count: 0, items_sold: 0, gross_profit: '0.00', profit_complete: true, operating_expenses:'0.00', net_profit:'0.00', net_profit_complete:true, average_transaction_value: '0.00', total_active_products: 0, total_units_in_stock: 0, low_stock_count: 0, out_of_stock_count: 0 }

function TrendChart({ data }: { data: TrendPoint[] }) {
  const maxMagnitude = Math.max(...data.map((point) => Math.abs(Number(point.sales))), 0)
  return <div className="trend-chart" aria-label="Sales trend chart">{data.map((point) => { const value = Number(point.sales); return <div className="trend-column" key={point.date} title={`${point.date}: ${formatMoney(point.sales)}`}><div className={value < 0 ? 'refund-bar' : ''} style={{ height: maxMagnitude ? `${Math.max(4, Math.abs(value) / maxMagnitude * 100)}%` : '2px' }} /><small>{point.date.slice(5)}</small></div> })}</div>
}

function Metrics({ summary }: { summary: ReportSummary }) {
  return <div className="metric-grid">
    <StatCard label="Total Products" value={summary.total_active_products} icon="products" />
    <StatCard label="Revenue" value={formatMoney(summary.sales_total)} icon="sales" tone="success" />
    <StatCard label="Transactions" value={summary.transaction_count} icon="activity" detail={`${summary.items_sold} items sold`} />
    <StatCard label="Low Stock" value={summary.low_stock_count} icon="warning" tone="warning" detail={`${summary.out_of_stock_count} out of stock`} />
    <StatCard label="Gross Profit" value={formatMoney(summary.gross_profit)} icon="money" detail={!summary.profit_complete ? 'Some sales lack cost snapshots' : undefined} />
    <StatCard label="Operating Expenses" value={formatMoney(summary.operating_expenses ?? '0.00')} icon="money" tone="danger" />
    <StatCard label="Net Profit" value={summary.net_profit_complete !== false && summary.net_profit != null ? formatMoney(summary.net_profit) : 'Unavailable'} icon="activity" tone="success" detail={summary.net_profit_complete === false ? 'Incomplete historical cost data' : undefined} />
  </div>
}

export function DashboardPage() {
  const [summary, setSummary] = useState(zero); const [top, setTop] = useState<TopProduct[]>([]); const [trend, setTrend] = useState<TrendPoint[]>([]); const [stock, setStock] = useState<InventoryStatus | null>(null); const [loading, setLoading] = useState(true); const [error, setError] = useState('')
  useEffect(() => { Promise.all([api.getReportSummary('', '', true), api.getSalesTrend(), api.getTopProducts('', '', 5), api.getInventoryStatus()]).then(([s, t, p, i]) => { setSummary(s); setTrend(t); setTop(p); setStock(i) }).catch(() => setError('Dashboard could not be loaded.')).finally(() => setLoading(false)) }, [])
  return <><PageHeader eyebrow="Business overview" title="Dashboard" description="A live view of sales performance and inventory health." actions={<a className="button primary button-link" href="/reports">View Reports</a>} />
    {error && <div className="error history-error" role="alert">{error}</div>}{loading ? <LoadingState label="Loading dashboard" /> : <><Metrics summary={summary} />
      <div className="report-grid"><section className="card report-card wide"><h2>Sales over time</h2><TrendChart data={trend} /></section><section className="card report-card"><h2>Top Products</h2>{top.length ? top.map((p, i) => <div className="rank-row" key={`${p.product_id}-${p.sku}`}><b>{i + 1}</b><span><strong>{p.product_name}</strong><small>{p.quantity_sold} sold · {p.sku}</small></span><strong>{formatMoney(p.revenue)}</strong></div>) : <p className="empty compact">No sales in this period.</p>}</section>
      <section className="card report-card"><h2>Stock alerts</h2>{stock && [...stock.out_of_stock, ...stock.low_stock].slice(0, 6).map((p) => <div className="stock-row" key={p.product_id}><span><strong>{p.product_name}</strong><small>{p.sku}</small></span><b>{p.current_stock} / min {p.minimum_stock}</b></div>)}{stock && !stock.out_of_stock.length && !stock.low_stock.length && <EmptyState title="Stock levels look healthy" description="There are no low-stock products requiring attention." />}<a className="text-button report-link" href="/">Manage products →</a></section></div></>}
  </>
}

export { Metrics, TrendChart, zero }
