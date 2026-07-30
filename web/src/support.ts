/** Copy and key rules for the tip jar. Kept free of `import.meta` so it stays unit-testable. */

export const SUPPORT_TITLE = 'Buy me a coffee'
export const SUPPORT_PRICE = '$5'
export const SUPPORT_LABEL = `${SUPPORT_TITLE} (${SUPPORT_PRICE})`
export const SUPPORT_PROMISE = 'Supporters get first access to future premium features.'
export const SUPPORT_FOOTER_SUFFIX = 'and get first access to future premium features 💙'
export const SUPPORT_THANKS = 'Thanks. Your seat for future premium features is saved.'
export const SUPPORTER_LABEL = 'You support this project. Thank you.'

/**
 * Publishable keys are the only Stripe keys safe to bundle, so anything else (a secret
 * key pasted by mistake, a blank env) disables the tip jar instead of shipping.
 */
export function resolvePublishableKey(raw: string | undefined | null): string | null {
  const key = raw?.trim()
  if (!key || !key.startsWith('pk_')) return null
  return key
}
