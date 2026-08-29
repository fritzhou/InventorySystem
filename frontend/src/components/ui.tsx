import type { ReactNode } from 'react'

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow?: string; title: string; description: string; actions?: ReactNode }) {
  return <header className="page-heading"><div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h1>{title}</h1><p>{description}</p></div>{actions && <div className="heading-actions">{actions}</div>}</header>
}

export function StatCard({ label, value, note, tone = 'indigo' }: { label: string; value: ReactNode; note?: ReactNode; tone?: 'indigo'|'green'|'amber'|'red'|'slate' }) {
  return <article className={`metric-card stat-${tone}`}><span>{label}</span><strong>{value}</strong>{note && <small>{note}</small>}</article>
}

export function EmptyState({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return <div className="empty-state"><span aria-hidden="true">—</span><strong>{title}</strong>{description && <p>{description}</p>}{action}</div>
}

export function LoadingState({ label = 'Loading…' }: { label?: string }) { return <div className="loading-state" role="status"><i aria-hidden="true"/><span>{label}</span></div> }
export function Notice({ tone, children }: { tone: 'error'|'warning'|'success'|'info'; children: ReactNode }) { return <div className={`notice-state ${tone}`} role={tone === 'error' ? 'alert' : 'status'}>{children}</div> }
