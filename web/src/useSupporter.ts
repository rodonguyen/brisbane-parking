import { useAuth } from '@clerk/react'
import { useCallback, useEffect, useState } from 'react'
import { fetchSupportStatus } from './api'
import { supportEnabled } from './supportConfig'

type Supporter = {
  isSupporter: boolean
  refresh: () => Promise<void>
}

/**
 * Supporter state lives on the API, keyed off the verified Clerk token, so it survives
 * a new device or a cleared browser. Signed-out visitors are simply never supporters.
 */
export function useSupporter(): Supporter {
  const { isSignedIn, getToken } = useAuth()
  const [isSupporter, setIsSupporter] = useState(false)

  const refresh = useCallback(async () => {
    if (!supportEnabled || !isSignedIn) {
      setIsSupporter(false)
      return
    }
    try {
      setIsSupporter(await fetchSupportStatus(await getToken()))
    } catch {
      setIsSupporter(false)
    }
  }, [isSignedIn, getToken])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return { isSupporter, refresh }
}
