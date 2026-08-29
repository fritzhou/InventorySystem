import { useEffect, useState, type ReactNode } from 'react'
import type { AuthUser, Role } from '../auth'

export type NavItem = { path: string; label: string; roles: Role[]; icon: string; section: string }

const icons: Record<string, ReactNode> = {
  dashboard: <><path d="M4 13h6V4H4v9Zm10 7h6v-9h-6v9ZM4 20h6v-3H4v3Zm10-13h6V4h-6v3Z" /></>,
  products: <><path d="M4 6.5 12 3l8 3.5-8 3.6-8-3.6Z"/><path d="M4 11.5 12 15l8-3.5M4 16.5 12 20l8-3.5"/></>,
  pos: <><path d="M4 5h16v12H4zM8 21h8M12 17v4"/><path d="M8 9h8M8 13h3"/></>,
  sales: <><path d="M6 3h12v18l-3-2-3 2-3-2-3 2V3Z"/><path d="M9 8h6M9 12h6"/></>,
  returns: <><path d="M9 7H5v-4M5 7a8 8 0 1 1-1 8"/><path d="m5 7 4-4"/></>,
  inventory: <><path d="M4 5h16M6 5v15h12V5M9 9h6M9 13h6"/></>,
  suppliers: <><path d="M3 20h18M5 20V8l7-4 7 4v12M9 20v-6h6v6"/></>,
  purchase: <><path d="M3 5h2l2 10h10l3-7H6M9 20h.01M17 20h.01"/></>,
  expenses: <><circle cx="12" cy="12" r="9"/><path d="M15 8.5c-.7-.5-1.6-.8-2.6-.8-1.5 0-2.7.8-2.7 2s1.1 1.8 2.7 2.2 2.7.9 2.7 2.2-1.2 2.1-2.8 2.1c-1.2 0-2.3-.4-3.1-1M12 6v12"/></>,
  reports: <><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></>,
  users: <><path d="M16 20v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 10a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM22 20v-2a4 4 0 0 0-3-3.87M16 2.13a4 4 0 0 1 0 7.75"/></>,
  audit: <><path d="M9 4H5v16h14V4h-4M9 2h6v4H9z"/><path d="m8 13 2 2 5-5"/></>,
  account: <><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></>,
}

function Icon({ name }: { name: string }) { return <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{icons[name]}</svg> }
function Logo() { return <svg className="flow-logo" aria-hidden="true" viewBox="0 0 40 40"><path d="M8 10h19c3 0 5 2 5 5s-2 5-5 5H13c-3 0-5 2-5 5s2 5 5 5h19"/><circle cx="8" cy="10" r="2.5"/><circle cx="32" cy="30" r="2.5"/></svg> }

export function AppShell({ user, currentPath, title, nav, logout, children }: { user: AuthUser; currentPath: string; title: string; nav: NavItem[]; logout: () => Promise<void>; children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('stockflow-sidebar') === 'collapsed')
  const [drawer, setDrawer] = useState(false)
  useEffect(() => { setDrawer(false) }, [currentPath])
  useEffect(() => { localStorage.setItem('stockflow-sidebar', collapsed ? 'collapsed' : 'expanded') }, [collapsed])
  return <div className={`app-shell ${collapsed ? 'sidebar-collapsed' : ''} ${drawer ? 'drawer-open' : ''}`}>
    <aside className="sidebar" aria-label="Application navigation">
      <div className="sidebar-brand"><a href={user.role === 'ADMIN' ? '/dashboard' : '/pos'} aria-label="StockFlow home"><Logo/><span><b>StockFlow</b><small>Inventory management</small></span></a><button className="sidebar-toggle" onClick={() => setCollapsed(x => !x)} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>‹</button></div>
      <nav aria-label="Main navigation">{[...new Set(nav.map(x => x.section))].map(section => <div className="nav-section" key={section}><p>{section}</p>{nav.filter(x => x.section === section && x.roles.includes(user.role)).map(item => <a href={item.path} className={currentPath === item.path ? 'active' : ''} key={item.path} title={collapsed ? item.label : undefined}><Icon name={item.icon}/><span>{item.label}</span></a>)}</div>)}</nav>
      <div className="sidebar-account"><a href="/account" className={currentPath === '/account' ? 'active' : ''}><span className="avatar">{user.display_name.slice(0, 2).toUpperCase()}</span><span><b>{user.display_name}</b><small>{user.role.toLowerCase()}</small></span></a><button onClick={() => void logout()} title="Log out"><span className="logout-icon">↗</span><span>Log out</span></button></div>
    </aside>
    <button className="drawer-backdrop" aria-label="Close navigation" onClick={() => setDrawer(false)}/>
    <div className="workspace"><header className="topbar"><button className="menu-button" onClick={() => setDrawer(true)} aria-label="Open navigation">☰</button><div><span>StockFlow</span><strong className="topbar-title">{title}</strong></div><a className="topbar-account" href="/account"><span className="avatar">{user.display_name.slice(0, 2).toUpperCase()}</span><span>{user.display_name}<small>{user.role}</small></span></a></header><main>{children}</main></div>
  </div>
}
