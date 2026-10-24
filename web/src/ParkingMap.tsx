import { useEffect, useRef } from 'react'
import * as maplibregl from 'maplibre-gl'
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import type { MapPin } from './api'
import { chanceColor } from './api'
import type { LngLat } from './directions'

// MapLibre v6: bundlers don't resolve the worker from import.meta.url.
maplibregl.setWorkerUrl(maplibreWorkerUrl)

type Props = {
  meters: MapPin[]
  selectedId: string | null
  onSelect: (meterNo: string) => void
  onUserLocation: (loc: LngLat) => void
  /** Any touch or click on the map; the app tucks chrome away. */
  onInteract: () => void
  focus?: { lng: number; lat: number } | null
}

const BRISBANE: [number, number] = [153.0251, -27.4698]
const SOURCE_ID = 'meters'
const HALO_LAYER_ID = 'meters-halo'
const LAYER_ID = 'meters-circles'
const SELECTED_LAYER_ID = 'meters-selected'

/** OpenFreeMap Liberty: free full-colour vector basemap, no API key or usage limits. */
const BASEMAP_STYLE = 'https://tiles.openfreemap.org/styles/liberty'

function pinsToGeoJson(
  meters: MapPin[],
  selectedId: string | null,
): {
  type: 'FeatureCollection'
  features: Array<{
    type: 'Feature'
    id: string
    properties: Record<string, string | number | null>
    geometry: { type: 'Point'; coordinates: [number, number] }
  }>
} {
  return {
    type: 'FeatureCollection',
    features: meters.map((m) => ({
      type: 'Feature' as const,
      id: m.meter_no,
      properties: {
        meter_no: m.meter_no,
        street: m.street,
        suburb: m.suburb,
        chance_free: m.chance_free,
        color: chanceColor(m.chance_free, m.parkable !== false, m.park_status),
        selected: m.meter_no === selectedId ? 1 : 0,
        parkable: m.parkable === false ? 0 : 1,
        free: m.park_status === 'free' ? 1 : 0,
      },
      geometry: {
        type: 'Point' as const,
        coordinates: [m.longitude, m.latitude] as [number, number],
      },
    })),
  }
}

