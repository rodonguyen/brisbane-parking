import { loadStripe, type Stripe } from '@stripe/stripe-js'
import { resolvePublishableKey } from './support'

const publishableKey = resolvePublishableKey(
  import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY as string | undefined,
)

/** Null when unconfigured, which is what hides the tip jar entirely. */
export const supportEnabled = publishableKey !== null

/** Loaded once per page, and only when a key exists, so Stripe.js is never fetched otherwise. */
export const stripePromise: Promise<Stripe | null> | null = publishableKey
  ? loadStripe(publishableKey)
  : null
