import { ArrowRight, MapPin } from '@phosphor-icons/react'
import { useEffect, useRef, useSyncExternalStore, type CSSProperties } from 'react'
import { SpaLink } from './SpaLink'
import './landing.css'

const VISITED_KEY = 'brisbane-parking-visited'

export function hasVisitedBefore(): boolean {
  try {
    return localStorage.getItem(VISITED_KEY) === '1'
  } catch {
    return false
  }
}

export function markVisited(): void {
  try {
    localStorage.setItem(VISITED_KEY, '1')
  } catch {
    // private mode / blocked storage — still allow enter
  }
}

type Props = {
  onEnter: () => void
}

const REDUCED_QUERY = '(prefers-reduced-motion: reduce)'

function subscribeReducedMotion(onChange: () => void): () => void {
  if (typeof window === 'undefined' || !window.matchMedia) return () => {}
  const mq = window.matchMedia(REDUCED_QUERY)
  mq.addEventListener('change', onChange)
  return () => mq.removeEventListener('change', onChange)
}

function getReducedMotion(): boolean {
  return typeof window !== 'undefined' && !!window.matchMedia?.(REDUCED_QUERY).matches
}

function usePrefersReducedMotion(): boolean {
  return useSyncExternalStore(subscribeReducedMotion, getReducedMotion, () => false)
}

/** Stagger delay for hero entrance (read by .landing-rise in landing.css). */
const delay = (ms: number) => ({ '--d': `${ms}ms` }) as CSSProperties

/** Free bay the hero car drives into (top kerb of the centre block). */
const FREE_BAY = { x: 236, y: 93 }
/** Car enters from below on the left street, turns the corner, slides into the free bay. */
const DRIVE_PATH = 'M 66 440 L 66 100 Q 66 66 100 66 L 196 66 C 217 66 214 93 236 93'
/** Car starts after the pins have dropped; the CSS "parked" pop (3.7s) is timed to match. */
const DRIVE_DELAY_MS = 1100

type Bay = { x: number; y: number; vertical?: boolean; tone: 'a' | 'b' | 'c' }

const PARKED: Bay[] = [
  { x: 128, y: 93, tone: 'a' },
  { x: 164, y: 93, tone: 'b' },
  { x: 200, y: 93, tone: 'c' },
  { x: 272, y: 93, tone: 'a' },
  { x: 93, y: 150, vertical: true, tone: 'c' },
  { x: 93, y: 190, vertical: true, tone: 'a' },
  { x: 93, y: 250, vertical: true, tone: 'b' },
  { x: 307, y: 140, vertical: true, tone: 'b' },
  { x: 307, y: 220, vertical: true, tone: 'a' },
  { x: 307, y: 260, vertical: true, tone: 'c' },
  { x: 150, y: 307, tone: 'b' },
  { x: 200, y: 307, tone: 'c' },
  { x: 250, y: 307, tone: 'a' },
]

/** Busy / full meters drop in first, then the free one lands. */
const FULL_PINS: { x: number; y: number; level: 'busy' | 'full' }[] = [
  { x: 128, y: 93, level: 'full' },
  { x: 93, y: 190, level: 'busy' },
  { x: 200, y: 307, level: 'full' },
]

function CarShape({ className }: { className: string }) {
  // Top-down car centred on the origin, nose pointing +x (matches animateMotion rotate="auto").
  return (
    <g className={className}>
      <rect x={-13} y={-7} width={26} height={14} rx={4.5} className="car-body" />
      <rect x={2} y={-5.5} width={6} height={11} rx={2} className="car-glass" />
      <rect x={-10} y={-5} width={4.5} height={10} rx={1.6} className="car-glass" />
    </g>
  )
}

