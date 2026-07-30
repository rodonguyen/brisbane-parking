export function shouldShowMapError(
  error: string | null,
  metaLoading: boolean,
  pinsLoading: boolean,
): boolean {
  return Boolean(error) && !metaLoading && !pinsLoading
}
