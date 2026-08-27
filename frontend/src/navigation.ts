import { useEffect, useState } from 'react'

const NAVIGATION_EVENT = 'stockflow:navigation'

export function navigate(to: string): void {
  if (window.location.pathname === to) return
  window.history.replaceState({}, '', to)
  window.dispatchEvent(new Event(NAVIGATION_EVENT))
}

export function usePathname(): string {
  const [pathname, setPathname] = useState(window.location.pathname)
  useEffect(() => {
    const update = () => setPathname(window.location.pathname)
    window.addEventListener('popstate', update)
    window.addEventListener(NAVIGATION_EVENT, update)
    return () => {
      window.removeEventListener('popstate', update)
      window.removeEventListener(NAVIGATION_EVENT, update)
    }
  }, [])
  return pathname
}
