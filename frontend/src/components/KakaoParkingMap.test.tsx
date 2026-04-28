import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { KakaoParkingMap, type MapParkingLot } from './KakaoParkingMap'

const destination = { lat: 37.5665, lng: 126.978, label: '서울시청' }
const parkingLots: MapParkingLot[] = [
  { id: 'far-high', name: '가능성 높은 주차장', lat: 37.571, lng: 126.976, label: '가능성 높음' },
  { id: 'near-low', name: '가까운 주차장', lat: 37.565, lng: 126.979, label: '가능성 낮음' },
]

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('KakaoParkingMap', () => {
  it('creates a Kakao map with destination and parking lot markers when the SDK is available', async () => {
    const mapConstructor = vi.fn(function KakaoMap() {})
    const markerConstructor = vi.fn(function KakaoMarker() {})
    const latLngConstructor = vi.fn(function KakaoLatLng(this: { lat: number; lng: number }, lat: number, lng: number) {
      this.lat = lat
      this.lng = lng
    })
    const load = vi.fn((callback: () => void) => callback())

    vi.stubGlobal('kakao', {
      maps: {
        load,
        LatLng: latLngConstructor,
        Map: mapConstructor,
        Marker: markerConstructor,
      },
    })

    render(<KakaoParkingMap destination={destination} parkingLots={parkingLots} javascriptKey="test-js-key" />)

    expect(screen.getByRole('region', { name: 'Kakao 지도' })).toBeInTheDocument()

    await waitFor(() => {
      expect(load).toHaveBeenCalled()
      expect(mapConstructor).toHaveBeenCalledTimes(1)
      expect(markerConstructor).toHaveBeenCalledTimes(3)
    })

    expect(latLngConstructor).toHaveBeenCalledWith(37.5665, 126.978)
    expect(latLngConstructor).toHaveBeenCalledWith(37.571, 126.976)
    expect(latLngConstructor).toHaveBeenCalledWith(37.565, 126.979)
    expect(screen.getByText('목적지: 서울시청')).toBeInTheDocument()
    expect(screen.getByText('마커 1. 가능성 높은 주차장')).toBeInTheDocument()
    expect(screen.getByText('마커 2. 가까운 주차장')).toBeInTheDocument()
  })

  it('shows a safe fallback when the Kakao JavaScript key is missing', () => {
    render(<KakaoParkingMap destination={destination} parkingLots={parkingLots} javascriptKey="" />)

    expect(screen.getByRole('region', { name: '지도 미리보기' })).toBeInTheDocument()
    expect(screen.getByText('Kakao JavaScript 키가 없어 지도 미리보기로 표시합니다.')).toBeInTheDocument()
    expect(screen.getByText('핀 1. 가능성 높은 주차장')).toBeInTheDocument()
  })
})
