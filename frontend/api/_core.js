class ApiError extends Error {
  constructor(statusCode, message) {
    super(message)
    this.statusCode = statusCode
  }
}

function normalizeQuery(query) {
  return String(query || '').split(/\s+/).filter(Boolean).join(' ')
}

async function geocodeDestination(query, apiKey, fetcher = fetch) {
  const normalizedQuery = normalizeQuery(query)
  if (!normalizedQuery) throw new ApiError(422, 'Query is required')
  if (!String(apiKey || '').trim()) throw new ApiError(503, 'Kakao REST API key is not configured')

  const document =
    (await requestKakaoGeocode('/v2/local/search/address.json', normalizedQuery, apiKey, fetcher)) ||
    (await requestKakaoGeocode('/v2/local/search/keyword.json', normalizedQuery, apiKey, fetcher))

  if (!document) throw new ApiError(404, 'Destination not found')

  return {
    query: normalizedQuery,
    label: normalizedQuery,
    lat: Number(document.y),
    lng: Number(document.x),
    address_name: document.address_name || document.place_name || normalizedQuery,
  }
}

function findParkingLots(lots, params) {
  const lat = Number(params.lat)
  const lng = Number(params.lng)
  const radiusM = params.radius_m === undefined ? 500 : Number(params.radius_m)
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) throw new ApiError(422, 'lat and lng are required')
  if (!Number.isFinite(radiusM) || radiusM <= 0 || radiusM > 5000) {
    throw new ApiError(422, 'radius_m must be between 1 and 5000')
  }

  const arrivalTime = params.arrival_time ? new Date(params.arrival_time) : new Date()
  const items = lots
    .filter((lot) => lot.lat !== null && lot.lng !== null)
    .map((lot) => ({ lot, distance_m: Math.round(haversineM(lat, lng, lot.lat, lot.lng)) }))
    .filter(({ distance_m }) => distance_m <= radiusM)
    .map(({ lot, distance_m }) => serializeParkingLot(lot, distance_m, arrivalTime))
    .sort((a, b) => a.distance_m - b.distance_m || a.name.localeCompare(b.name))

  return { items, count: items.length }
}

async function requestKakaoGeocode(path, query, apiKey, fetcher) {
  const url = new URL(`https://dapi.kakao.com${path}`)
  url.searchParams.set('query', query)
  const response = await fetcher(url.toString(), { headers: { Authorization: `KakaoAK ${apiKey}` } })
  if (!response.ok) throw new ApiError(response.status, 'Kakao geocoding request failed')
  const payload = await response.json()
  return (payload.documents || [])[0] || null
}

function serializeParkingLot(lot, distanceM, arrivalTime) {
  const totalSpaces = lot.total_spaces
  const occupiedSpaces = lot.occupied_spaces
  let availableSpaces = null
  let score = null
  let label = '확인 필요'
  let reason = '주차면수 데이터가 부족합니다.'

  if (totalSpaces !== null && occupiedSpaces !== null && lot.updated_at) {
    availableSpaces = Math.max(totalSpaces - occupiedSpaces, 0)
    const parkingScore = scoreParkingLot(totalSpaces, occupiedSpaces, new Date(lot.updated_at), arrivalTime, distanceM)
    score = parkingScore.score
    label = parkingScore.label
    reason = parkingScore.reason
  }

  return {
    id: lot.id,
    name: lot.name,
    address: lot.address,
    lat: lot.lat,
    lng: lot.lng,
    distance_m: distanceM,
    total_spaces: totalSpaces,
    occupied_spaces: occupiedSpaces,
    available_spaces: availableSpaces,
    updated_at: lot.updated_at,
    score,
    label,
    reason,
  }
}

function scoreParkingLot(totalSpaces, occupiedSpaces, updatedAt, arrivalTime, distanceM) {
  if (totalSpaces <= 0) return { score: 0, label: '확인 필요', reason: '전체 주차면수 데이터가 부족합니다.' }
  const availableSpaces = Math.max(totalSpaces - occupiedSpaces, 0)
  const availabilityScore = Math.min(availableSpaces / totalSpaces, 1) * 60
  const freshnessScore = getFreshnessScore(updatedAt, arrivalTime)
  const distanceScore = getDistanceScore(distanceM)
  const timeScore = getTimeScore(arrivalTime)
  const score = Math.round(Math.max(0, Math.min(100, availabilityScore + freshnessScore + distanceScore + timeScore)))
  return { score, label: getLabel(score), reason: getReason(availableSpaces, totalSpaces, freshnessScore, distanceScore) }
}

function getFreshnessScore(updatedAt, arrivalTime) {
  const ageMinutes = Math.abs(arrivalTime.getTime() - updatedAt.getTime()) / 60000
  if (ageMinutes <= 20) return 15
  if (ageMinutes <= 40) return 10
  if (ageMinutes <= 60) return 6
  if (ageMinutes <= 120) return 2
  return 0
}

function getDistanceScore(distanceM) {
  if (distanceM <= 300) return 10
  if (distanceM <= 500) return 8
  if (distanceM <= 800) return 5
  if (distanceM <= 1000) return 3
  return 0
}

function getTimeScore(arrivalTime) {
  const hour = arrivalTime.getHours()
  if ((hour >= 7 && hour <= 9) || (hour >= 18 && hour <= 20)) return 8
  if ((hour >= 11 && hour <= 14) || (hour >= 16 && hour <= 17)) return 10
  return 15
}

function getLabel(score) {
  if (score >= 75) return '가능성 높음'
  if (score >= 50) return '보통'
  if (score >= 25) return '가능성 낮음'
  return '어려움'
}

function getReason(availableSpaces, totalSpaces, freshnessScore, distanceScore) {
  const parts = [`잔여면수 약 ${Math.trunc(availableSpaces)} / 전체 ${Math.trunc(totalSpaces)}면`]
  if (freshnessScore >= 10) parts.push('데이터가 최신입니다')
  else if (freshnessScore <= 2) parts.push('데이터가 오래되어 신뢰도가 낮습니다')
  if (distanceScore >= 8) parts.push('목적지와 가깝습니다')
  else if (distanceScore <= 3) parts.push('목적지와 거리가 있습니다')
  return `${parts.join(', ')}.`
}

function haversineM(lat1, lng1, lat2, lng2) {
  const radiusM = 6371000
  const phi1 = toRadians(lat1)
  const phi2 = toRadians(lat2)
  const deltaPhi = toRadians(lat2 - lat1)
  const deltaLambda = toRadians(lng2 - lng1)
  const a = Math.sin(deltaPhi / 2) ** 2 + Math.cos(phi1) * Math.cos(phi2) * Math.sin(deltaLambda / 2) ** 2
  return radiusM * (2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)))
}

function toRadians(degrees) {
  return (degrees * Math.PI) / 180
}

module.exports = { ApiError, normalizeQuery, geocodeDestination, findParkingLots }
