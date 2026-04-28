const parkingLots = require('./parking_lots.json')
const { ApiError, findParkingLots } = require('./_core')

module.exports = function handler(request, response) {
  if (request.method !== 'GET') {
    response.status(405).json({ detail: 'Method not allowed' })
    return
  }

  try {
    const lat = Number(first(request.query.lat))
    const lng = Number(first(request.query.lng))
    const radiusValue = first(request.query.radius_m)
    const radius_m = radiusValue ? Number(radiusValue) : undefined
    const arrival_time = first(request.query.arrival_time)
    const result = findParkingLots(parkingLots, { lat, lng, radius_m, arrival_time })
    response.status(200).json(result)
  } catch (error) {
    if (error instanceof ApiError) {
      response.status(error.statusCode).json({ detail: error.message })
      return
    }
    response.status(500).json({ detail: 'Internal server error' })
  }
}

function first(value) {
  return Array.isArray(value) ? value[0] || '' : value || ''
}
