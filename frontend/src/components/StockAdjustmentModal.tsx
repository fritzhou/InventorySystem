import { useMemo, useState, type FormEvent } from 'react'
import type { Product } from '../types/product'
import type { StockAdjustmentInput } from '../types/inventory'

export function StockAdjustmentModal({ product, saving, error, onCancel, onConfirm }: { product: Product; saving: boolean; error: string | null; onCancel: () => void; onConfirm: (value: StockAdjustmentInput) => void }) {
  const [type, setType] = useState<StockAdjustmentInput['type']>('RESTOCK')
  const [value, setValue] = useState('')
  const [note, setNote] = useState('')
  const amount = Number(value)
  const after = useMemo(() => type === 'CORRECTION' ? amount : product.current_stock + (type === 'RESTOCK' ? amount : -amount), [amount, product.current_stock, type])
  const valid = Number.isInteger(amount) && amount >= (type === 'CORRECTION' ? 0 : 1) && after >= 0
  const submit = (event: FormEvent) => { event.preventDefault(); if (valid) onConfirm(type === 'CORRECTION' ? { type, actual_stock: amount, note } : { type, quantity: amount, note }) }
  return <div className="modal-backdrop"><section className="modal adjustment-modal" role="dialog" aria-modal="true" aria-labelledby="adjust-title">
    <div className="modal-heading"><div><span className="eyebrow">Inventory movement</span><h2 id="adjust-title">Adjust Stock</h2></div><button className="icon-button" aria-label="Close" onClick={onCancel}>×</button></div>
    <p><strong>Product:</strong> {product.name}<br /><span className="muted">Current Stock: {product.current_stock}</span></p>
    <form className="adjustment-form" onSubmit={submit}><label>Adjustment Type<select value={type} onChange={(e) => { setType(e.target.value as StockAdjustmentInput['type']); setValue('') }}><option value="RESTOCK">Restock</option><option value="DAMAGE">Damage</option><option value="CORRECTION">Correction</option></select></label>
      <label>{type === 'CORRECTION' ? 'Actual counted stock' : 'Quantity'}<input aria-label={type === 'CORRECTION' ? 'Actual counted stock' : 'Quantity'} type="number" min={type === 'CORRECTION' ? 0 : 1} step="1" value={value} onChange={(e) => setValue(e.target.value)} /></label>
      <label>Note <span className="optional">Optional</span><input value={note} maxLength={1000} onChange={(e) => setNote(e.target.value)} placeholder="Supplier delivery, reason for correction…" /></label>
      {value && <div className={`stock-preview ${valid ? '' : 'invalid'}`}><span>Current: {product.current_stock}</span><strong>{type === 'CORRECTION' && valid ? `Adjustment: ${after - product.current_stock >= 0 ? '+' : ''}${after - product.current_stock}` : type === 'DAMAGE' ? `Remove: ${amount}` : `Add: ${amount}`}</strong><span>Result: {Number.isFinite(after) ? after : '—'}</span></div>}
      {!valid && value && <p className="error" role="alert">{after < 0 ? `Cannot remove more than ${product.current_stock} items.` : 'Enter a valid whole number.'}</p>}{error && <p className="error" role="alert">{error}</p>}
      <div className="form-actions"><button type="button" className="button secondary" disabled={saving} onClick={onCancel}>Cancel</button><button className="button primary" disabled={!valid || saving}>{saving ? 'Saving…' : 'Confirm Adjustment'}</button></div>
    </form>
  </section></div>
}
