export type LngLat = { lat: number; lng: number }

/** Deep links that hand turn-by-turn driving directions to the native maps apps. */
export function directionsUrls(dest: LngLat, origin?: LngLat | null): { apple: string; google: string } {
  const to = `${dest.lat},${dest.lng}`
  const from = origin ? `${origin.lat},${origin.lng}` : null

  const apple = new URLSearchParams({ daddr: to, dirflg: 'd' })
  if (from) apple.set('saddr', from)

  const google = new URLSearchParams({ api: '1', destination: to, travelmode: 'driving' })
  if (from) google.set('origin', from)

  return {
    apple: `https://maps.apple.com/?${apple}`,
    google: `https://www.google.com/maps/dir/?${google}`,
  }
}

/** Straight-line distance in metres (haversine). */
export function distanceMeters(a: LngLat, b: LngLat): number {
  const r = 6_371_000
  const rad = (d: number) => (d * Math.PI) / 180
  const dLat = rad(b.lat - a.lat)
  const dLng = rad(b.lng - a.lng)
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2
  return 2 * r * Math.asin(Math.sqrt(h))
}

export function formatDistance(m: number): string {
  return m < 1000 ? `${Math.round(m / 10) * 10} m` : `${(m / 1000).toFixed(1)} km`
}
