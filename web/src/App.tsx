import {
  Show,
  SignInButton,
  SignUpButton,
  useAuth,
} from '@clerk/react'
import { CircleNotchIcon } from '@phosphor-icons/react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  fetchMeta,
  fetchMeterInsight,
  fetchMetersInView,
  type BBox,
  type MapPin,
  type MapResponse,
  type MetaResponse,
  type MeterInsight,
} from './api'
import { AttributionDialog } from './AttributionDialog'
import { DetailPanel } from './DetailPanel'
import { hasVisitedBefore, Landing, markVisited } from './Landing'
import { LegalPage } from './LegalPage'
import { ParkingMap } from './ParkingMap'
import { getRoute, subscribe, type AppRoute } from './route'
import { SpaLink } from './SpaLink'
import { SUPPORT_FOOTER_SUFFIX, SUPPORT_LABEL } from './support'
import { supportEnabled } from './supportConfig'
import { SupportFooterButton, SupportIconButton } from './SupportButtons'
import { SupporterUserButton } from './SupporterUserButton'
import { SupportDialog } from './SupportDialog'
import {
  FREE_DISTINCT_METERS,
  canOpenMeter,
  loadSeenMeters,
  saveSeenMeters,
  withRecordedMeter,
} from './trial'
import { shouldShowMapError } from './appStatus'
import type { LngLat } from './directions'
import { useSupporter } from './useSupporter'

/** Covers every BCC meter (945 pins), so one fetch serves all pans and zooms. */
// ponytail: whole city in one request; switch back to viewport fetches if meters exceed the API limit (1000).
const CITY_BBOX: BBox = { west: 152.98, south: -27.52, east: 153.07, north: -27.42 }
/** Forecasts change hourly; refresh often enough to catch the hour rollover. */
const REFRESH_MS = 5 * 60 * 1000

function inBBox(m: MapPin, b: BBox): boolean {
  return m.longitude >= b.west && m.longitude <= b.east && m.latitude >= b.south && m.latitude <= b.north
}

export default function App() {
  const [route, setRoute] = useState<AppRoute>(() => getRoute())
  const [showLanding, setShowLanding] = useState(() => !hasVisitedBefore())

  useEffect(() => subscribe(setRoute), [])

  const enterMap = useCallback(() => {
    markVisited()
    setShowLanding(false)
  }, [])

  if (route === 'terms' || route === 'privacy') {
    return <LegalPage doc={route} />
  }

  if (showLanding) {
    return <Landing onEnter={enterMap} />
  }

  return <MapApp />
}

