export type ParkingLotAvailabilityLabel = '가능성 높음' | '보통' | '가능성 낮음' | '어려움' | '확인 필요'

export interface ParkingLotCardProps {
  parkingLot: {
    id: string
    name: string
    address: string
    availableSpaces: number | null
    totalSpaces: number | null
    occupiedSpaces: number | null
    updatedAt: string | null
    distanceM: number
    score: number | null
    label: ParkingLotAvailabilityLabel
    reason: string
  }
}

export function ParkingLotCard({ parkingLot }: ParkingLotCardProps) {
  const statusClassName = `parking-status ${statusClassForLabel(parkingLot.label)}`

  return (
    <article className="parking-card" aria-label={parkingLot.name}>
      <div className="parking-card__header">
        <div>
          <h2>{parkingLot.name}</h2>
          <p className="parking-card__address">{parkingLot.address}</p>
        </div>
        <span className={statusClassName}>{parkingLot.label}</span>
      </div>

      <dl className="parking-card__metrics">
        <div>
          <dt>점수</dt>
          <dd>{parkingLot.score === null ? '점수 없음' : `${parkingLot.score}점`}</dd>
        </div>
        <div>
          <dt>거리</dt>
          <dd>{formatDistance(parkingLot.distanceM)}</dd>
        </div>
        <div>
          <dt>잔여면수</dt>
          <dd>{formatSpaces(parkingLot.availableSpaces, parkingLot.totalSpaces)}</dd>
        </div>
      </dl>

      <p className="parking-card__updated">{formatUpdatedAt(parkingLot.updatedAt)}</p>
      <p className="parking-card__reason">{parkingLot.reason}</p>
    </article>
  )
}

function statusClassForLabel(label: ParkingLotAvailabilityLabel): string {
  switch (label) {
    case '가능성 높음':
      return 'status-high'
    case '보통':
      return 'status-medium'
    case '가능성 낮음':
      return 'status-low'
    case '어려움':
      return 'status-hard'
    case '확인 필요':
      return 'status-unknown'
  }
}

function formatSpaces(availableSpaces: number | null, totalSpaces: number | null): string {
  if (availableSpaces === null || totalSpaces === null) {
    return '잔여 정보 없음'
  }

  return `잔여 ${availableSpaces.toLocaleString('ko-KR')}면 / 전체 ${totalSpaces.toLocaleString('ko-KR')}면`
}

function formatDistance(distanceM: number): string {
  if (distanceM >= 1000) {
    return `${(distanceM / 1000).toFixed(1)}km`
  }

  return `${Math.round(distanceM).toLocaleString('ko-KR')}m`
}

function formatUpdatedAt(updatedAt: string | null): string {
  if (updatedAt === null) {
    return '갱신 시각 없음'
  }

  const date = new Date(updatedAt)
  if (Number.isNaN(date.getTime())) {
    return '갱신 시각 없음'
  }

  return `갱신 ${new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'Asia/Seoul',
  }).format(date)}`
}
