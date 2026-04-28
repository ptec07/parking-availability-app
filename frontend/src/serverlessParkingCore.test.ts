import { describe, expect, it, vi } from 'vitest'

import {
  findParkingLots,
  geocodeDestination,
  normalizeQuery,
  type KakaoDocument,
  type ParkingLotData,
} from './serverlessParkingCore'

const sampleLots: ParkingLotData[] = [
  {
    id: 'near',
    name: '가까운 공영주차장',
    address: '서울 강남구 테헤란로',
    lat: 37.498,
    lng: 127.028,
    total_spaces: 100,
    occupied_spaces: 40,
    updated_at: '2026-04-28T14:13:23+09:00',
  },
  {
    id: 'far',
    name: '먼 공영주차장',
    address: '서울 중구 세종대로',
    lat: 37.5665,
    lng: 126.978,
    total_spaces: 100,
    occupied_spaces: 20,
    updated_at: '2026-04-28T14:13:23+09:00',
  },
]

describe('serverless API core', () => {
  it('normalizes a destination query', () => {
    expect(normalizeQuery('  강남역   2번출구 ')).toBe('강남역 2번출구')
    expect(normalizeQuery('   ')).toBe('')
  })

  it('geocodes with Kakao address search and falls back to keyword search', async () => {
    const fetcher = vi.fn(async (url: RequestInfo | URL): Promise<Response> => {
      const docs: KakaoDocument[] = String(url).includes('/keyword.json')
        ? [{ x: '127.02800140627488', y: '37.49808633653005', address_name: '서울 강남구 역삼동 858' }]
        : []
      return new Response(JSON.stringify({ documents: docs }), { status: 200 })
    })

    await expect(geocodeDestination('강남역', 'test-key', fetcher)).resolves.toEqual({
      query: '강남역',
      label: '강남역',
      lat: 37.49808633653005,
      lng: 127.02800140627488,
      address_name: '서울 강남구 역삼동 858',
    })
    expect(fetcher).toHaveBeenCalledTimes(2)
  })

  it('filters nearby parking lots and serializes the backend-compatible response', () => {
    const response = findParkingLots(sampleLots, {
      lat: 37.498086,
      lng: 127.028001,
      radius_m: 1000,
      arrival_time: '2026-04-28T14:20:00+09:00',
    })

    expect(response.count).toBe(1)
    expect(response.items[0]).toMatchObject({
      id: 'near',
      name: '가까운 공영주차장',
      available_spaces: 60,
      label: '보통',
    })
    expect(response.items[0].distance_m).toBeLessThan(100)
  })
})
