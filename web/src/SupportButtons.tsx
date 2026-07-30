import { CoffeeIcon } from '@phosphor-icons/react'
import {
  SUPPORT_FOOTER_SUFFIX,
  SUPPORT_LABEL,
  SUPPORT_PROMISE,
  SUPPORTER_LABEL,
} from './support'
import { supportEnabled } from './supportConfig'

type Props = {
  onOpen: () => void
}

type IconProps = Props & {
  isSupporter: boolean
}

/** Compact topbar entry point: icon only, full copy in the tooltip and accessible name. */
export function SupportIconButton({ onOpen, isSupporter }: IconProps) {
  if (!supportEnabled) return null
  const label = isSupporter ? SUPPORTER_LABEL : SUPPORT_LABEL
  return (
    <button
      type="button"
      className="support-icon"
      onClick={onOpen}
      title={isSupporter ? label : `${label}. ${SUPPORT_PROMISE}`}
      aria-label={label}
      data-supporter={isSupporter}
    >
      <CoffeeIcon size={17} weight={isSupporter ? 'fill' : 'regular'} aria-hidden="true" />
    </button>
  )
}

/** Footer entry point: carries the wording the topbar icon can only imply. */
export function SupportFooterButton({ onOpen }: Props) {
  if (!supportEnabled) return null
  return (
    <span className="footer-support">
      <button type="button" className="footer-support__link" onClick={onOpen}>
        {SUPPORT_LABEL}
      </button>{' '}
      {SUPPORT_FOOTER_SUFFIX}
    </span>
  )
}
