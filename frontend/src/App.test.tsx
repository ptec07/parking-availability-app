import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, vi } from 'vitest'

import App from './App'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('주차될까 앱 스캐폴드', () => {
  it('renders the product title and primary parking search CTA', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: '주차될까' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '목적지 주변 주차장 찾기' })).toBeInTheDocument()
    expect(screen.getByText('서울 공영주차장 실시간 데이터 기반')).toBeInTheDocument()
  })

  it('searches a typed destination and opens nearby parking results', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          query: '강남역',
          label: '강남역',
          lat: 37.497952,
          lng: 127.027619,
          address_name: '서울 강남구 강남대로 지하 396',
        }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ items: [], count: 0 }),
      } as Response)
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    render(<App />)
    await user.type(screen.getByLabelText('목적지'), '강남역')
    await user.click(screen.getByRole('button', { name: '목적지 주변 주차장 찾기' }))

    expect(await screen.findByRole('heading', { name: '강남역 주변 주차장' })).toBeInTheDocument()
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/geocode?query=%EA%B0%95%EB%82%A8%EC%97%AD')
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/parking-lots?lat=37.497952&lng=127.027619&radius_m=3000')
  })

  it('shows a message when the typed destination cannot be geocoded', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Destination not found' }),
      } as Response),
    )
    const user = userEvent.setup()

    render(<App />)
    await user.type(screen.getByLabelText('목적지'), '없는장소')
    await user.click(screen.getByRole('button', { name: '목적지 주변 주차장 찾기' }))

    expect(await screen.findByText('목적지를 찾지 못했습니다. 다른 장소명을 입력해 주세요.')).toBeInTheDocument()
  })
})
