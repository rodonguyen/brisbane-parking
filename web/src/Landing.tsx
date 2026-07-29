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

/**
 * Design read: first-visit landing for Brisbane drivers, trust-first civic utility,
 * brand-led, calm river/leaf language (VARIANCE 4 / MOTION 3 / DENSITY 3).
 */
export function Landing({ onEnter }: Props) {
  return (
    <div className="landing">
      <div className="landing-atmosphere" aria-hidden="true">
        <span className="landing-bay landing-bay--a" />
        <span className="landing-bay landing-bay--b" />
        <span className="landing-bay landing-bay--c" />
        <span className="landing-bay landing-bay--d" />
        <div className="landing-river" />
      </div>

      <main className="landing-hero">
        <p className="landing-brand">Brisbane Parking</p>
        <h1 className="landing-headline">Find a free bay before you circle the block.</h1>
        <p className="landing-support">
          Next-hour forecasts for paid street meters, checked against hours and clearways.
        </p>
        <div className="landing-cta">
          <button type="button" className="landing-enter" onClick={onEnter}>
            Open the map
          </button>
        </div>
      </main>

      <p className="landing-note">
        Forecast data © Brisbane City Council (CC BY 4.0). Not live sensors.
      </p>
    </div>
  )
}
