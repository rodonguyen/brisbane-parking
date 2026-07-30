import { UserButton } from '@clerk/react'

type Props = {
  isSupporter: boolean
}

/** Clerk owns the profile popover header; we badge the avatar from our supporter record. */
export function SupporterUserButton({ isSupporter }: Props) {
  return (
    <span
      className="user-button-wrap"
      data-supporter={isSupporter}
      title={isSupporter ? 'Future premium supporter' : undefined}
    >
      <UserButton />
      {isSupporter && (
        <span className="user-button-wrap__badge" aria-hidden="true">
          💎
        </span>
      )}
    </span>
  )
}
