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

/** Muted teal — off-meter / free street parking (not a chance %). */
export const FREE_PIN_COLOR = '#2f7d6d'
/** Grey — clearway / no stopping / other no-parking. */
export const NO_PARKING_PIN_COLOR = '#9a958c'

export function chanceColor(
  chance: number | null | undefined,
  parkable: boolean | undefined = true,
  parkStatus?: ParkStatus | null,
): string {
  if (parkStatus === 'free') return FREE_PIN_COLOR
  if (parkStatus === 'restricted' || parkable === false) return NO_PARKING_PIN_COLOR
  if (chance == null) return '#6e675c'
  if (chance >= 0.6) return '#0f8a4a'
  if (chance >= 0.35) return '#d97706'
  return '#c23030'
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

export async function fetchMeterInsight(meterNo: string): Promise<MeterInsight> {
  const res = await fetch(apiUrl(`/api/meters/${encodeURIComponent(meterNo)}`))
  if (!res.ok) throw new Error(`Failed to load meter (${res.status})`)
  return res.json()
}
