import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  fetchMeta,
  fetchMeterInsight,
  fetchMetersInView,
  formatPct,
  type BBox,
  type MapPin,
  type MapResponse,
  type MetaResponse,
  type MeterInsight,
} from './api'
import { DetailPanel } from './DetailPanel'
import { hasVisitedBefore, Landing, markVisited } from './Landing'
import { ParkingMap } from './ParkingMap'

/** Below this zoom the viewport covers too much city — skip loading pins. */
const MIN_LOAD_ZOOM = 12.8

export default function App() {
  const [showLanding, setShowLanding] = useState(() => !hasVisitedBefore())

  const enterMap = useCallback(() => {
    markVisited()
    setShowLanding(false)
  }, [])

  if (showLanding) {
    return <Landing onEnter={enterMap} />
  }

  return <MapApp />
}

function MapApp() {
  const [meta, setMeta] = useState<MetaResponse | null>(null)
  const [mapData, setMapData] = useState<MapResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [metaLoading, setMetaLoading] = useState(true)
  const [pinsLoading, setPinsLoading] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [insight, setInsight] = useState<MeterInsight | null>(null)
  const [insightLoading, setInsightLoading] = useState(false)
  const [suburb, setSuburb] = useState('ALL')
  const [zoomTooWide, setZoomTooWide] = useState(false)
  const [focus, setFocus] = useState<{ lng: number; lat: number } | null>(null)

  const fetchSeq = useRef(0)
  const lastBBox = useRef<BBox | null>(null)
  const lastZoom = useRef(14)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        setMetaLoading(true)
        const data = await fetchMeta()
        if (!cancelled) {
          setMeta(data)
          setError(null)
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load')
      } finally {
        if (!cancelled) setMetaLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const loadViewport = useCallback(
    async (bbox: BBox, zoom: number) => {
      lastZoom.current = zoom
      if (zoom < MIN_LOAD_ZOOM) {
        setZoomTooWide(true)
        setMapData(null)
        return
      }
      setZoomTooWide(false)
      lastBBox.current = bbox
      const seq = ++fetchSeq.current
      setPinsLoading(true)
      try {
        const data = await fetchMetersInView(bbox, suburb, 250)
        if (seq === fetchSeq.current) {
          setMapData(data)
          setError(null)
        }
      } catch (e) {
        if (seq === fetchSeq.current) {
          setError(e instanceof Error ? e.message : 'Failed to load meters')
        }
      } finally {
        if (seq === fetchSeq.current) setPinsLoading(false)
      }
    },
    [suburb],
  )

  useEffect(() => {
    if (!lastBBox.current) return
    void loadViewport(lastBBox.current, lastZoom.current)
  }, [suburb, loadViewport])

  const selectMeter = useCallback(async (meterNo: string) => {
    setSelectedId(meterNo)
    setInsightLoading(true)
    try {
      const data = await fetchMeterInsight(meterNo)
      setInsight(data)
      setFocus({ lng: data.meter.longitude, lat: data.meter.latitude })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load meter')
    } finally {
      setInsightLoading(false)
    }
  }, [])

  const meters: MapPin[] = mapData?.meters ?? []

  const avgChance = useMemo(() => {
    const vals = meters
      .filter((m) => m.parkable !== false)
      .map((m) => m.chance_free)
      .filter((v): v is number => v != null)
    if (!vals.length) return null
    return vals.reduce((a, b) => a + b, 0) / vals.length
  }, [meters])

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand-block">
          <p className="brand">Brisbane Parking</p>
          <h1>Find a free bay before you circle the block.</h1>
        </div>
        <div className="status-block">
          {meta && (
            <>
              <p className="clock">{meta.brisbane_now}</p>
              <p className="next-hour">
                Next hour · {String(meta.next_hour).padStart(2, '0')}:00
                {meters.length > 0 && <> · view avg {formatPct(avgChance)}</>}
                {mapData && (
                  <>
                    {' '}
                    · {mapData.count}
                    {mapData.count >= mapData.limit ? '+' : ''} in view
                  </>
                )}
              </p>
            </>
          )}
          <label className="suburb-filter">
            <span>Suburb</span>
            <select value={suburb} onChange={(e) => setSuburb(e.target.value)}>
              <option value="ALL">All suburbs</option>
              {(meta?.suburbs ?? []).map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      <div className="legend">
        <span>
          <i style={{ background: '#0f8a4a' }} /> Likely
        </span>
        <span>
          <i style={{ background: '#d97706' }} /> Mixed
        </span>
        <span>
          <i style={{ background: '#c23030' }} /> Unlikely
        </span>
        <span>
          <i style={{ background: '#9a958c' }} /> Closed / restricted
        </span>
        {pinsLoading && <span className="legend-status">Updating view…</span>}
      </div>

      <main className="stage">
        {metaLoading && <div className="overlay-msg">Loading Brisbane map…</div>}
        {error && !metaLoading && <div className="overlay-msg error">{error}</div>}
        {!metaLoading && (
          <ParkingMap
            meters={meters}
            selectedId={selectedId}
            onSelect={selectMeter}
            onViewportChange={loadViewport}
            focus={focus}
          />
        )}
        {zoomTooWide && (
          <div className="zoom-hint">Zoom in to load parking meters for this area</div>
        )}
        {insight && selectedId && (
          <DetailPanel
            insight={insight}
            loading={insightLoading}
            onClose={() => {
              setSelectedId(null)
              setInsight(null)
              setFocus(null)
            }}
            onSelectNearby={selectMeter}
          />
        )}
      </main>

      <footer className="footer">
        Forecast occupancy from Brisbane City Council open data (CC BY 4.0). Not live sensors.
        {meta ? ` · ${meta.meter_count} meters total` : ''}
      </footer>
    </div>
  )
}
