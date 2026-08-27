import type { ReactNode } from 'react'

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow: string; title: string; description: string; actions?: ReactNode }) {
  return <header className="page-heading"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{actions && <div className="heading-actions">{actions}</div>}</header>
}

const statIcons = {
  products: <path d="M5 7h14v12H5zM8 4h8v3M9 11h6" />,
  sales: <path d="M4 17 9 12l4 3 7-8M16 7h4v4" />,
  warning: <path d="M12 4 3 20h18zM12 9v5M12 17h.01" />,
  money: <path d="M4 7h16v11H4zM4 10h16M8 15h3" />,
  activity: <path d="M3 12h4l2-6 4 12 2-6h6" />,
} as const

export function StatCard({ label, value, detail, tone = 'primary', icon = 'activity' }: { label: string; value: ReactNode; detail?: ReactNode; tone?: 'primary' | 'success' | 'warning' | 'danger'; icon?: keyof typeof statIcons }) {
  return <article className={`metric-card metric-${tone}`}><div className="metric-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">{statIcons[icon]}</svg></div><div><span>{label}</span><strong>{value}</strong>{detail && <small>{detail}</small>}</div></article>
}

export function StatusBadge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'success' | 'warning' | 'danger' | 'info' | 'neutral' }) {
  return <span className={`status-badge status-${tone}`}><i aria-hidden="true" />{children}</span>
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return <div className="empty-state"><span aria-hidden="true">—</span><strong>{title}</strong><p>{description}</p></div>
}

export function LoadingState({ label = 'Loading data…' }: { label?: string }) {
  return <div className="skeleton-state" role="status" aria-label={label}><i/><i/><i/><span className="sr-only">{label}</span></div>
}
