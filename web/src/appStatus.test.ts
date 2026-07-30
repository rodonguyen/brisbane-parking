import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { shouldShowMapError } from './appStatus.ts'

describe('map status presentation', () => {
  it('hides a stale failure while the map is loading a viewport', () => {
    assert.equal(shouldShowMapError('Failed to load meters', false, true), false)
  })

  it('shows a failure after loading finishes', () => {
    assert.equal(shouldShowMapError('Failed to load meters', false, false), true)
  })

  it('hides failures while metadata is loading', () => {
    assert.equal(shouldShowMapError('Failed to load', true, false), false)
  })
})
