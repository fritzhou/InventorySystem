import { useState, type FormEvent } from 'react'
import { useAuth } from '../auth'

function FlowMark() {
  return <svg viewBox="0 0 42 42" fill="none" aria-hidden="true"><path d="M9 11h20c3.3 0 6 2.7 6 6s-2.7 6-6 6H15c-3.3 0-6 2.7-6 6s2.7 6 6 6h18"/><circle cx="9" cy="11" r="2.4"/><circle cx="33" cy="35" r="2.4"/></svg>
}

export function LoginPage() {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try { await login(email, password) }
    catch { setError('Invalid email or password') }
    finally { setPassword(''); setBusy(false) }
  }

  return <main className="auth-page stockflow-login">
    <div className="login-shell">
      <section className="login-showcase">
        <div className="login-brand"><span className="login-logo"><FlowMark/></span><span><strong>StockFlow</strong><small>Inventory Management</small></span></div>
        <div className="login-showcase-copy"><span className="login-kicker">Business operations</span><h1>Inventory control that stays clear and organized.</h1><p>Manage products, sales, purchasing, expenses, reports, and day-to-day stock activity from one workspace.</p></div>
        <div className="login-feature-row"><span>Inventory</span><span>Point of Sale</span><span>Reports</span></div>
      </section>

      <section className="login-card" aria-labelledby="login-title">
        <div className="login-mobile-brand"><span className="login-logo"><FlowMark/></span><span><strong>StockFlow</strong><small>Inventory Management</small></span></div>
        <div className="login-heading"><span className="login-kicker">Welcome back</span><h1 id="login-title">Sign in to StockFlow</h1><p>Enter your account details to continue to your workspace.</p></div>

        <form className="login-form" onSubmit={submit}>
          <label htmlFor="login-email">Email address</label>
          <div className="login-input-wrap"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m4 7 8 6 8-6"/></svg><input id="login-email" type="email" autoComplete="username" placeholder="you@example.com" required value={email} onChange={event => setEmail(event.target.value)} /></div>

          <label htmlFor="login-password">Password</label>
          <div className="login-input-wrap password-field"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg><input id="login-password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" placeholder="Enter your password" required value={password} onChange={event => setPassword(event.target.value)} /><button type="button" className="password-toggle" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword(value => !value)}>{showPassword ? 'Hide' : 'Show'}</button></div>

          {error && <div className="login-error" role="alert"><span aria-hidden="true">!</span><p>{error}</p></div>}

          <button className="button primary login-submit" disabled={busy}>{busy ? <><span className="login-spinner" aria-hidden="true"/>Signing in…</> : <>Sign in<span aria-hidden="true">→</span></>}</button>
        </form>

        <p className="login-footnote">StockFlow · Inventory Management System</p>
      </section>
    </div>
  </main>
}
