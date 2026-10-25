export type ParkStatus = 'operating' | 'free' | 'restricted'

export type MapPin = {
  meter_no: string
  street: string
  suburb: string
  latitude: number
  longitude: number
  mobile_zone: string
  chance_free: number | null
  occupancy_pred: number | null
  lookup_method: string | null
  parkable?: boolean
  park_status?: ParkStatus
  park_reason?: string
}

export type MeterSummary = {
  meter_no: string
  street: string
  suburb: string
  loc_desc: string
  latitude: number
  longitude: number
  mobile_zone: string
  veh_bays: number
  max_stay_hrs: string
  operational_day: string
  operational_time: string
  restrictions?: string
  tar_rate_weekday: string
  tar_rate_ah_we: string
  category: string
  chance_free: number | null
  occupancy_pred: number | null
  lookup_method: string | null
  parkable?: boolean
  park_status?: ParkStatus
  park_reason?: string
}

export type HourPoint = {
  hour: number
  occupancy_pred: number
  chance_free: number
  parkable?: boolean
  park_status?: ParkStatus
}

export type ContextPoint = {
  label: string
  occupancy_pred: number
  chance_free: number
  sample_count: number
}

export type NearbyMeter = {
  meter_no: string
  street: string
  suburb: string
  distance_m: number
  chance_free: number | null
  occupancy_pred: number | null
  park_status?: ParkStatus
}

export type MetaResponse = {
  brisbane_now: string
  next_hour: number
  target_date: string
  day_class: string
  season: string
  is_holiday: boolean
  suburbs: string[]
  meter_count: number
}

export type BBox = {
  west: number
  south: number
  east: number
  north: number
}

export type MapResponse = {
  brisbane_now: string
  next_hour: number
  target_date: string
  meters: MapPin[]
  count: number
  limit: number
  truncated: boolean
}

export type MeterInsight = {
  meter: MeterSummary
  brisbane_now: string
  next_hour: number
  target_date: string
  day_class: string
  season: string
  is_holiday: boolean
  next_hour_chance_free: number | null
  next_hour_occupancy: number | null
  next_hour_label: string
  parkable?: boolean
  park_status?: ParkStatus
  park_reason?: string
  lookup_method: string
  today_series: HourPoint[]
  typical_series: HourPoint[]
  context_comparison: ContextPoint[]
  nearby: NearbyMeter[]
}

export type CarparkRateRow = {
  label: string | null
  price: string | null
  online_price: string | null
  when: string | null
}

export type Carpark = {
  id: string
  name: string
  address: string | null
  operator: string | null
  lat: number
  lng: number
  hours: string | null
  /** Opening hours split for scanning: bold `days`, plain `time`. `days` null = free text / "Open 24/7". */
  hours_lines: Array<{ days: string | null; time: string }>
  height_m: number | null
  url: string | null
  priced: boolean
  rates: Array<{ title: string; rows: CarparkRateRow[] }>
}

/** River blue: off-street car parks, kept apart from the meter chance colours. */
export const CARPARK_PIN_COLOR = '#1f5c8a'

/** Muted teal — high free-bay chance during paid hours. */
export const LIKELY_PIN_COLOR = '#2f7d6d'
/** Bright green — off-meter / free street parking (not a chance %). */
export const FREE_PIN_COLOR = '#16c45a'
/** Grey — clearway / no stopping / other no-parking. */
export const NO_PARKING_PIN_COLOR = '#9a958c'

export const MIXED_PIN_COLOR = '#d97706'
export const UNLIKELY_PIN_COLOR = '#c23030'
const UNKNOWN_PIN_COLOR = '#6e675c'

export type PinCategory = 'likely' | 'mixed' | 'unlikely' | 'free' | 'none' | 'unknown'

