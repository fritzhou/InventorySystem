import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'

import { BarcodeScanner } from '../components/BarcodeScanner'
import { Receipt } from '../components/Receipt'
import { ApiError, api } from '../services/api'
import type { Product } from '../types/product'
import type { Sale } from '../types/sale'

interface CartLine { product: Product; quantity: number }

const cents = (value: string) => Math.round(Number(value) * 100)
const money = (value: number) => `₱${(value / 100).toFixed(2)}`

export function PosPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Product[]>([])
  const [cart, setCart] = useState<CartLine[]>([])
  const [cash, setCash] = useState('')
  const [scanner, setScanner] = useState(false)
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [sale, setSale] = useState<Sale | null>(null)

  const search = useCallback(async (term = query) => {
    setMessage('')
    try { setResults(await api.getProducts({ search: term, activeOnly: true })) }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Products could not be loaded') }
  }, [query])

  useEffect(() => {
    api.getProducts({ activeOnly: true }).then(setResults).catch((error: unknown) => setMessage(error instanceof Error ? error.message : 'Products could not be loaded'))
  }, [])

  const add = (product: Product) => {
    setMessage('')
    if (!product.is_active) { setMessage('Product is inactive'); return }
    if (product.current_stock < 1) { setMessage(`${product.name} is out of stock`); return }
    setCart((current) => {
      const existing = current.find((line) => line.product.id === product.id)
      if (existing) {
        if (existing.quantity >= product.current_stock) { setMessage(`Only ${product.current_stock} available for ${product.name}`); return current }
        return current.map((line) => line.product.id === product.id ? { ...line, quantity: line.quantity + 1 } : line)
      }
      return [...current, { product, quantity: 1 }]
    })
  }

  const adjust = (id: string, quantity: number) => {
    setCart((current) => current.map((line) => {
      if (line.product.id !== id) return line
      const safe = Math.max(1, Math.min(quantity, line.product.current_stock))
      if (quantity > line.product.current_stock) setMessage(`Only ${line.product.current_stock} available for ${line.product.name}`)
      return { ...line, quantity: safe }
    }))
  }

  const scanned = async (barcode: string) => {
    setScanner(false); setMessage('')
    try { add(await api.getProductByBarcode(barcode)) }
    catch (error) {
      setMessage(error instanceof ApiError && error.status === 404 ? 'Product not registered in inventory' : error instanceof Error ? error.message : 'Barcode lookup failed')
    }
  }

  const total = useMemo(() => cart.reduce((sum, line) => sum + cents(line.product.selling_price) * line.quantity, 0), [cart])
  const tendered = cash === '' ? 0 : cents(cash)
  const invalid = cart.some((line) => line.quantity < 1 || line.quantity > line.product.current_stock)
  const canCheckout = cart.length > 0 && !invalid && tendered >= total && !loading

  const checkout = async () => {
    if (!canCheckout) return
    setLoading(true); setMessage('')
    try {
      setSale(await api.checkout({ items: cart.map((line) => ({ product_id: line.product.id, quantity: line.quantity })), amount_tendered: Number(cash).toFixed(2) }))
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Checkout could not be completed') }
    finally { setLoading(false) }
  }

  if (sale) return <Receipt sale={sale} showComplete onNewSale={() => { setSale(null); setCart([]); setCash(''); void search('') }} />

  return <div className="page-content pos-page">
    <div className="page-heading"><div><span className="eyebrow">Cashier workspace</span><h1>Point of Sale</h1><p>Search or scan products, then take a secure cash payment.</p></div><button className="button secondary" onClick={() => setScanner(true)}>▣ Scan Barcode</button></div>
    {message && <div className="error pos-message" role="alert">{message}{message === 'Product not registered in inventory' && <> · <a href="/">Register product</a></>}</div>}
    <div className="pos-layout">
      <section className="card product-picker"><form className="pos-search" onSubmit={(event: FormEvent) => { event.preventDefault(); void search() }}><label className="sr-only" htmlFor="pos-search">Search name, SKU, or barcode</label><input id="pos-search" placeholder="Search name, SKU, or barcode" value={query} onChange={(event) => setQuery(event.target.value)} /><button className="button primary">Search</button></form>
        <div className="pos-results">{results.length === 0 ? <p className="empty">No matching active products.</p> : results.map((product) => <article key={product.id} className="result-item"><div><strong>{product.name}</strong><span>{product.sku}{product.barcode ? ` · ${product.barcode}` : ''}</span><small>{money(cents(product.selling_price))} · {product.current_stock} available</small></div><button className="button secondary" disabled={product.current_stock === 0} onClick={() => add(product)}>{product.current_stock ? 'Add' : 'Out of stock'}</button></article>)}</div>
      </section>
      <section className="card cart-panel"><div className="cart-heading"><div><span className="eyebrow">Current sale</span><h2>Cart <small>{cart.reduce((n, line) => n + line.quantity, 0)} items</small></h2></div><button className="text-button danger" disabled={!cart.length} onClick={() => setCart([])}>Clear cart</button></div>
        {!cart.length ? <p className="empty">Scan or add a product to begin.</p> : <div className="cart-lines">{cart.map((line) => <article key={line.product.id} className="cart-line"><div className="cart-product"><strong>{line.product.name}</strong><span>{line.product.sku} · {money(cents(line.product.selling_price))} each</span><small>{line.product.current_stock} in stock</small></div><div className="quantity"><button aria-label={`Decrease ${line.product.name}`} onClick={() => adjust(line.product.id, line.quantity - 1)}>−</button><input aria-label={`${line.product.name} quantity`} type="number" min="1" max={line.product.current_stock} value={line.quantity} onChange={(event) => adjust(line.product.id, Number(event.target.value))} /><button aria-label={`Increase ${line.product.name}`} disabled={line.quantity >= line.product.current_stock} onClick={() => adjust(line.product.id, line.quantity + 1)}>+</button></div><strong>{money(cents(line.product.selling_price) * line.quantity)}</strong><button className="text-button danger" aria-label={`Remove ${line.product.name}`} onClick={() => setCart((current) => current.filter((item) => item.product.id !== line.product.id))}>Remove</button></article>)}</div>}
        <div className="payment"><dl><div><dt>Subtotal</dt><dd>{money(total)}</dd></div><div className="grand-total"><dt>Total</dt><dd>{money(total)}</dd></div></dl><label htmlFor="cash">Cash received</label><div className="money-input"><span>₱</span><input id="cash" type="number" inputMode="decimal" min="0" step="0.01" value={cash} onChange={(event) => setCash(event.target.value)} placeholder="0.00" /></div><div className="change-display"><span>Change</span><strong>{money(Math.max(0, tendered - total))}</strong></div><button className="button primary checkout" disabled={!canCheckout} onClick={() => void checkout()}>{loading ? 'Processing…' : 'Checkout'}</button>{cart.length > 0 && tendered < total && <small className="payment-hint">Enter at least {money(total)} to checkout.</small>}</div>
      </section>
    </div>
    {scanner && <div className="modal-backdrop scanner-backdrop"><section className="modal scanner-modal"><div className="modal-heading"><div><span className="eyebrow">Point of Sale</span><h2>Scan Barcode</h2></div><button className="icon-button" aria-label="Close scanner" onClick={() => setScanner(false)}>×</button></div><BarcodeScanner onDetected={(barcode) => void scanned(barcode)} /><button className="button scanner-close" onClick={() => setScanner(false)}>Cancel</button></section></div>}
  </div>
}
