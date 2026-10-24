/** Free anonymous looks at distinct meters before Clerk sign-in is required. */
export const FREE_DISTINCT_METERS = 20

export const SEEN_METERS_KEY = 'bpf_seen_meters'

export function canOpenMeter(
  meterNo: string,
  seen: Set<string>,
  signedIn: boolean,
): boolean {
  if (signedIn) return true
  if (seen.has(meterNo)) return true
  return seen.size < FREE_DISTINCT_METERS
}

export function withRecordedMeter(meterNo: string, seen: Set<string>): Set<string> {
  if (seen.has(meterNo)) return seen
  const next = new Set(seen)
  next.add(meterNo)
  return next
}

export function serializeSeenMeters(seen: Set<string>): string {
  return JSON.stringify([...seen])
}

export function parseSeenMeters(raw: string | null): Set<string> {
  if (!raw) return new Set()
  try {
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return new Set()
    return new Set(parsed.filter((id): id is string => typeof id === 'string'))
  } catch {
    return new Set()
  }
}

export function loadSeenMeters(storage: Pick<Storage, 'getItem'> = localStorage): Set<string> {
  return parseSeenMeters(storage.getItem(SEEN_METERS_KEY))
}

export function saveSeenMeters(
  seen: Set<string>,
  storage: Pick<Storage, 'setItem'> = localStorage,
): void {
  storage.setItem(SEEN_METERS_KEY, serializeSeenMeters(seen))
}