/** Legend buckets, in display order; colours match the map pins exactly. */
export const PIN_CATEGORIES: Array<{ key: Exclude<PinCategory, 'unknown'>; label: string; color: string }> = [
  { key: 'likely', label: 'Likely', color: LIKELY_PIN_COLOR },
  { key: 'mixed', label: 'Mixed', color: MIXED_PIN_COLOR },
  { key: 'unlikely', label: 'Unlikely', color: UNLIKELY_PIN_COLOR },
  { key: 'free', label: 'Free', color: FREE_PIN_COLOR },
  { key: 'none', label: 'No parking', color: NO_PARKING_PIN_COLOR },
]

export function pinCategory(
  chance: number | null | undefined,
  parkable: boolean | undefined = true,
  parkStatus?: ParkStatus | null,
): PinCategory {
  if (parkStatus === 'free') return 'free'
  if (parkStatus === 'restricted' || parkable === false) return 'none'
  if (chance == null) return 'unknown'
  if (chance >= 0.6) return 'likely'
  if (chance >= 0.35) return 'mixed'
  return 'unlikely'
}

export function chanceColor(
  chance: number | null | undefined,
  parkable: boolean | undefined = true,
  parkStatus?: ParkStatus | null,
): string {
  const cat = pinCategory(chance, parkable, parkStatus)
  return cat === 'unknown' ? UNKNOWN_PIN_COLOR : PIN_CATEGORIES.find((c) => c.key === cat)!.color
}

export function formatPct(chance: number | null | undefined): string {
  if (chance == null) return '—'
  return `${Math.round(chance * 100)}%`
}

/** Empty in local Vite (uses /api proxy). Set VITE_API_BASE on Netlify to the public API origin. */
const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, '') ?? ''

function apiUrl(path: string): string {
  return `${API_BASE}${path}`
}

export async function fetchMeta(): Promise<MetaResponse> {
  const res = await fetch(apiUrl('/api/meta'))
  if (!res.ok) throw new Error(`Failed to load meta (${res.status})`)
  return res.json()
}

export async function fetchMetersInView(
  bbox: BBox,
  suburb?: string,
  limit = 1000,
): Promise<MapResponse> {
  const params = new URLSearchParams({
    west: String(bbox.west),
    south: String(bbox.south),
    east: String(bbox.east),
    north: String(bbox.north),
    limit: String(limit),
  })
  if (suburb && suburb !== 'ALL') params.set('suburb', suburb)
  const res = await fetch(apiUrl(`/api/meters?${params}`))
  if (!res.ok) throw new Error(`Failed to load meters (${res.status})`)
  return res.json()
}

export async function fetchCarparks(): Promise<Carpark[]> {
  const res = await fetch(apiUrl('/api/carparks'))
  if (!res.ok) throw new Error(`Failed to load car parks (${res.status})`)
  const data = (await res.json()) as { carparks: Carpark[] }
  return data.carparks
}

export async function fetchMeterInsight(meterNo: string): Promise<MeterInsight> {
  const res = await fetch(apiUrl(`/api/meters/${encodeURIComponent(meterNo)}`))
  if (!res.ok) throw new Error(`Failed to load meter (${res.status})`)
  return res.json()
}

function authHeaders(token: string | null): HeadersInit {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

/**
 * The API signs the amount and the supporter identity itself; `email` is only a
 * prefill hint for Checkout when the Clerk token carries no email claim.
 */
export async function createSupportSession(
  token: string | null,
  email?: string | null,
): Promise<string> {
  const res = await fetch(apiUrl('/api/support/session'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
    body: JSON.stringify({ email: email ?? null }),
  })
  if (!res.ok) throw new Error(`Could not start checkout (${res.status})`)
  const data = (await res.json()) as { client_secret: string }
  return data.client_secret
}

export async function fetchSupportStatus(token: string | null): Promise<boolean> {
  const res = await fetch(apiUrl('/api/support/status'), { headers: authHeaders(token) })
  if (!res.ok) return false
  const data = (await res.json()) as { supporter: boolean }
  return Boolean(data.supporter)
}