function MapApp() {
  const { isSignedIn } = useAuth()
  const [meta, setMeta] = useState<MetaResponse | null>(null)
  const [mapData, setMapData] = useState<MapResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [metaLoading, setMetaLoading] = useState(true)
  const [pinsLoading, setPinsLoading] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [insight, setInsight] = useState<MeterInsight | null>(null)
  const [insightLoading, setInsightLoading] = useState(false)
  const [viewBBox, setViewBBox] = useState<BBox | null>(null)
  const [userLoc, setUserLoc] = useState<LngLat | null>(null)
  const [focus, setFocus] = useState<{ lng: number; lat: number } | null>(null)
  const [seenMeters, setSeenMeters] = useState<Set<string>>(() => loadSeenMeters())
  const [signInGate, setSignInGate] = useState(false)
  const [pendingMeter, setPendingMeter] = useState<string | null>(null)
  const [supportOpen, setSupportOpen] = useState(false)
  const [attributionOpen, setAttributionOpen] = useState(false)
  const [sheetDragY, setSheetDragY] = useState(0)
  const { isSupporter, refresh: refreshSupporter } = useSupporter()

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

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setPinsLoading(true)
      try {
        const data = await fetchMetersInView(CITY_BBOX, 'ALL', 1000)
        if (!cancelled) {
          setMapData(data)
          setError(null)
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load meters')
      } finally {
        if (!cancelled) setPinsLoading(false)
      }
    }
    void load()
    const timer = setInterval(load, REFRESH_MS)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [])

  const onViewportChange = useCallback((bbox: BBox) => setViewBBox(bbox), [])

  const openMeterInsight = useCallback(async (meterNo: string) => {
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

  const closeMeterDetail = useCallback(() => {
    setSelectedId(null)
    setInsight(null)
    setFocus(null)
  }, [])

  const selectMeter = useCallback(
    async (meterNo: string) => {
      const signedIn = Boolean(isSignedIn)
      if (!canOpenMeter(meterNo, seenMeters, signedIn)) {
        setPendingMeter(meterNo)
        setSignInGate(true)
        return
      }

      if (!signedIn && !seenMeters.has(meterNo)) {
        const next = withRecordedMeter(meterNo, seenMeters)
        setSeenMeters(next)
        try {
          saveSeenMeters(next)
        } catch {
          // private mode / blocked storage — still allow this open
        }
      }

      setSignInGate(false)
      await openMeterInsight(meterNo)
    },
    [isSignedIn, seenMeters, openMeterInsight],
  )

  useEffect(() => {
    if (!isSignedIn || !pendingMeter) return
    const meterNo = pendingMeter
    setPendingMeter(null)
    setSignInGate(false)
    void openMeterInsight(meterNo)
  }, [isSignedIn, pendingMeter, openMeterInsight])

  const meters: MapPin[] = useMemo(() => mapData?.meters ?? [], [mapData])
  const inViewCount = useMemo(
    () => (viewBBox ? meters.filter((m) => inBBox(m, viewBBox)).length : meters.length),
    [meters, viewBBox],
  )
  const freeLeft = Math.max(0, FREE_DISTINCT_METERS - seenMeters.size)
  const detailOpen = Boolean(insight && selectedId)
  const sheetDragProgress = Math.min(sheetDragY / 280, 1)

  useEffect(() => {
    if (!detailOpen) setSheetDragY(0)
  }, [detailOpen])

  return (
    <div
      className={`app${detailOpen ? ' app--detail-open' : ''}${sheetDragY > 0 ? ' app--detail-dragging' : ''}`}
      style={{ '--sheet-drag-progress': sheetDragProgress } as React.CSSProperties}
    >
      <div className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <p className="brand">Brisbane Parking</p>
          <h1>Find a free bay before you circle the block.</h1>
        </div>
        <div className="status-block">
          {meta && (
            <p className="next-hour">
              Next hour · {String(meta.next_hour).padStart(2, '0')}:00
              {mapData && (
                <>
                  {' '}
                  · {inViewCount} in view
                </>
              )}
            </p>
          )}
          <div className="auth-controls">
            <SupportIconButton
              onOpen={() => setSupportOpen(true)}
              isSupporter={isSupporter}
            />
            <Show when="signed-out">
              {!signInGate && freeLeft < FREE_DISTINCT_METERS && (
                <span className="trial-left">
                  {freeLeft === 0
                    ? 'Sign in for more meters'
                    : `${freeLeft} free meter${freeLeft === 1 ? '' : 's'} left`}
                </span>
              )}
              <SignInButton mode="modal">
                <button type="button" className="auth-btn">
                  Sign in
                </button>
              </SignInButton>
              <SignUpButton mode="modal">
                <button type="button" className="auth-btn auth-btn--primary">
                  Sign up
                </button>
              </SignUpButton>
            </Show>
            <Show when="signed-in">
              <SupporterUserButton isSupporter={isSupporter} />
            </Show>
          </div>
        </div>
      </header>

      <div className="legend">
        <span>
          <i style={{ background: '#2f7d6d' }} /> Likely
        </span>
        <span>
          <i style={{ background: '#d97706' }} /> Mixed
        </span>
        <span>
          <i style={{ background: '#c23030' }} /> Unlikely
        </span>
        <span>
          <i style={{ background: '#16c45a' }} /> Free
        </span>
        <span>
          <i style={{ background: '#9a958c' }} /> No parking
        </span>
        <span
          className="legend-status"
          data-loading={pinsLoading}
          role="status"
          aria-label={pinsLoading ? 'Updating map view' : undefined}
          aria-hidden={!pinsLoading}
        >
          <CircleNotchIcon className="legend-spinner" size={14} weight="bold" aria-hidden="true" />
        </span>
      </div>

      <main className="stage">
        {metaLoading && <div className="overlay-msg">Loading Brisbane map…</div>}
        {shouldShowMapError(error, metaLoading, pinsLoading) && (
          <div className="overlay-msg error">{error}</div>
        )}
        {!metaLoading && (
          <ParkingMap
            meters={meters}
            selectedId={selectedId}
            onSelect={selectMeter}
            onViewportChange={onViewportChange}
            onUserLocation={setUserLoc}
            focus={focus}
          />
        )}
        {signInGate && (
          <div className="sign-in-gate" role="dialog" aria-labelledby="sign-in-gate-title">
            <div className="sign-in-gate__card">
              <h2 id="sign-in-gate-title">Keep exploring</h2>
              <p>
                You’ve opened {FREE_DISTINCT_METERS} meters. Sign in free with Google (or
                email) to open more.
              </p>
              <div className="sign-in-gate__actions">
                <SignInButton mode="modal">
                  <button type="button" className="auth-btn auth-btn--primary">
                    Sign in
                  </button>
                </SignInButton>
                <SignUpButton mode="modal">
                  <button type="button" className="auth-btn">
                    Sign up
                  </button>
                </SignUpButton>
                <button
                  type="button"
                  className="auth-btn sign-in-gate__dismiss"
                  onClick={() => {
                    setSignInGate(false)
                    setPendingMeter(null)
                  }}
                >
                  Not now
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      <footer className={`footer${detailOpen ? ' footer--detail-open' : ''}`}>
        <p className="footer-mobile">
          {supportEnabled && (
            <>
              <button
                type="button"
                className="footer-inline-link"
                onClick={() => setSupportOpen(true)}
              >
                {SUPPORT_LABEL}
              </button>{' '}
              {SUPPORT_FOOTER_SUFFIX}
              {' · '}
            </>
          )}
          <SpaLink to="terms">Terms</SpaLink>
          <span aria-hidden="true"> · </span>
          <SpaLink to="privacy">Privacy</SpaLink>
          <span aria-hidden="true"> · </span>
          <button
            type="button"
            className="footer-inline-link"
            onClick={() => setAttributionOpen(true)}
          >
            Open data
          </button>
        </p>
        <span className="footer-desktop">
          Forecast occupancy from Brisbane City Council open data (CC BY 4.0). Not live
          sensors.
          {meta ? ` · ${meta.meter_count} meters total` : ''}
        </span>
        <span className="footer-desktop">
          <SupportFooterButton onOpen={() => setSupportOpen(true)} />
        </span>
        <span className="footer-links footer-desktop">
          <SpaLink to="terms">Terms</SpaLink>
          <span aria-hidden="true"> · </span>
          <SpaLink to="privacy">Privacy</SpaLink>
        </span>
      </footer>
      </div>

      {detailOpen && insight && (
        <div className="detail-layer">
          <button
            type="button"
            className="detail-scrim"
            aria-label="Close parking details"
            onClick={closeMeterDetail}
            style={{ opacity: 1 - sheetDragProgress * 0.85 }}
          />
          <DetailPanel
            insight={insight}
            loading={insightLoading}
            onClose={closeMeterDetail}
            onSelectNearby={selectMeter}
            onDrag={setSheetDragY}
            userLoc={userLoc}
          />
        </div>
      )}

      {supportOpen && (
        <SupportDialog
          onClose={() => setSupportOpen(false)}
          onPaid={() => void refreshSupporter()}
        />
      )}
      {attributionOpen && (
        <AttributionDialog
          meterCount={meta?.meter_count}
          onClose={() => setAttributionOpen(false)}
        />
      )}
    </div>
  )
}
