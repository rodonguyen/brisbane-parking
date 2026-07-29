import { useEffect, useRef } from 'react'
import * as maplibregl from 'maplibre-gl'
import type { BBox, MapPin } from './api'
import { chanceColor } from './api'

type Props = {
  meters: MapPin[]
  selectedId: string | null
  onSelect: (meterNo: string) => void
  onViewportChange: (bbox: BBox, zoom: number) => void
  focus?: { lng: number; lat: number } | null
}

const BRISBANE: [number, number] = [153.0251, -27.4698]
const SOURCE_ID = 'meters'
const HALO_LAYER_ID = 'meters-halo'
const LAYER_ID = 'meters-circles'
const SELECTED_LAYER_ID = 'meters-selected'

/** Quiet light basemap — muted greys, almost no POI clutter. */
const BASEMAP_TILES = [
  'https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
  'https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
  'https://c.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
]

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
        color: chanceColor(m.chance_free, m.parkable !== false),
        selected: m.meter_no === selectedId ? 1 : 0,
        parkable: m.parkable === false ? 0 : 1,
      },
      geometry: {
        type: 'Point' as const,
        coordinates: [m.longitude, m.latitude] as [number, number],
      },
    })),
  }
}

function readBBox(map: maplibregl.Map): BBox {
  const b = map.getBounds()
  return {
    west: b.getWest(),
    south: b.getSouth(),
    east: b.getEast(),
    north: b.getNorth(),
  }
}

export function ParkingMap({
  meters,
  selectedId,
  onSelect,
  onViewportChange,
  focus,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const onViewportChangeRef = useRef(onViewportChange)
  const onSelectRef = useRef(onSelect)
  const readyRef = useRef(false)

  onViewportChangeRef.current = onViewportChange
  onSelectRef.current = onSelect

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {
          basemap: {
            type: 'raster',
            tiles: BASEMAP_TILES,
            tileSize: 256,
            attribution: '© OpenStreetMap © CARTO',
          },
        },
        layers: [
          {
            id: 'basemap',
            type: 'raster',
            source: 'basemap',
            paint: {
              // Push basemap into the background so pins dominate
              'raster-saturation': -0.55,
              'raster-contrast': -0.2,
              'raster-brightness-min': 0.08,
              'raster-brightness-max': 0.92,
              'raster-opacity': 0.88,
            },
          },
        ],
      },
      center: BRISBANE,
      zoom: 14,
      minZoom: 11,
      attributionControl: { compact: true },
    })

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')

    const emitViewport = () => {
      onViewportChangeRef.current(readBBox(map), map.getZoom())
    }

    map.on('load', () => {
      map.addSource(SOURCE_ID, {
        type: 'geojson',
        data: pinsToGeoJson([], null),
      })

      // Soft white halo so pins lift off the street grid
      map.addLayer({
        id: HALO_LAYER_ID,
        type: 'circle',
        source: SOURCE_ID,
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 12, 8, 15, 12, 18, 16],
          'circle-color': '#ffffff',
          'circle-opacity': 0.72,
          'circle-blur': 0.35,
        },
      })

      map.addLayer({
        id: LAYER_ID,
        type: 'circle',
        source: SOURCE_ID,
        paint: {
          'circle-radius': [
            'interpolate',
            ['linear'],
            ['zoom'],
            12,
            ['case', ['==', ['get', 'parkable'], 0], 5, 6],
            15,
            ['case', ['==', ['get', 'parkable'], 0], 7, 9],
            18,
            ['case', ['==', ['get', 'parkable'], 0], 10, 13],
          ],
          'circle-color': ['get', 'color'],
          'circle-stroke-width': 2,
          'circle-stroke-color': '#1c1914',
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
      emitViewport()
    })

    let moveTimer: ReturnType<typeof setTimeout> | null = null
    const onMoveEnd = () => {
      if (moveTimer) clearTimeout(moveTimer)
      moveTimer = setTimeout(emitViewport, 220)
    }
    map.on('moveend', onMoveEnd)

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
      if (moveTimer) clearTimeout(moveTimer)
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
