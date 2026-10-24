/** Mirrors api/py/timectx.py chance_free: 0 cars expected -> 100%, 5+ -> 0%. */
export function chanceFromOccupancy(occupancy: number | null | undefined): number | null {
  if (occupancy == null) return null
  return Math.max(0, Math.min(1, (5 - occupancy) / 5))
}
