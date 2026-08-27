import type { Sale } from '../types/sale'
import { formatMoney } from '../utils/money'

interface ReceiptProps { sale: Sale; showComplete?: boolean; onNewSale?: () => void }

const paymentLabel = (method: string) => method.charAt(0).toUpperCase() + method.slice(1)

export function Receipt({ sale, showComplete = false, onNewSale }: ReceiptProps) {
  return <section className="receipt card" aria-label={showComplete ? 'Sale complete' : 'Receipt'}>
    <div className="receipt-screen-heading">
      {showComplete && <><div className="success-mark">✓</div><span className="eyebrow">Sale complete</span><h1>Payment received</h1></>}
    </div>
    <div className="receipt-paper">
      <h2>STOCKFLOW</h2>
      <p><strong>Receipt: {sale.receipt_number}</strong><br />Date: {new Date(sale.created_at).toLocaleString()}</p>
      <div className="receipt-column-head"><span>Product<br /><small>Qty × Price</small></span><span>Amount</span></div>
      <div className="receipt-lines">{sale.items.map((item) => <div key={item.id}><span><strong>{item.product_name}</strong><small>{item.sku}<br />{item.quantity} × {formatMoney(item.unit_price)}</small></span><strong>{formatMoney(item.line_total)}</strong></div>)}</div>
      <dl className="receipt-totals">
        <div><dt>Subtotal</dt><dd>{formatMoney(sale.subtotal)}</dd></div>
        <div><dt>Total</dt><dd>{formatMoney(sale.total)}</dd></div>
        <div><dt>{paymentLabel(sale.payment_method)}</dt><dd>{formatMoney(sale.amount_tendered)}</dd></div>
        <div className="change"><dt>Change</dt><dd>{formatMoney(sale.change_due)}</dd></div>
      </dl>
      <p className="receipt-payment">Payment: {paymentLabel(sale.payment_method)}</p>
    </div>
    <div className="receipt-actions">
      <button className="button primary" onClick={() => window.print()}>Print Receipt</button>
      {onNewSale && <button className="button secondary" onClick={onNewSale}>New Sale</button>}
    </div>
  </section>
}
