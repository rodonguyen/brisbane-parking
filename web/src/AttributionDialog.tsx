import { useEffect } from 'react'

type Props = {
  meterCount?: number
  onClose: () => void
}

export function AttributionDialog({ meterCount, onClose }: Props) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="attribution-dialog" role="presentation" onClick={onClose}>
      <div
        className="attribution-dialog__card"
        role="dialog"
        aria-labelledby="attribution-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="attribution-dialog__head">
          <h2 id="attribution-title">Open data</h2>
          <button type="button" className="attribution-dialog__close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <p>
          Forecast occupancy from Brisbane City Council open data (CC BY 4.0). This is not live
          sensor data — it is a statistical forecast built from historical patterns.
          {meterCount ? ` The map covers ${meterCount.toLocaleString()} meters across Brisbane.` : ''}
        </p>
        <p>
          <a
            href="https://www.data.brisbane.qld.gov.au/"
            target="_blank"
            rel="noopener noreferrer"
          >
            Brisbane Open Data portal
          </a>
        </p>
      </div>
    </div>
  )
}
