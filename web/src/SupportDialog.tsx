import { useAuth, useUser } from '@clerk/react'
import { XIcon } from '@phosphor-icons/react'
import { EmbeddedCheckout, EmbeddedCheckoutProvider } from '@stripe/react-stripe-js'
import { useCallback, useEffect, useState } from 'react'
import { createSupportSession } from './api'
import { SUPPORT_PROMISE, SUPPORT_THANKS, SUPPORT_TITLE } from './support'
import { stripePromise } from './supportConfig'

type Props = {
  onClose: () => void
  onPaid: () => void
}

/**
 * Stripe Checkout runs in the dialog, so paying never leaves the map. The session is
 * created by our API, which is also where the email prefill and the Clerk attribution
 * are attached.
 */
export function SupportDialog({ onClose, onPaid }: Props) {
  const { getToken } = useAuth()
  const { user } = useUser()
  const [paid, setPaid] = useState(false)
  const [failed, setFailed] = useState(false)

  const email = user?.primaryEmailAddress?.emailAddress ?? null

  const fetchClientSecret = useCallback(async () => {
    try {
      return await createSupportSession(await getToken(), email)
    } catch (error) {
      setFailed(true)
      throw error
    }
  }, [getToken, email])

  const handleComplete = useCallback(() => {
    setPaid(true)
    onPaid()
  }, [onPaid])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  if (stripePromise === null) return null

  return (
    <div className="support-dialog" role="presentation" onClick={onClose}>
      <div
        className="support-dialog__card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="support-dialog-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="support-dialog__head">
          <div>
            <h2 id="support-dialog-title">{SUPPORT_TITLE}</h2>
            <p>{paid ? SUPPORT_THANKS : SUPPORT_PROMISE}</p>
          </div>
          <button
            type="button"
            className="support-dialog__close"
            onClick={onClose}
            aria-label="Close"
          >
            <XIcon size={16} aria-hidden="true" />
          </button>
        </header>

        {failed ? (
          <p className="support-dialog__error" role="status">
            Checkout is unavailable right now. Please try again later.
          </p>
        ) : paid ? (
          <div className="support-dialog__done">
            <p>Your receipt is on its way by email.</p>
            <button type="button" className="auth-btn auth-btn--primary" onClick={onClose}>
              Back to the map
            </button>
          </div>
        ) : (
          <div className="support-dialog__checkout">
            <EmbeddedCheckoutProvider
              stripe={stripePromise}
              options={{ fetchClientSecret, onComplete: handleComplete }}
            >
              <EmbeddedCheckout className="support-dialog__embed" />
            </EmbeddedCheckoutProvider>
          </div>
        )}
      </div>
    </div>
  )
}
