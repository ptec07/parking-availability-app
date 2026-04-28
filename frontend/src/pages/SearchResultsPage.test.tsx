import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { SearchResultsPage } from './SearchResultsPage'

const apiItems = [
  {
    id: 'near-low',
    name: '가까운 주차장',
    address: '서울 중구 세종대로 110',
    available_spaces: 5,
    total_spaces: 100,
    occupied_spaces: 95,
    updated_at: '2026-04-28T08:31:23+09:00',
    lat: 37.565,
    lng: 126.979,
    distance_m: 120,
    score: 42,
    label: '가능성 낮음',
    reason: '가깝지만 잔여면수가 적습니다.',
  },
  {
    id: 'far-high',
    name: '가능성 높은 주차장',
    address: '서울 종로구 세종로 80-1',
    available_spaces: 803,
    total_spaces: 1260,
    occupied_spaces: 457,
    updated_at: '2026-04-28T08:31:23+09:00',
    lat: 37.571,
    lng: 126.976,
    distance_m: 640,
    score: 86,
    label: '가능성 높음',
    reason: '잔여면수가 충분합니다.',
  },
]

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('SearchResultsPage', () => {
  it('fetches nearby parking lots and renders map preview plus cards sorted by score', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ items: apiItems, count: apiItems.length }),
    } as Response)
    vi.stubGlobal('fetch', fetchMock)

    render(<SearchResultsPage destination={{ lat: 37.5665, lng: 126.978, label: '서울시청' }} kakaoJavaScriptKey="" />)

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/api/parking-lots?lat=37.5665&lng=126.978&radius_m=500')
    })

    expect(await screen.findByRole('heading', { name: '서울시청 주변 주차장' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: '지도 미리보기' })).toBeInTheDocument()
    expect(screen.getByText('핀 1. 가능성 높은 주차장')).toBeInTheDocument()
    expect(screen.getByText('핀 2. 가까운 주차장')).toBeInTheDocument()

    const cards = screen.getAllByRole('article')
    expect(cards[0]).toHaveAccessibleName('가능성 높은 주차장')
    expect(cards[1]).toHaveAccessibleName('가까운 주차장')
  })

  it('allows sorting by distance', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ items: apiItems, count: apiItems.length }),
      } as Response),
    )
    const user = userEvent.setup()

    render(<SearchResultsPage destination={{ lat: 37.5665, lng: 126.978, label: '서울시청' }} kakaoJavaScriptKey="" />)
    await screen.findByText('가능성 높은 주차장')

    await user.click(screen.getByRole('button', { name: '가까운 순' }))

    const cards = screen.getAllByRole('article')
    expect(cards[0]).toHaveAccessibleName('가까운 주차장')
    expect(cards[1]).toHaveAccessibleName('가능성 높은 주차장')
  })

  it('renders an empty state when no lots are returned', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ items: [], count: 0 }),
      } as Response),
    )

    render(<SearchResultsPage destination={{ lat: 37.5665, lng: 126.978, label: '서울시청' }} kakaoJavaScriptKey="" />)

    expect(await screen.findByText('반경 500m 안에 좌표가 확인된 공영주차장이 없습니다.')).toBeInTheDocument()
  })

  it('renders an error state when the parking API fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        json: async () => ({}),
      } as Response),
    )

    render(<SearchResultsPage destination={{ lat: 37.5665, lng: 126.978, label: '서울시청' }} kakaoJavaScriptKey="" />)

    expect(await screen.findByText('주차장 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.')).toBeInTheDocument()
  })
})
