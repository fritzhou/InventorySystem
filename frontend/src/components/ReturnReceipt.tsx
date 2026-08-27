import type { SaleReturn } from '../types/sale'
import { formatMoney } from '../utils/money'

export function ReturnReceipt({ value }: { value: SaleReturn }) {
  return <section className="receipt card" aria-label="Return receipt"><div className="receipt-paper">
    <h2>STOCKFLOW</h2><p><strong>RETURN RECEIPT</strong><br />Return # {value.return_number}<br />Original Receipt # {value.sale.receipt_number}<br />{new Date(value.created_at).toLocaleString()}</p>
    <div className="receipt-lines">{value.items.map(item => <div key={item.id}><span><strong>{item.product_name}</strong><small>{item.quantity} × {formatMoney(item.unit_price)}{item.return_to_stock ? ' · Returned to stock' : ''}</small></span><strong>{formatMoney(item.refund_amount)}</strong></div>)}</div>
    <dl className="receipt-totals"><div className="change"><dt>Refund Total</dt><dd>{formatMoney(value.refund_total)}</dd></div></dl>{value.reason && <p>Reason: {value.reason}</p>}
  </div><div className="receipt-actions"><button className="button primary" onClick={() => window.print()}>Print Return Receipt</button></div></section>
}