export function ParkingMap({
  meters,
  selectedId,
  onSelect,
  onUserLocation,
  onInteract,
  focus,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const onSelectRef = useRef(onSelect)
  const onUserLocationRef = useRef(onUserLocation)
  const onInteractRef = useRef(onInteract)
  const readyRef = useRef(false)

  // Pins can arrive before the map's load event; keep the latest so load can seed them.
  const pinsRef = useRef({ meters, selectedId })

  onSelectRef.current = onSelect
  onUserLocationRef.current = onUserLocation
  onInteractRef.current = onInteract
  pinsRef.current = { meters, selectedId }

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: BASEMAP_STYLE,
      center: BRISBANE,
      zoom: 14,
      minZoom: 11,
      attributionControl: { compact: true },
    })

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')

    const geolocate = new maplibregl.GeolocateControl({
      positionOptions: { enableHighAccuracy: true },
      trackUserLocation: true,
      fitBoundsOptions: { maxZoom: 16 },
    })
    map.addControl(geolocate, 'top-right')
    geolocate.on('geolocate', (pos) => {
      onUserLocationRef.current({ lat: pos.coords.latitude, lng: pos.coords.longitude })
    })

    map.on('load', () => {
      // 3D buildings hide pins and cost GPU on phones; keep the flat footprints.
      if (map.getLayer('building-3d')) map.setLayoutProperty('building-3d', 'visibility', 'none')

      map.addSource(SOURCE_ID, {
        type: 'geojson',
        data: pinsToGeoJson(pinsRef.current.meters, pinsRef.current.selectedId),
      })

      // Soft white halo so pins lift off the street grid
      map.addLayer({
        id: HALO_LAYER_ID,
        type: 'circle',
        source: SOURCE_ID,
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 12, 8, 15, 12, 18, 16],
          'circle-color': '#ffffff',
          // The soft halo only helps pins stand off the street map up close; zoomed out it fattens the blob.
          'circle-opacity': ['interpolate', ['linear'], ['zoom'], 13, 0, 14.5, 0.72],
          'circle-blur': 0.35,
        },
      })

      map.addLayer({
        id: LAYER_ID,
        type: 'circle',
        source: SOURCE_ID,
        layout: {
          // Draw paid pins above free ones so the red/orange/teal signal isn't buried in green.
          'circle-sort-key': ['case', ['==', ['get', 'free'], 1], 0, ['==', ['get', 'parkable'], 0], 1, 2],
        },
        paint: {
          // Zoomed out: small dots with a thin light rim so overlapping pins read as a texture,
          // not a black-outlined blob. Zoomed in: today's bold pins.
          'circle-radius': [
            'interpolate',
            ['linear'],
            ['zoom'],
            10,
            2,
            12,
            ['case', ['==', ['get', 'parkable'], 0], 3, 3.5],
            14,
            ['case', ['==', ['get', 'parkable'], 0], 5.5, 7],
            15,
            ['case', ['==', ['get', 'parkable'], 0], 7, 9],
            18,
            ['case', ['==', ['get', 'parkable'], 0], 10, 13],
          ],
          'circle-color': ['get', 'color'],
          'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 11, 0.6, 13, 1, 15, 2],
          'circle-stroke-color': [
            'interpolate',
            ['linear'],
            ['zoom'],
            12.5,
            'rgba(255, 255, 255, 0.85)',
            14.5,
            '#1c1914',
          ],
          'circle-opacity': ['case', ['==', ['get', 'parkable'], 0], 0.45, 1],
        },
      })

      map.addLayer({
        id: SELECTED_LAYER_ID,
        type: 'circle',
        source: SOURCE_ID,
        filter: ['==', ['get', 'selected'], 1],
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 12, 11, 15, 15, 18, 20],
          'circle-color': 'transparent',
          'circle-stroke-width': 3,
          'circle-stroke-color': '#1c1914',
        },
      })

      readyRef.current = true

      navigator.permissions
        ?.query({ name: 'geolocation' })
        .then((status) => {
          if (status.state === 'granted') geolocate.trigger()
        })
        .catch(() => {})
    })

    // MapLibre only shrinks the compact attribution to its (i) on drag; also do it on tap/pinch.
    // That is visual only, so do it on press. Hiding the footer resizes the map, and a resize
    // mid-gesture cancels the pan, so tell the app only once the gesture (and any fling) ends.
    const onPress = () => {
      map.getContainer().querySelector('.maplibregl-compact-show')?.classList.remove('maplibregl-compact-show')
    }
    const onRelease = () => {
      if (map.isMoving()) map.once('moveend', () => onInteractRef.current())
      else onInteractRef.current()
    }
    map.on('touchstart', onPress)
    map.on('mousedown', onPress)
    map.on('touchend', onRelease)
    map.on('mouseup', onRelease)

    map.on('mouseenter', LAYER_ID, () => {
      map.getCanvas().style.cursor = 'pointer'
    })
    map.on('mouseleave', LAYER_ID, () => {
      map.getCanvas().style.cursor = ''
    })
    map.on('click', LAYER_ID, (e) => {
      const feature = e.features?.[0]
      const id = feature?.properties?.meter_no
      if (typeof id === 'string') onSelectRef.current(id)
    })

    mapRef.current = map

    return () => {
      readyRef.current = false
      map.remove()
      mapRef.current = null
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !readyRef.current) return
    const source = map.getSource(SOURCE_ID) as maplibregl.GeoJSONSource | undefined
    source?.setData(pinsToGeoJson(meters, selectedId))
  }, [meters, selectedId])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !focus) return
    map.easeTo({
      center: [focus.lng, focus.lat],
      zoom: Math.max(map.getZoom(), 15),
      duration: 450,
    })
  }, [focus])

  return <div className="map-shell" ref={containerRef} />
}
