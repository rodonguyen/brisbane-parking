import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { MeterInsight } from './api'
import { chanceColor, formatPct } from './api'
import { chanceFromOccupancy, chanceWord } from './chance'
import type { LngLat } from './directions'
import { directionsUrls, distanceMeters, formatDistance } from './directions'
import { useMobileViewport, useSheetDrag } from './useSheetDrag'

type Props = {
  insight: MeterInsight
  loading: boolean
  onClose: () => void
  onSelectNearby: (meterNo: string) => void
  onDrag?: (offsetY: number) => void
  userLoc: LngLat | null
}

function hourLabel(h: number) {
  const suffix = h >= 12 ? 'pm' : 'am'
  const h12 = h % 12 === 0 ? 12 : h % 12
  return `${h12}${suffix}`
}

export function DetailPanel({ insight, loading, onClose, onSelectNearby, onDrag, userLoc }: Props) {
  const mobileSheet = useMobileViewport()
  const { scrollRef, dragging, sheetStyle, onGrabPointerDown, onScrollPointerDown, onPointerMove, finishPointer } =
    useSheetDrag({
      enabled: mobileSheet,
      onClose,
      onDrag,
    })

  const m = insight.meter
  const parkStatus = insight.park_status
  const isFree = parkStatus === 'free'
  const isBlocked = parkStatus === 'restricted' || insight.parkable === false
  const chance = insight.next_hour_chance_free
  const color = chanceColor(chance, insight.parkable !== false, parkStatus)
  // Free meters cost nothing but can still be full; the API omits their chance, so derive it.
  const freeSpotChance = isFree ? chanceFromOccupancy(insight.next_hour_occupancy) : null
  const dest = { lat: m.latitude, lng: m.longitude }
  const directions = directionsUrls(dest, userLoc)

  const seriesMap = new Map<number, { hour: number; today?: number; typical?: number }>()
  for (const p of insight.typical_series) {
    // Chance chart only for paid operating hours
    if (p.park_status ? p.park_status !== 'operating' : p.parkable === false) continue
    seriesMap.set(p.hour, { hour: p.hour, typical: Math.round(p.chance_free * 100) })
  }
  for (const p of insight.today_series) {
    if (p.park_status ? p.park_status !== 'operating' : p.parkable === false) continue
    const prev = seriesMap.get(p.hour) ?? { hour: p.hour }
    prev.today = Math.round(p.chance_free * 100)
    seriesMap.set(p.hour, prev)
  }
  const chartData = [...seriesMap.values()].sort((a, b) => a.hour - b.hour)

  const contextData = insight.context_comparison.map((c) => ({
    label: c.label.replace(' (same season)', ''),
    chance: Math.round(c.chance_free * 100),
    samples: c.sample_count,
  }))

  const heroKicker = isFree
    ? `Now (${hourLabel(insight.next_hour)})`
    : isBlocked
      ? `Now (${hourLabel(insight.next_hour)})`
      : `Chance of a spot · now (${hourLabel(insight.next_hour)})`
  const heroValue = isFree ? 'Free' : isBlocked ? 'No' : formatPct(chance)

  return (
    <aside
      className={`detail-panel ${loading ? 'is-loading' : ''}${dragging ? ' detail-panel--dragging' : ''}`}
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
      <div
        className="detail-panel__scroll"
        ref={scrollRef}
        onPointerDown={onScrollPointerDown}
      >
      <div className="detail-top">
        <p className="eyebrow">
          Meter {m.meter_no} · Zone {m.mobile_zone}
        </p>
        <h2>
          {m.street}
          <span>{m.suburb}</span>
        </h2>
        <p className="loc">{m.loc_desc}</p>
      </div>

      <div className="chance-hero" style={{ ['--chance' as string]: color }}>
        <p className="chance-kicker">{heroKicker}</p>
        <p className="chance-value">{heroValue}</p>
        {freeSpotChance != null ? (
          <p className="chance-label">
            <span className="chance-spot" style={{ color: chanceColor(freeSpotChance) }}>
              {formatPct(freeSpotChance)} chance of a spot
            </span>{' '}
            · {chanceWord(freeSpotChance)}
          </p>
        ) : (
          <p className="chance-label">{insight.next_hour_label}</p>
        )}
        <p className="chance-meta">
          {insight.park_reason
            ? insight.park_reason
            : `${insight.day_class}${insight.is_holiday ? ' holiday' : ''} · ${insight.season} · ${insight.lookup_method}`}
        </p>
      </div>

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

      <section className="facts">
        <dl>
          <div>
            <dt>Max stay</dt>
            <dd>{m.max_stay_hrs || '—'}h</dd>
          </div>
          <div>
            <dt>Bays</dt>
            <dd>{m.veh_bays}</dd>
          </div>
          <div>
            <dt>Weekday rate</dt>
            <dd>{m.tar_rate_weekday ? `$${m.tar_rate_weekday}/h` : '—'}</dd>
          </div>
          <div>
            <dt>Hours</dt>
            <dd>
              {m.operational_day} {m.operational_time}
            </dd>
          </div>
          {m.restrictions && m.restrictions !== 'NONE' && (
            <div className="facts-wide">
              <dt>Restrictions</dt>
              <dd>{m.restrictions}</dd>
            </div>
          )}
        </dl>
      </section>

      {chartData.length > 0 && (
        <section className="chart-block">
          <h3>Free chance by hour</h3>
          <p className="chart-note">Today’s forecast vs typical {insight.day_class} in {insight.season}</p>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="rgba(40,36,30,0.08)" vertical={false} />
                <XAxis
                  dataKey="hour"
                  tickFormatter={hourLabel}
                  tick={{ fill: '#5c564c', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  domain={[0, 100]}
                  ticks={[0, 20, 40, 60, 80, 100]}
                  tickFormatter={(v) => `${v}%`}
                  tick={{ fill: '#5c564c', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  width={40}
                />
                <Tooltip
                  formatter={(value) => [`${value}%`, '']}
                  labelFormatter={(h) => hourLabel(Number(h))}
                  contentStyle={{
                    background: '#f7f2e8',
                    border: '1px solid rgba(40,36,30,0.12)',
                    borderRadius: 0,
                    fontSize: 12,
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Line
                  type="monotone"
                  dataKey="typical"
                  name="Typical"
                  stroke="#8a7a5c"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="today"
                  name="Today"
                  stroke="#1f5c8a"
                  strokeWidth={2.5}
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      {contextData.length > 0 && (
        <section className="chart-block">
          <h3>Same hour, different days</h3>
          <p className="chart-note">How {hourLabel(insight.next_hour)} usually compares</p>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={contextData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="rgba(40,36,30,0.08)" vertical={false} />
                <XAxis dataKey="label" tick={{ fill: '#5c564c', fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis
                  domain={[0, 100]}
                  ticks={[0, 20, 40, 60, 80, 100]}
                  tickFormatter={(v) => `${v}%`}
                  tick={{ fill: '#5c564c', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  width={40}
                />
                <Tooltip
                  formatter={(value, _n, item) => [
                    `${value}% free (${item.payload.samples} samples)`,
                    'Chance',
                  ]}
                  contentStyle={{
                    background: '#f7f2e8',
                    border: '1px solid rgba(40,36,30,0.12)',
                    borderRadius: 0,
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="chance" fill="#1f7a4c" radius={0} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      {insight.nearby.length > 0 && (
        <section className="nearby">
          <h3>Better nearby</h3>
          <ul>
            {insight.nearby.map((n) => (
              <li key={n.meter_no}>
                <button type="button" onClick={() => onSelectNearby(n.meter_no)}>
                  <span className="nearby-street">
                    {n.street}
                    <em>{n.suburb}</em>
                  </span>
                  <span className="nearby-meta">
                    {Math.round(n.distance_m)}m ·{' '}
                    {n.park_status === 'free' ? 'Free' : formatPct(n.chance_free)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
      </div>
    </aside>
  )
}
