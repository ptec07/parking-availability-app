import { FormEvent, useState } from 'react'

import { buildApiUrl } from './api'
import { SearchResultsPage } from './pages/SearchResultsPage'
import './styles.css'

interface Destination {
  lat: number
  lng: number
  label: string
}

interface GeocodeResponse {
  query: string
  label: string
  lat: number
  lng: number
  address_name: string
}

function App() {
  const [query, setQuery] = useState('')
  const [destination, setDestination] = useState<Destination | null>(null)
  const [status, setStatus] = useState<'idle' | 'loading' | 'error'>('idle')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const normalizedQuery = query.trim()
    if (!normalizedQuery) {
      setStatus('error')
      return
    }

    setStatus('loading')
    try {
      const response = await fetch(buildApiUrl('/geocode', { query: normalizedQuery }))
      if (!response.ok) {
        throw new Error(`Geocode failed with status ${response.status}`)
      }
      const payload = (await response.json()) as GeocodeResponse
      setDestination({ lat: payload.lat, lng: payload.lng, label: payload.label || normalizedQuery })
      setStatus('idle')
    } catch {
      setDestination(null)
      setStatus('error')
    }
  }

  if (destination) {
    return (
      <main className="app-shell app-shell--results">
        <SearchResultsPage destination={destination} radiusM={3000} />
      </main>
    )
  }

  return (
    <main className="app-shell">
      <section className="hero" aria-labelledby="product-title">
        <p className="eyebrow">서울 공영주차장 실시간 데이터 기반</p>
        <h1 id="product-title">주차될까</h1>
        <p className="hero-copy">
          목적지 주변 공영주차장의 실시간 주차대수와 갱신 시각을 바탕으로 주차 가능성을 빠르게 확인합니다.
        </p>
        <form className="destination-search" onSubmit={handleSubmit}>
          <label htmlFor="destination-query">목적지</label>
          <div className="destination-search__controls">
            <input
              id="destination-query"
              type="search"
              value={query}
              placeholder="예: 강남역, 여의도 IFC, 홍대입구"
              onChange={(event) => setQuery(event.target.value)}
            />
            <button type="submit" className="primary-button" disabled={status === 'loading'}>
              {status === 'loading' ? '찾는 중...' : '목적지 주변 주차장 찾기'}
            </button>
          </div>
        </form>
        {status === 'error' && <p className="state-message">목적지를 찾지 못했습니다. 다른 장소명을 입력해 주세요.</p>}
      </section>
    </main>
  )
}

export default App
