/* eslint-disable react-refresh/only-export-components */
import { useEffect, useState, type ReactNode } from 'react'
import { api } from '../services/api'
import type { InventoryStatus, ReportSummary, TopProduct, TrendPoint } from '../types/report'
import { formatMoney } from '../utils/money'
import { EmptyState, LoadingState, Notice } from '../components/ui'

const zero: ReportSummary = { sales_total: '0.00', transaction_count: 0, items_sold: 0, gross_profit: '0.00', profit_complete: true, operating_expenses:'0.00', net_profit:'0.00', net_profit_complete:true, average_transaction_value: '0.00', total_active_products: 0, total_units_in_stock: 0, low_stock_count: 0, out_of_stock_count: 0 }

const dashboardIcons: Record<string, ReactNode> = {
  products: <><path d="M4 7.5 12 4l8 3.5-8 3.7-8-3.7Z"/><path d="M4 12.5 12 16l8-3.5M4 17.3 12 21l8-3.7"/></>,
  stock: <><ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"/></>,
  warning: <><path d="M12 3 2.8 20h18.4L12 3Z"/><path d="M12 9v5M12 17h.01"/></>,
  sales: <><path d="M4 19V9M10 19V5M16 19v-7M21 19H2"/></>,
}

function DashboardMetric({ icon, label, value, detail, tone }: { icon: keyof typeof dashboardIcons; label: string; value: ReactNode; detail: string; tone: string }) {
  return <article className={`overview-card overview-${tone}`}><div className="overview-card-top"><span className="overview-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{dashboardIcons[icon]}</svg></span><span>{label}</span></div><strong>{value}</strong><small>{detail}</small></article>
}

function TrendChart({ data }: { data: TrendPoint[] }) {
  const values = data.map(point => Number(point.sales))
  const max = Math.max(...values, 1)
  const min = Math.min(...values, 0)
  const span = Math.max(max - min, 1)
  const width = 760
  const height = 250
  const padX = 28
  const padY = 28
  const plotWidth = width - padX * 2
  const plotHeight = height - padY * 2
  const xFor = (index: number) => data.length <= 1 ? width / 2 : padX + (index / (data.length - 1)) * plotWidth
  const yFor = (value: number) => padY + ((max - value) / span) * plotHeight
  const points = data.map((point, index) => `${xFor(index)},${yFor(Number(point.sales))}`).join(' ')
  const areaPoints = data.length ? `${padX},${height - padY} ${points} ${width - padX},${height - padY}` : ''

  return <div className="line-chart" aria-label="Sales trend chart"><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Actual revenue by day"><defs><linearGradient id="stockflowTrendGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="currentColor" stopOpacity=".22"/><stop offset="100%" stopColor="currentColor" stopOpacity="0"/></linearGradient></defs><g className="chart-grid">{[0,1,2,3,4].map(row => <line key={row} x1={padX} y1={padY + row * (plotHeight / 4)} x2={width - padX} y2={padY + row * (plotHeight / 4)}/>)}</g>{data.length > 1 && <polygon className="chart-area" points={areaPoints}/>}<polyline className="chart-line" points={points}/>{data.map((point, index) => <g key={point.date}><circle className="chart-point" cx={xFor(index)} cy={yFor(Number(point.sales))} r="4"><title>{point.date}: {formatMoney(point.sales)}</title></circle></g>)}</svg><div className="chart-labels">{data.map(point => <span key={point.date}>{point.date.slice(5)}</span>)}</div></div>
}

function Metrics({ summary }: { summary: ReportSummary }) {
  return <div className="overview-grid" aria-label="Business performance metrics">
    <DashboardMetric icon="products" label="Total Products" value={summary.total_active_products} detail={`${summary.total_units_in_stock} units currently on hand`} tone="purple" />
    <DashboardMetric icon="stock" label="Units in Stock" value={summary.total_units_in_stock.toLocaleString()} detail={`${summary.items_sold} items sold in the selected period`} tone="green" />
    <DashboardMetric icon="warning" label="Low Stock Items" value={summary.low_stock_count} detail={`${summary.out_of_stock_count} currently out of stock`} tone="orange" />
    <DashboardMetric icon="sales" label="Transactions" value={summary.transaction_count} detail={`${formatMoney(summary.sales_total)} recorded revenue`} tone="pink" />
  </div>
}

