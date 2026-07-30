import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { resolvePublishableKey } from './support.ts'

describe('stripe publishable key resolution', () => {
  it('accepts test and live publishable keys', () => {
    assert.equal(resolvePublishableKey('pk_test_abc123'), 'pk_test_abc123')
    assert.equal(resolvePublishableKey('pk_live_abc123'), 'pk_live_abc123')
  })

  it('trims surrounding whitespace from env values', () => {
    assert.equal(resolvePublishableKey('  pk_test_abc123  '), 'pk_test_abc123')
  })

  it('refuses a secret key so it can never reach the bundle', () => {
    assert.equal(resolvePublishableKey('sk_test_abc123'), null)
    assert.equal(resolvePublishableKey('rk_live_abc123'), null)
  })

  it('disables the tip jar when unset or blank', () => {
    assert.equal(resolvePublishableKey(undefined), null)
    assert.equal(resolvePublishableKey('   '), null)
  })
})