function StreetScene({ reduced }: { reduced: boolean }) {
  const driveRef = useRef<SVGAnimateMotionElement>(null)
  const showRef = useRef<SVGSetElement>(null)

  useEffect(() => {
    if (reduced) return
    const t = window.setTimeout(() => {
      showRef.current?.beginElement()
      driveRef.current?.beginElement()
    }, DRIVE_DELAY_MS)
    return () => window.clearTimeout(t)
  }, [reduced])

  return (
    <svg className="landing-scene-svg" viewBox="0 0 400 400" focusable="false">
      <rect width={400} height={400} className="scene-ground" />

      {/* Streets */}
      <rect x={0} y={50} width={400} height={54} className="scene-road" />
      <rect x={0} y={296} width={400} height={54} className="scene-road" />
      <rect x={50} y={0} width={54} height={400} className="scene-road" />
      <rect x={296} y={0} width={54} height={400} className="scene-road" />
      <path d="M 0 66 H 400 M 0 334 H 400 M 66 0 V 400 M 334 0 V 400" className="scene-lane" />

      {/* Centre block: buildings + pocket park */}
      <rect x={112} y={112} width={176} height={176} rx={14} className="scene-block" />
      <rect x={124} y={124} width={70} height={64} rx={10} className="scene-building" />
      <rect x={206} y={124} width={70} height={94} rx={10} className="scene-building" />
      <rect x={124} y={200} width={70} height={76} rx={10} className="scene-park" />
      <circle cx={146} cy={226} r={11} className="scene-tree" />
      <circle cx={170} cy={252} r={9} className="scene-tree" />
      <rect x={206} y={230} width={70} height={46} rx={10} className="scene-building" />

      {/* Neighbouring blocks */}
      <rect x={-10} y={-10} width={52} height={52} rx={12} className="scene-building" />
      <rect x={358} y={-10} width={52} height={52} rx={12} className="scene-building" />
      <rect x={-10} y={358} width={52} height={52} rx={12} className="scene-park" />
      <rect x={358} y={358} width={52} height={52} rx={12} className="scene-building" />
      <rect x={112} y={-10} width={176} height={52} rx={12} className="scene-building scene-building--soft" />
      <rect x={112} y={358} width={176} height={52} rx={12} className="scene-building scene-building--soft" />
      <rect x={-10} y={112} width={52} height={176} rx={12} className="scene-park" />
      <rect x={358} y={112} width={52} height={176} rx={12} className="scene-building scene-building--soft" />

      {/* Parked cars */}
      {PARKED.map((b) => (
        <g key={`${b.x}-${b.y}`} transform={`translate(${b.x} ${b.y}) rotate(${b.vertical ? 90 : 0})`}>
          <CarShape className={`scene-car scene-car--${b.tone}`} />
        </g>
      ))}

      {/* The free bay */}
      <g transform={`translate(${FREE_BAY.x} ${FREE_BAY.y})`}>
        <rect x={-17} y={-11} width={34} height={22} rx={5} className="scene-free-bay" />
        <ellipse rx={21} ry={14} className="scene-free-ring" />
      </g>

      {/* Hero car */}
      {reduced ? (
        <g transform={`translate(${FREE_BAY.x} ${FREE_BAY.y})`}>
          <CarShape className="scene-car scene-car--hero" />
        </g>
      ) : (
        <g visibility="hidden">
          <set ref={showRef} attributeName="visibility" to="visible" begin="indefinite" fill="freeze" />
          <animateMotion
            ref={driveRef}
            path={DRIVE_PATH}
            rotate="auto"
            begin="indefinite"
            dur="2.6s"
            fill="freeze"
            calcMode="spline"
            keyPoints="0;1"
            keyTimes="0;1"
            keySplines="0.35 0 0.15 1"
          />
          <CarShape className="scene-car scene-car--hero" />
        </g>
      )}

      {/* Pins: positioned by the outer <g>, animated by the inner one */}
      {FULL_PINS.map((p, i) => (
        <g key={`${p.x}-${p.y}`} transform={`translate(${p.x - 13} ${p.y - 25})`}>
          <g className={`scene-pin scene-pin--${p.level}`} style={{ '--i': i } as CSSProperties}>
            <MapPin size={26} weight="fill" />
          </g>
        </g>
      ))}
      <g transform={`translate(${FREE_BAY.x - 19} ${FREE_BAY.y - 37})`}>
        <g className="scene-pin scene-pin--free">
          <g className="scene-pin-float">
            <MapPin size={38} weight="fill" />
          </g>
        </g>
      </g>
    </svg>
  )
}

/**
 * Design read: first-visit landing for Brisbane drivers, bright modern civic utility with a
 * playful street-scene story (pins drop, then the car heads straight for the free bay).
 * Dials: VARIANCE 6 / MOTION 6 / DENSITY 3. All motion collapses to static under reduced motion.
 */
export function Landing({ onEnter }: Props) {
  const reduced = usePrefersReducedMotion()

  return (
    <div className="landing">
      <main className="landing-hero">
        <div className="landing-copy">
          <p className="landing-brand landing-rise" style={delay(0)}>
            <span className="landing-brand-mark" aria-hidden="true">
              <MapPin size={18} weight="fill" />
            </span>
            Brisbane Parking
          </p>
          <h1 className="landing-headline landing-rise" style={delay(90)}>
            Find a <span className="landing-mark">free bay</span> before you circle the block.
          </h1>
          <p className="landing-support landing-rise" style={delay(200)}>
            Current-hour forecasts for paid street meters, checked against hours and clearways.
          </p>
          <div className="landing-cta landing-rise" style={delay(320)}>
            <button type="button" className="landing-enter" onClick={onEnter}>
              <span>Open the map</span>
              <span className="landing-enter-icon" aria-hidden="true">
                <ArrowRight size={20} weight="bold" />
              </span>
            </button>
          </div>
        </div>

        <div className="landing-scene" aria-hidden="true">
          <StreetScene reduced={reduced} />
        </div>
      </main>

      <p className="landing-note">
        Forecast data © Brisbane City Council (CC BY 4.0). Not live sensors.{' '}
        <SpaLink to="terms">Terms</SpaLink>
        <span aria-hidden="true"> · </span>
        <SpaLink to="privacy">Privacy</SpaLink>
      </p>
    </div>
  )
}
