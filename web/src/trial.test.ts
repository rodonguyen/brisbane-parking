import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import {
  FREE_DISTINCT_METERS,
  canOpenMeter,
  parseSeenMeters,
  serializeSeenMeters,
  withRecordedMeter,
} from './trial.ts'

/** Meter ids '1'..'n'. */
const meterIds = (n: number) => new Set(Array.from({ length: n }, (_, i) => String(i + 1)))

describe('meter trial gate', () => {
  it('gives signed-out users 20 free meters', () => {
    assert.equal(FREE_DISTINCT_METERS, 20)
  })

  it('allows signed-in users regardless of seen count', () => {
    const seen = meterIds(FREE_DISTINCT_METERS)
    assert.equal(canOpenMeter('new', seen, true), true)
  })

  it('allows a meter already seen without burning a new look', () => {
    const seen = meterIds(FREE_DISTINCT_METERS)
    assert.equal(canOpenMeter('3', seen, false), true)
  })

  it('allows new meters until the free distinct limit', () => {
    const seen = meterIds(FREE_DISTINCT_METERS - 1)
    assert.equal(canOpenMeter('new', seen, false), true)
  })

  it('blocks a new meter once the free limit of distinct meters is reached', () => {
    const seen = meterIds(FREE_DISTINCT_METERS)
    assert.equal(canOpenMeter('new', seen, false), false)
  })

  it('records only distinct meter ids', () => {
    const once = withRecordedMeter('10', new Set())
    const twice = withRecordedMeter('10', once)
    assert.deepEqual([...twice], ['10'])
  })

  it('round-trips seen meters through storage serialization', () => {
    const seen = new Set(['a', 'b'])
    assert.deepEqual(parseSeenMeters(serializeSeenMeters(seen)), seen)
    assert.deepEqual(parseSeenMeters(null), new Set())
    assert.deepEqual(parseSeenMeters('not-json'), new Set())
  })
})
