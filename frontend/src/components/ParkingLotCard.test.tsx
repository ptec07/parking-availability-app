import { render, screen } from '@testing-library/react'

import { ParkingLotCard, type ParkingLotCardProps } from './ParkingLotCard'

const baseLot: ParkingLotCardProps['parkingLot'] = {
  id: '171721',
  name: '세종로 공영주차장(시)',
  address: '종로구 세종로 80-1',
  availableSpaces: 803,
  totalSpaces: 1260,
  occupiedSpaces: 457,
  updatedAt: '2026-04-28T08:31:23+09:00',
  distanceM: 240,
  score: 86,
  label: '가능성 높음',
  reason: '잔여면수 803면, 데이터 갱신 3분 전',
}

describe('ParkingLotCard', () => {
  it('renders a high availability card with a green status badge', () => {
    render(<ParkingLotCard parkingLot={baseLot} />)

    expect(screen.getByRole('article', { name: '세종로 공영주차장(시)' })).toBeInTheDocument()
    expect(screen.getByText('가능성 높음')).toHaveClass('status-high')
    expect(screen.getByText('86점')).toBeInTheDocument()
    expect(screen.getByText('잔여 803면 / 전체 1,260면')).toBeInTheDocument()
  })

  it('renders updated time, distance, and reason', () => {
    render(<ParkingLotCard parkingLot={baseLot} />)

    expect(screen.getByText('240m')).toBeInTheDocument()
    expect(screen.getByText('갱신 2026. 04. 28. 08:31')).toBeInTheDocument()
    expect(screen.getByText('잔여면수 803면, 데이터 갱신 3분 전')).toBeInTheDocument()
  })

  it('renders a gray fallback state when availability data is missing', () => {
    render(
      <ParkingLotCard
        parkingLot={{
          ...baseLot,
          availableSpaces: null,
          totalSpaces: null,
          occupiedSpaces: null,
          updatedAt: null,
          score: null,
          label: '확인 필요',
          reason: '전체 주차면수 데이터가 없어 전화 확인이 필요합니다.',
        }}
      />,
    )

    expect(screen.getByText('확인 필요')).toHaveClass('status-unknown')
    expect(screen.getByText('잔여 정보 없음')).toBeInTheDocument()
    expect(screen.getByText('점수 없음')).toBeInTheDocument()
    expect(screen.getByText('갱신 시각 없음')).toBeInTheDocument()
  })
})