export function DashboardPage() {
  const [summary, setSummary] = useState(zero)
  const [top, setTop] = useState<TopProduct[]>([])
  const [trend, setTrend] = useState<TrendPoint[]>([])
  const [stock, setStock] = useState<InventoryStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => { Promise.all([api.getReportSummary('', '', true), api.getSalesTrend(), api.getTopProducts('', '', 5), api.getInventoryStatus()]).then(([s, t, p, i]) => { setSummary(s); setTrend(t); setTop(p); setStock(i) }).catch(() => setError('Dashboard could not be loaded.')).finally(() => setLoading(false)) }, [])

  const healthyProducts = Math.max(summary.total_active_products - summary.low_stock_count - summary.out_of_stock_count, 0)
  const totalForChart = Math.max(summary.total_active_products, 1)
  const healthyPct = healthyProducts / totalForChart * 100
  const lowPct = summary.low_stock_count / totalForChart * 100
  const donutBackground = `conic-gradient(#6657e8 0 ${healthyPct}%, #ffb657 ${healthyPct}% ${healthyPct + lowPct}%, #f25d86 ${healthyPct + lowPct}% 100%)`
  const attention = stock ? [...stock.out_of_stock, ...stock.low_stock].slice(0, 3) : []

  return <section className="dashboard-page reference-dashboard">
    <div className="dashboard-hero"><div><span className="eyebrow">Business overview</span><h1>Dashboard <span aria-hidden="true">✦</span></h1><p>Here’s what’s happening with your inventory and sales today.</p></div><a className="button primary button-link" href="/reports">View Reports</a></div>

    {error && <Notice tone="error">{error}</Notice>}
    {loading ? <LoadingState label="Loading business overview…" /> : <>
      <Metrics summary={summary} />

      <div className="dashboard-main-grid">
        <section className="card stock-overview-card"><div className="dashboard-section-heading"><div><span className="eyebrow">Performance</span><h2>Sales Overview</h2></div><a href="/reports">Full report →</a></div>{trend.length ? <TrendChart data={trend}/> : <EmptyState title="No sales trend yet" description="Completed sales will appear here." />}</section>

        <section className="card inventory-breakdown-card"><div className="dashboard-section-heading"><div><span className="eyebrow">Inventory health</span><h2>Stock Status</h2></div></div><div className="inventory-donut-wrap"><div className="inventory-donut" style={{background: donutBackground}}><div><strong>{summary.total_active_products}</strong><span>Total</span></div></div><div className="inventory-legend"><div><i className="legend-purple"/><span>Healthy</span><strong>{healthyProducts}</strong></div><div><i className="legend-orange"/><span>Low stock</span><strong>{summary.low_stock_count}</strong></div><div><i className="legend-pink"/><span>Out of stock</span><strong>{summary.out_of_stock_count}</strong></div><div><i className="legend-blue"/><span>Total units</span><strong>{stock?.total_units_in_stock ?? summary.total_units_in_stock}</strong></div></div></div>{attention.length > 0 && <div className="inventory-attention"><span>Needs attention</span>{attention.map(product => <a href={`/inventory?product_id=${product.product_id}`} key={product.product_id}><span><strong>{product.product_name}</strong><small>{product.sku}</small></span><b>{product.current_stock === 0 ? 'Out' : `${product.current_stock} left`}</b></a>)}</div>}<a className="card-link" href="/">View product catalog →</a></section>
      </div>

      <section className="card finance-strip"><div><span>Revenue</span><strong>{formatMoney(summary.sales_total)}</strong></div><div><span>Gross Profit</span><strong>{formatMoney(summary.gross_profit)}</strong><small>{summary.profit_complete ? 'Complete cost history' : 'Partial historical cost data'}</small></div><div><span>Operating Expenses</span><strong>{formatMoney(summary.operating_expenses ?? '0.00')}</strong></div><div><span>Net Profit</span><strong>{summary.net_profit_complete !== false && summary.net_profit != null ? formatMoney(summary.net_profit) : 'Unavailable'}</strong><small>{summary.net_profit_complete === false ? 'Incomplete historical cost data' : 'After operating expenses'}</small></div></section>

      <section className="card top-products-table"><div className="dashboard-section-heading"><div><span className="eyebrow">Sales mix</span><h2>Top Products</h2></div><a href="/">View All Products</a></div>{top.length ? <div className="table-wrap"><table><thead><tr><th>Rank</th><th>Product</th><th>SKU / Code</th><th>Quantity Sold</th><th>Revenue</th></tr></thead><tbody>{top.map((product, index) => <tr key={`${product.product_id}-${product.sku}`}><td><span className="rank-badge">{index + 1}</span></td><td><strong>{product.product_name}</strong></td><td><code className="sku-code">{product.sku}</code></td><td>{product.quantity_sold}</td><td><strong>{formatMoney(product.revenue)}</strong></td></tr>)}</tbody></table></div> : <EmptyState title="No products sold yet" description="Top products will appear after completed sales." />}</section>
    </>}
  </section>
}

export { Metrics, TrendChart, zero }
