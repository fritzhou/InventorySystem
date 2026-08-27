import { useEffect, useState, type ReactNode } from 'react'
import type { AuthUser, Role } from '../auth'

export type NavigationItem = { path: string; label: string; roles: Role[]; group: 'main' | 'finance' | 'management' }

const glyphs: Record<string, ReactNode> = {
  Dashboard: <><path d="M4 13h6V4H4zM14 20h6V11h-6zM4 20h6v-3H4zM14 7h6V4h-6z" /></>,
  Products: <><path d="m4 7 8-4 8 4-8 4zM4 7v10l8 4 8-4V7M12 11v10" /></>,
  'Point of Sale': <><path d="M3 3h2l2.4 11h9.8l2-7H6M9 19h.01M17 19h.01" /></>,
  'Sales History': <><path d="M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5M12 7v5l3 2" /></>,
  Returns: <><path d="m9 14-4-4 4-4M5 10h9a5 5 0 0 1 5 5v3" /></>,
  'Inventory History': <><path d="M4 5h16v4H4zM6 9v11h12V9M9 13h6" /></>,
  Expenses: <><path d="M4 6h16v13H4zM16 10h4M7 3h10v3" /></>,
  Reports: <><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></>,
  'Purchase Orders': <><path d="M6 3h12v18H6zM9 8h6M9 12h6M9 16h4" /></>,
  Suppliers: <><path d="M3 20h18M5 20V8l7-4 7 4v12M9 20v-5h6v5" /></>,
  Users: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8M22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8" /></>,
  'Audit Log': <><path d="M6 3h12v18H6zM9 8h6M9 12h6M9 16h3" /></>,
}

function Icon({ name }: { name: string }) { return <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{glyphs[name] ?? glyphs.Products}</svg> }
export function StockFlowLogo() { return <svg className="stockflow-logo" viewBox="0 0 40 40" aria-hidden="true"><path d="M8 10h19c4 0 6 2 6 5s-2 5-6 5H14c-4 0-6 2-6 5s2 5 6 5h18"/><circle cx="8" cy="10" r="2"/><circle cx="32" cy="30" r="2"/></svg> }

export function AppShell({ user, activePath, items, onLogout, children }: { user: AuthUser; activePath: string; items: NavigationItem[]; onLogout: () => void; children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('stockflow:sidebar') === 'collapsed')
  const [mobileOpen, setMobileOpen] = useState(false)
  useEffect(() => setMobileOpen(false), [activePath])
  const toggle = () => { setCollapsed((value) => { localStorage.setItem('stockflow:sidebar', value ? 'expanded' : 'collapsed'); return !value }) }
  const initials = user.display_name.split(/\s+/).map((word) => word[0]).join('').slice(0, 2).toUpperCase()
  return <div className={`app-shell ${collapsed ? 'sidebar-collapsed' : ''} ${mobileOpen ? 'mobile-nav-open' : ''}`}>
    <aside className="sidebar" aria-label="Application sidebar">
      <div className="sidebar-brand"><a href={user.role === 'ADMIN' ? '/dashboard' : '/pos'} aria-label="StockFlow home"><StockFlowLogo/><span><b>StockFlow</b><small>Inventory management</small></span></a><button className="sidebar-collapse" onClick={toggle} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>‹</button></div>
      <nav className="side-nav" aria-label="Main navigation">{(['main', 'finance', 'management'] as const).map((group) => {
        const available = items.filter((item) => item.group === group && item.roles.includes(user.role)); if (!available.length) return null
        return <section key={group}><h2>{group === 'main' ? 'Main' : group === 'finance' ? 'Finance & reporting' : 'Management'}</h2>{available.map((item) => <a title={collapsed ? item.label : undefined} className={activePath === item.path ? 'active' : ''} href={item.path} key={item.path}><Icon name={item.label}/><span>{item.label}</span></a>)}</section>
      })}</nav>
      <div className="sidebar-user"><a href="/account"><span className="avatar">{initials}</span><span><b>{user.display_name}</b><small>{user.role}</small></span></a><button onClick={onLogout} aria-label="Logout"><Icon name="Returns"/><span>Logout</span></button></div>
    </aside>
    <button className="sidebar-scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />
    <div className="app-workspace"><header className="topbar"><button className="mobile-menu" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><span/><span/><span/></button><div className="topbar-context"><b>{items.find((item) => item.path === activePath)?.label ?? 'StockFlow'}</b><span>StockFlow workspace</span></div><a className="topbar-account" href="/account"><span className="avatar">{initials}</span><span><b>{user.display_name}</b><small>{user.role}</small></span></a></header><main>{children}</main></div>
  </div>
}
