import { useEffect, useMemo, useRef, useState } from 'react'

export interface MapDestination {
  lat: number
  lng: number
  label: string
}

export interface MapParkingLot {
  id: string
  name: string
  lat: number
  lng: number
  label: string
}

interface KakaoParkingMapProps {
  destination: MapDestination
  parkingLots: MapParkingLot[]
  javascriptKey?: string
}

declare global {
  interface Window {
    kakao?: KakaoMapsWindow
  }
}

interface KakaoMapsWindow {
  maps: {
    load: (callback: () => void) => void
    LatLng: new (lat: number, lng: number) => unknown
    Map: new (container: HTMLElement, options: { center: unknown; level: number }) => unknown
    Marker: new (options: { position: unknown; map: unknown; title?: string }) => unknown
  }
}

const KAKAO_SDK_ID = 'kakao-maps-sdk'

export function KakaoParkingMap({ destination, parkingLots, javascriptKey = '' }: KakaoParkingMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [loadState, setLoadState] = useState<'preview' | 'loading' | 'ready' | 'error'>(() =>
    javascriptKey.trim() ? 'loading' : 'preview',
  )

  const safeLots = useMemo(
    () => parkingLots.filter((parkingLot) => Number.isFinite(parkingLot.lat) && Number.isFinite(parkingLot.lng)),
    [parkingLots],
  )

  useEffect(() => {
    if (!javascriptKey.trim()) {
      setLoadState('preview')
      return
    }

    let cancelled = false
    setLoadState('loading')

    loadKakaoMapsSdk(javascriptKey)
      .then((kakao) => {
        if (cancelled || !containerRef.current) {
          return
        }
        kakao.maps.load(() => {
          if (cancelled || !containerRef.current) {
            return
          }
          const center = new kakao.maps.LatLng(destination.lat, destination.lng)
          const map = new kakao.maps.Map(containerRef.current, { center, level: 4 })
          new kakao.maps.Marker({ position: center, map, title: destination.label })
          safeLots.forEach((parkingLot) => {
            new kakao.maps.Marker({
              position: new kakao.maps.LatLng(parkingLot.lat, parkingLot.lng),
              map,
              title: parkingLot.name,
            })
          })
          setLoadState('ready')
        })
      })
      .catch(() => {
        if (!cancelled) {
          setLoadState('error')
        }
      })

    return () => {
      cancelled = true
    }
  }, [destination, javascriptKey, safeLots])

  if (!javascriptKey.trim()) {
    return <MapPreview destination={destination} parkingLots={safeLots} reason="Kakao JavaScript 키가 없어 지도 미리보기로 표시합니다." />
  }

  return (
    <section className="kakao-map" aria-label="Kakao 지도">
      <div ref={containerRef} className="kakao-map__canvas" />
      <div className="kakao-map__overlay" aria-live="polite">
        {loadState === 'loading' && <p>Kakao 지도를 불러오는 중입니다.</p>}
        {loadState === 'ready' && <p>목적지: {destination.label}</p>}
        {loadState === 'error' && <p>Kakao 지도를 불러오지 못해 목록 기준으로 표시합니다.</p>}
      </div>
      <ol className="kakao-map__markers" aria-label="지도 마커 목록">
        {safeLots.map((parkingLot, index) => (
          <li key={parkingLot.id}>
            마커 {index + 1}. {parkingLot.name}
          </li>
        ))}
      </ol>
    </section>
  )
}

function MapPreview({ destination, parkingLots, reason }: { destination: MapDestination; parkingLots: MapParkingLot[]; reason: string }) {
  return (
    <section className="map-preview" aria-label="지도 미리보기">
      <div className="map-preview__canvas">
        <span className="map-preview__destination">목적지: {destination.label}</span>
        {parkingLots.map((parkingLot, index) => (
          <span key={parkingLot.id} className="map-preview__pin">
            핀 {index + 1}. {parkingLot.name}
          </span>
        ))}
      </div>
      <p className="map-preview__hint">{reason}</p>
    </section>
  )
}

function loadKakaoMapsSdk(javascriptKey: string): Promise<KakaoMapsWindow> {
  if (window.kakao?.maps) {
    return Promise.resolve(window.kakao)
  }

  return new Promise((resolve, reject) => {
    const existingScript = document.getElementById(KAKAO_SDK_ID) as HTMLScriptElement | null
    if (existingScript) {
      existingScript.addEventListener('load', () => (window.kakao?.maps ? resolve(window.kakao) : reject(new Error('Kakao SDK unavailable'))), {
        once: true,
      })
      existingScript.addEventListener('error', () => reject(new Error('Kakao SDK failed to load')), { once: true })
      return
    }

    const script = document.createElement('script')
    script.id = KAKAO_SDK_ID
    script.async = true
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${encodeURIComponent(javascriptKey)}&autoload=false`
    script.addEventListener('load', () => (window.kakao?.maps ? resolve(window.kakao) : reject(new Error('Kakao SDK unavailable'))), {
      once: true,
    })
    script.addEventListener('error', () => reject(new Error('Kakao SDK failed to load')), { once: true })
    document.head.appendChild(script)
  })
}
