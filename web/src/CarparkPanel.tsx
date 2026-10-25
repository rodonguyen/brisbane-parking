import type { Carpark } from './api'
import './carpark.css'
import type { LngLat } from './directions'
import { directionsUrls, distanceMeters, formatDistance } from './directions'
import { useMobileViewport, useSheetDrag } from './useSheetDrag'

type Props = {
  carpark: Carpark
  onClose: () => void
  onDrag?: (offsetY: number) => void
  userLoc: LngLat | null
}

export function CarparkPanel({ carpark: c, onClose, onDrag, userLoc }: Props) {
  const mobileSheet = useMobileViewport()
  const { scrollRef, dragging, sheetStyle, onGrabPointerDown, onScrollPointerDown, onPointerMove, finishPointer } =
    useSheetDrag({ enabled: mobileSheet, onClose, onDrag })

  const dest = { lat: c.lat, lng: c.lng }
  const directions = directionsUrls(dest, userLoc)

  return (
    <aside
      className={`detail-panel carpark-panel${dragging ? ' detail-panel--dragging' : ''}`}
      style={sheetStyle}
      aria-live="polite"
      onPointerMove={onPointerMove}
      onPointerUp={finishPointer}
      onPointerCancel={finishPointer}
    >
      <div className="detail-panel__bar" onPointerDown={onGrabPointerDown}>
        <div className="detail-panel__grab" aria-hidden="true">
          <span className="detail-panel__handle" />
        </div>
        <button type="button" className="close-btn" onClick={onClose} aria-label="Close">
          Close
        </button>
      </div>
      <div className="detail-panel__scroll" ref={scrollRef} onPointerDown={onScrollPointerDown}>
        <div className="detail-top">
          <h2>
            {c.name}
            {c.operator && <span>{c.operator}</span>}
          </h2>
          {c.address && <p className="loc">{c.address}</p>}
        </div>

        {(c.hours_lines.length > 0 || c.height_m != null) && (
          <section className="facts">
            <dl>
              {c.hours_lines.length > 0 && (
                <div className={`carpark-hours${c.hours_lines.length > 1 ? ' facts-wide' : ''}`}>
                  <dt>Hours</dt>
                  <dd>
                    {c.hours_lines.map((ln, i) => (
                      <span key={i} className="carpark-hours-line">
                        {ln.days && <b>{ln.days}</b>} {ln.time}
                      </span>
                    ))}
                  </dd>
                </div>
              )}
              {c.height_m != null && (
                <div>
                  <dt>Max height</dt>
                  <dd>{c.height_m} m</dd>
                </div>
              )}
            </dl>
          </section>
        )}

        <section className="carpark-rates" aria-label="Prices">
          {c.rates.length === 0 && <p className="carpark-none">Prices not published</p>}
          {c.rates.map((g) => (
            <div key={g.title} className="carpark-group">
              <h3>{g.title}</h3>
              <ul>
                {g.rows.map((r, i) => (
                  <li key={i}>
                    <span className="carpark-row-label">
                      {r.label}
                      {r.when && <em>{r.when}</em>}
                    </span>
                    <span className="carpark-row-price">
                      {r.price ?? r.online_price}
                      {r.price && r.online_price && <em>{r.online_price} online</em>}
                      {!r.price && r.online_price && <em>online only</em>}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </section>

        <section className="directions" aria-label="Directions">
          <p className="directions-label">
            Directions{userLoc ? ` · ${formatDistance(distanceMeters(userLoc, dest))} away` : ''}
          </p>
          <div className="directions-links">
            <a className="directions-btn" href={directions.apple} target="_blank" rel="noopener noreferrer">
              Apple Maps
            </a>
            <a className="directions-btn" href={directions.google} target="_blank" rel="noopener noreferrer">
              Google Maps
            </a>
          </div>
        </section>

        {c.url && (
          <a className="carpark-page-btn" href={c.url} target="_blank" rel="noopener noreferrer">
            View car park page
          </a>
        )}
        {/* Room to scroll the last buttons up past the bottom edge / home indicator. */}
        <div className="carpark-scroll-pad" aria-hidden="true" />
      </div>
    </aside>
  )
}
