import { ClerkProvider } from '@clerk/react'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import 'maplibre-gl/dist/maplibre-gl.css'
import App from './App'
import './index.css'

const root = document.getElementById('root')!
const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY as string | undefined

if (!publishableKey) {
  root.innerHTML =
    '<p style="font-family:system-ui;padding:2rem;max-width:36rem">Missing <code>VITE_CLERK_PUBLISHABLE_KEY</code>. Copy <code>web/.env.example</code> to <code>web/.env.local</code> and set a Clerk publishable key (<code>pk_…</code>).</p>'
} else {
  createRoot(root).render(
    <StrictMode>
      <ClerkProvider publishableKey={publishableKey} afterSignOutUrl="/">
        <App />
      </ClerkProvider>
    </StrictMode>,
  )
}
