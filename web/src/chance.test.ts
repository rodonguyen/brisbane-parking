import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { chanceFromOccupancy, chanceWord } from './chance.ts'

describe('free-meter spot chance', () => {
  it('matches the server formula and clamps to 0..1', () => {
    assert.equal(chanceFromOccupancy(0), 1)
    assert.equal(Math.round(chanceFromOccupancy(3.45)! * 100), 31)
    assert.equal(chanceFromOccupancy(7), 0)
    assert.equal(chanceFromOccupancy(-1), 1)
  })

  it('is unknown without an occupancy forecast', () => {
    assert.equal(chanceFromOccupancy(null), null)
    assert.equal(chanceFromOccupancy(undefined), null)
  })

  it('uses the same thresholds as the server labels', () => {
    assert.equal(chanceWord(0.6), 'Likely')
    assert.equal(chanceWord(0.35), 'Mixed')
    assert.equal(chanceWord(0.31), 'Unlikely')
  })
})
