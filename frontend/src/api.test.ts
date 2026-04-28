import { buildApiUrl } from './api'

describe('frontend API URL builder', () => {
  it('defaults to relative /api URLs for local Vite proxy', () => {
    expect(buildApiUrl('/parking-lots', { lat: 37.5665, lng: 126.978, radius_m: 3000 })).toBe(
      '/api/parking-lots?lat=37.5665&lng=126.978&radius_m=3000',
    )
  })

  it('uses an absolute backend origin when VITE_API_BASE_URL is provided', () => {
    expect(
      buildApiUrl('/parking-lots', { lat: 37.5665, lng: 126.978, radius_m: 3000 }, 'https://parking-api.onrender.com'),
    ).toBe('https://parking-api.onrender.com/api/parking-lots?lat=37.5665&lng=126.978&radius_m=3000')
  })

  it('does not duplicate /api when the configured backend URL already includes it', () => {
    expect(buildApiUrl('/parking-lots', { lat: 37.5665 }, 'https://parking-api.onrender.com/api/')).toBe(
      'https://parking-api.onrender.com/api/parking-lots?lat=37.5665',
    )
  })
})
