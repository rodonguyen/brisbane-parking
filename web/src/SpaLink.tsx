import type { ReactNode } from 'react'
import { navigate, routeToPath, type AppRoute } from './route'

type SpaLinkProps = {
  to: AppRoute
  children: ReactNode
  className?: string
}

/** In-app link: updates History without a full reload; still works with open-in-new-tab. */
export function SpaLink({ to, children, className }: SpaLinkProps) {
  return (
    <a
      href={routeToPath(to)}
      className={className}
      onClick={(e) => {
        if (e.defaultPrevented) return
        if (e.button !== 0) return
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return
        e.preventDefault()
        navigate(to)
      }}
    >
      {children}
    </a>
  )
}
