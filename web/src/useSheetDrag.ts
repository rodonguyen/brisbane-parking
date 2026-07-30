import { useCallback, useEffect, useRef, useState } from 'react'

const DISMISS_DISTANCE = 96
const DISMISS_VELOCITY = 0.55
const SCROLL_DRAG_START = 10

type Tracking = {
  pointerId: number
  startY: number
  lastY: number
  lastT: number
  dragging: boolean
}

type Options = {
  enabled: boolean
  onClose: () => void
  onDrag?: (offsetY: number) => void
}

export function useMobileViewport(maxWidth = 820) {
  const query = `(max-width: ${maxWidth}px)`
  const [mobile, setMobile] = useState(
    () => typeof window !== 'undefined' && window.matchMedia(query).matches,
  )

  useEffect(() => {
    const mq = window.matchMedia(query)
    const sync = () => setMobile(mq.matches)
    sync()
    mq.addEventListener('change', sync)
    return () => mq.removeEventListener('change', sync)
  }, [query])

  return mobile
}

export function useSheetDrag({ enabled, onClose, onDrag }: Options) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const tracking = useRef<Tracking | null>(null)
  const [dragY, setDragY] = useState(0)
  const [dragging, setDragging] = useState(false)

  const applyDrag = useCallback(
    (y: number) => {
      setDragY(y)
      onDrag?.(y)
    },
    [onDrag],
  )

  const resetDrag = useCallback(() => {
    tracking.current = null
    setDragging(false)
    applyDrag(0)
  }, [applyDrag])

  const beginTracking = useCallback((pointerId: number, startY: number, draggingNow: boolean) => {
    tracking.current = {
      pointerId,
      startY,
      lastY: startY,
      lastT: performance.now(),
      dragging: draggingNow,
    }
    setDragging(draggingNow)
  }, [])

  const onGrabPointerDown = useCallback(
    (e: React.PointerEvent<HTMLElement>) => {
      if (!enabled || e.button !== 0) return
      if ((e.target as HTMLElement).closest('.close-btn')) return
      e.currentTarget.setPointerCapture(e.pointerId)
      beginTracking(e.pointerId, e.clientY, true)
    },
    [beginTracking, enabled],
  )

  const onScrollPointerDown = useCallback(
    (e: React.PointerEvent<HTMLElement>) => {
      if (!enabled || e.button !== 0) return
      if ((scrollRef.current?.scrollTop ?? 0) > 0) return
      beginTracking(e.pointerId, e.clientY, false)
    },
    [beginTracking, enabled],
  )

  const onPointerMove = useCallback(
    (e: React.PointerEvent<HTMLElement>) => {
      const t = tracking.current
      if (!t || e.pointerId !== t.pointerId) return

      const dy = e.clientY - t.startY

      if (!t.dragging) {
        if ((scrollRef.current?.scrollTop ?? 0) > 0) {
          resetDrag()
          return
        }
        if (dy <= SCROLL_DRAG_START) return
        t.dragging = true
        setDragging(true)
        e.currentTarget.setPointerCapture(e.pointerId)
      }

      if (dy <= 0) {
        applyDrag(0)
        return
      }

      applyDrag(dy)
      t.lastY = e.clientY
      t.lastT = performance.now()
      e.preventDefault()
    },
    [applyDrag, resetDrag],
  )

  const finishPointer = useCallback(
    (e: React.PointerEvent<HTMLElement>) => {
      const t = tracking.current
      if (!t || e.pointerId !== t.pointerId) return

      const dy = e.clientY - t.startY
      const velocity = (e.clientY - t.lastY) / Math.max(performance.now() - t.lastT, 1)

      tracking.current = null
      setDragging(false)

      if (t.dragging && (dy > DISMISS_DISTANCE || velocity > DISMISS_VELOCITY)) {
        applyDrag(0)
        onClose()
        return
      }

      applyDrag(0)
    },
    [applyDrag, onClose],
  )

  const sheetStyle =
    enabled && dragY > 0
      ? ({
          transform: `translateY(${dragY}px)`,
          transition: dragging ? 'none' : 'transform 220ms cubic-bezier(0.32, 0.72, 0, 1)',
        } as const)
      : undefined

  return {
    scrollRef,
    dragY,
    dragging,
    sheetStyle,
    resetDrag,
    onGrabPointerDown,
    onScrollPointerDown,
    onPointerMove,
    finishPointer,
  }
}
