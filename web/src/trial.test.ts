import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import {
  FREE_DISTINCT_METERS,
  canOpenMeter,
  parseSeenMeters,
  serializeSeenMeters,
  withRecordedMeter,
} from './trial.ts'

describe('meter trial gate', () => {
  it('allows signed-in users regardless of seen count', () => {
    const seen = new Set(['1', '2', '3', '4', '5'])
    assert.equal(canOpenMeter('6', seen, true), true)
  })

  it('allows a meter already seen without burning a new look', () => {
    const seen = new Set(['1', '2', '3', '4', '5'])
    assert.equal(canOpenMeter('3', seen, false), true)
  })

  it('allows new meters until the free distinct limit', () => {
    const seen = new Set(['1', '2', '3', '4'])
    assert.equal(seen.size, FREE_DISTINCT_METERS - 1)
    assert.equal(canOpenMeter('5', seen, false), true)
  })

  it('blocks a new meter once five distinct meters were opened', () => {
    const seen = new Set(['1', '2', '3', '4', '5'])
    assert.equal(canOpenMeter('6', seen, false), false)
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
