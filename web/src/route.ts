export type AppRoute = 'home' | 'terms' | 'privacy'

type Listener = (route: AppRoute) => void

const listeners = new Set<Listener>()

export function pathToRoute(pathname: string): AppRoute {
  const path = pathname.replace(/\/+$/, '') || '/'
  if (path === '/terms') return 'terms'
  if (path === '/privacy') return 'privacy'
  return 'home'
}

export function routeToPath(route: AppRoute): string {
  if (route === 'terms') return '/terms'
  if (route === 'privacy') return '/privacy'
  return '/'
}

export function getRoute(): AppRoute {
  return pathToRoute(window.location.pathname)
}

export function navigate(route: AppRoute, replace = false): void {
  const path = routeToPath(route)
  if (window.location.pathname !== path) {
    if (replace) window.history.replaceState(null, '', path)
    else window.history.pushState(null, '', path)
  }
  for (const listener of listeners) listener(route)
}

export function subscribe(listener: Listener): () => void {
  listeners.add(listener)
  const onPop = () => listener(getRoute())
  window.addEventListener('popstate', onPop)
  return () => {
    listeners.delete(listener)
    window.removeEventListener('popstate', onPop)
  }
}
