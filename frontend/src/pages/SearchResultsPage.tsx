import { useEffect, useMemo, useState } from 'react'

import { buildApiUrl } from '../api'
import { KakaoParkingMap } from '../components/KakaoParkingMap'
import { ParkingLotCard, type ParkingLotAvailabilityLabel, type ParkingLotCardProps } from '../components/ParkingLotCard'

type ParkingLot = ParkingLotCardProps['parkingLot'] & {
  lat: number
  lng: number
}

type SortMode = 'score' | 'distance'

interface Destination {
  lat: number
  lng: number
  label: string
}

interface SearchResultsPageProps {
  destination: Destination
  radiusM?: number
  kakaoJavaScriptKey?: string
}

interface ParkingLotApiItem {
  id: string
  name: string
  address: string
  available_spaces: number | null
  total_spaces: number | null
  occupied_spaces: number | null
  updated_at: string | null
  lat: number
  lng: number
  distance_m: number
  score: number | null
  label: ParkingLotAvailabilityLabel
  reason: string
}

interface ParkingLotsApiResponse {
  items: ParkingLotApiItem[]
  count: number
}

export function SearchResultsPage({
  destination,
  radiusM = 500,
  kakaoJavaScriptKey = import.meta.env.VITE_KAKAO_JAVASCRIPT_KEY ?? '',
}: SearchResultsPageProps) {
  const [parkingLots, setParkingLots] = useState<ParkingLot[]>([])
  const [sortMode, setSortMode] = useState<SortMode>('score')
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')

  useEffect(() => {
    let ignore = false

    async function loadParkingLots() {
      setStatus('loading')
      try {
        const nextParkingLots = await fetchParkingLots(destination, radiusM)
        if (!ignore) {
          setParkingLots(nextParkingLots)
          setStatus('success')
        }
      } catch {
        if (!ignore) {
          setParkingLots([])
          setStatus('error')
        }
      }
    }

    void loadParkingLots()

    return () => {
      ignore = true
    }
  }, [destination, radiusM])

  const sortedParkingLots = useMemo(() => {
    const next = [...parkingLots]
    if (sortMode === 'distance') {
      return next.sort((a, b) => a.distanceM - b.distanceM)
    }

    return next.sort((a, b) => (b.score ?? -1) - (a.score ?? -1) || a.distanceM - b.distanceM)
  }, [parkingLots, sortMode])

  const mapParkingLots = useMemo(
    () =>
      sortedParkingLots
        .filter((parkingLot) => Number.isFinite(parkingLot.lat) && Number.isFinite(parkingLot.lng))
        .map((parkingLot) => ({
          id: parkingLot.id,
          name: parkingLot.name,
          lat: parkingLot.lat,
          lng: parkingLot.lng,
          label: parkingLot.label,
        })),
    [sortedParkingLots],
  )

  return (
    <section className="results-page" aria-labelledby="results-title">
      <div className="results-page__header">
        <p className="eyebrow">실시간 주차 가능성</p>
        <h1 id="results-title">{destination.label} 주변 주차장</h1>
        <p className="hero-copy">좌표가 확인된 서울 공영주차장을 지도 미리보기와 카드 목록으로 보여줍니다.</p>
      </div>

      <div className="results-layout">
        <KakaoParkingMap destination={destination} parkingLots={mapParkingLots} javascriptKey={kakaoJavaScriptKey} />

        <section className="results-list" aria-label="주차장 목록">
          <div className="results-list__toolbar">
            <span>{status === 'success' ? `${parkingLots.length}곳` : '조회 중'}</span>
            <div className="sort-buttons" aria-label="정렬 방식">
              <button type="button" className={sortMode === 'score' ? 'active' : ''} onClick={() => setSortMode('score')}>
                가능성 높은 순
              </button>
              <button
                type="button"
                className={sortMode === 'distance' ? 'active' : ''}
                onClick={() => setSortMode('distance')}
              >
                가까운 순
              </button>
            </div>
          </div>

          {status === 'loading' && <p className="state-message">주차장 정보를 불러오는 중입니다.</p>}
          {status === 'error' && <p className="state-message">주차장 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.</p>}
          {status === 'success' && sortedParkingLots.length === 0 && (
            <p className="state-message">반경 {radiusM.toLocaleString('ko-KR')}m 안에 좌표가 확인된 공영주차장이 없습니다.</p>
          )}
          {status === 'success' && sortedParkingLots.map((parkingLot) => <ParkingLotCard key={parkingLot.id} parkingLot={parkingLot} />)}
        </section>
      </div>
    </section>
  )
}

async function fetchParkingLots(destination: Destination, radiusM: number): Promise<ParkingLot[]> {
  const url = buildApiUrl('/parking-lots', {
    lat: destination.lat,
    lng: destination.lng,
    radius_m: radiusM,
  })
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`Parking lots request failed with status ${response.status}`)
  }

  const payload = (await response.json()) as ParkingLotsApiResponse
  return payload.items.map(toParkingLot)
}

function toParkingLot(item: ParkingLotApiItem): ParkingLot {
  return {
    id: item.id,
    name: item.name,
    address: item.address,
    availableSpaces: item.available_spaces,
    totalSpaces: item.total_spaces,
    occupiedSpaces: item.occupied_spaces,
    updatedAt: item.updated_at,
    lat: item.lat,
    lng: item.lng,
    distanceM: item.distance_m,
    score: item.score,
    label: item.label,
    reason: item.reason,
  }
}
