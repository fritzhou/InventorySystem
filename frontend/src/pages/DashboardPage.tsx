/* eslint-disable react-refresh/only-export-components */
import { useEffect, useState } from 'react'
import { api } from '../services/api'
import type { InventoryStatus, ReportSummary, TopProduct, TrendPoint } from '../types/report'
import { formatMoney } from '../utils/money'
import { EmptyState, LoadingState, Notice, PageHeader, StatCard } from '../components/ui'

const zero: ReportSummary = { sales_total: '0.00', transaction_count: 0, items_sold: 0, gross_profit: '0.00', profit_complete: true, operating_expenses:'0.00', net_profit:'0.00', net_profit_complete:true, average_transaction_value: '0.00', total_active_products: 0, total_units_in_stock: 0, low_stock_count: 0, out_of_stock_count: 0 }

function TrendChart({ data }: { data: TrendPoint[] }) {
  const maxMagnitude = Math.max(...data.map((point) => Math.abs(Number(point.sales))), 0)
  return <div className="trend-chart" aria-label="Sales trend chart">{data.map((point) => { const value = Number(point.sales); return <div className="trend-column" key={point.date} title={`${point.date}: ${formatMoney(point.sales)}`}><div className={value < 0 ? 'refund-bar' : ''} style={{ height: maxMagnitude ? `${Math.max(4, Math.abs(value) / maxMagnitude * 100)}%` : '2px' }} /><small>{point.date.slice(5)}</small></div> })}</div>
}

function Metrics({ summary }: { summary: ReportSummary }) {
  return <div className="metric-grid" aria-label="Business performance metrics">
    <StatCard label="Total Products" value={summary.total_active_products} note={`${summary.total_units_in_stock} units on hand`} tone="slate" />
    <StatCard label="Revenue" value={formatMoney(summary.sales_total)} tone="indigo" />
    <StatCard label="Transactions" value={summary.transaction_count} tone="indigo" />
    <StatCard label="Items Sold" value={summary.items_sold} tone="green" />
    <StatCard label="Low Stock" value={summary.low_stock_count} note="At or below minimum" tone="amber" />
    <StatCard label="Out of Stock" value={summary.out_of_stock_count} note="Needs attention" tone="red" />
    <StatCard label="Gross Profit" value={formatMoney(summary.gross_profit)} note={!summary.profit_complete ? 'Partial — some sales lack cost snapshots' : 'Complete cost history'} tone="green" />
    <StatCard label="Operating Expenses" value={formatMoney(summary.operating_expenses ?? '0.00')} tone="amber" />
    <StatCard label="Net Profit" value={summary.net_profit_complete !== false && summary.net_profit != null ? formatMoney(summary.net_profit) : 'Unavailable'} note={summary.net_profit_complete === false ? 'Incomplete historical cost data' : undefined} tone="indigo" />
  </div>
}

export function DashboardPage() {
  const [summary, setSummary] = useState(zero); const [top, setTop] = useState<TopProduct[]>([]); const [trend, setTrend] = useState<TrendPoint[]>([]); const [stock, setStock] = useState<InventoryStatus | null>(null); const [loading, setLoading] = useState(true); const [error, setError] = useState('')
  useEffect(() => { Promise.all([api.getReportSummary('', '', true), api.getSalesTrend(), api.getTopProducts('', '', 5), api.getInventoryStatus()]).then(([s, t, p, i]) => { setSummary(s); setTrend(t); setTop(p); setStock(i) }).catch(() => setError('Dashboard could not be loaded.')).finally(() => setLoading(false)) }, [])
  return <section className="dashboard-page"><PageHeader eyebrow="Business overview" title="Dashboard" description="Today’s sales performance, profitability, and current inventory health." actions={<a className="button primary button-link" href="/reports">View detailed reports</a>} />
    {error && <Notice tone="error">{error}</Notice>}{loading ? <LoadingState label="Loading business overview…" /> : <><Metrics summary={summary} />
      <div className="dashboard-grid"><section className="card dashboard-panel trend-panel"><div className="panel-heading"><div><span className="eyebrow">Performance</span><h2>Sales trend</h2></div><small>Actual revenue by day</small></div>{trend.length ? <TrendChart data={trend} /> : <EmptyState title="No sales trend yet" description="Completed sales will appear here." />}</section>
      <section className="card dashboard-panel"><div className="panel-heading"><div><span className="eyebrow">Best sellers</span><h2>Top products</h2></div></div>{top.length ? <div className="rank-list">{top.map((p, i) => <div className="rank-row" key={`${p.product_id}-${p.sku}`}><b>{i + 1}</b><span><strong>{p.product_name}</strong><small>{p.quantity_sold} sold · {p.sku}</small></span><strong>{formatMoney(p.revenue)}</strong></div>)}</div> : <EmptyState title="No products sold yet" description="Product performance will appear after a completed sale." />}</section>
      <section className="card dashboard-panel alerts-panel"><div className="panel-heading"><div><span className="eyebrow">Inventory attention</span><h2>Stock alerts</h2></div><a href="/">View catalog</a></div>{stock && [...stock.out_of_stock, ...stock.low_stock].length ? <div className="alert-list">{[...stock.out_of_stock, ...stock.low_stock].slice(0, 6).map((p) => <div className="stock-row" key={p.product_id}><span><strong>{p.product_name}</strong><small>{p.sku}</small></span><span className={`stock-status ${p.current_stock === 0 ? 'out' : 'low'}`}>{p.current_stock === 0 ? 'Out of stock' : `${p.current_stock} left`}</span><small>Minimum {p.minimum_stock}</small></div>)}</div> : <EmptyState title="Inventory levels look healthy" description="No low-stock or out-of-stock products need attention." />}</section></div></>}
  </section>
}

export { Metrics, TrendChart, zero }
