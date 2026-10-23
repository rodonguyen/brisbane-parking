import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { directionsUrls, distanceMeters, formatDistance } from './directions.ts'

const meter = { lat: -27.4698, lng: 153.0251 }
const user = { lat: -27.4705, lng: 153.0235 }

describe('directions links', () => {
  it('builds destination-only links when location is unknown', () => {
    assert.deepEqual(directionsUrls(meter), {
      apple: 'https://maps.apple.com/?daddr=-27.4698%2C153.0251&dirflg=d',
      google: 'https://www.google.com/maps/dir/?api=1&destination=-27.4698%2C153.0251&travelmode=driving',
    })
  })

  it('adds the user location as origin when known', () => {
    const urls = directionsUrls(meter, user)
    assert.equal(urls.apple, 'https://maps.apple.com/?daddr=-27.4698%2C153.0251&dirflg=d&saddr=-27.4705%2C153.0235')
    assert.equal(
      urls.google,
      'https://www.google.com/maps/dir/?api=1&destination=-27.4698%2C153.0251&travelmode=driving&origin=-27.4705%2C153.0235',
    )
  })
})

describe('distance', () => {
  it('measures ~176 m between two CBD points', () => {
    assert.equal(Math.round(distanceMeters(user, meter)), 176)
  })

  it('formats metres and kilometres', () => {
    assert.equal(formatDistance(178), '180 m')
    assert.equal(formatDistance(1234), '1.2 km')
  })
})
