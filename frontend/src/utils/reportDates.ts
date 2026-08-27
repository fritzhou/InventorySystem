export type ReportPreset = 'today' | '7' | '30' | 'month' | 'custom'

/** Format a Date from its local calendar fields without converting it to UTC. */
export function formatLocalDate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function getPresetDateRange(
  preset: Exclude<ReportPreset, 'custom'>,
  now = new Date(),
): [string, string] {
  const end = formatLocalDate(now)
  if (preset === 'today') return [end, end]
  if (preset === 'month') return [`${end.slice(0, 8)}01`, end]

  const start = new Date(now)
  start.setDate(start.getDate() - (preset === '7' ? 6 : 29))
  return [formatLocalDate(start), end]
}
