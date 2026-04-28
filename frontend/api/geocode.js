const { ApiError, geocodeDestination } = require('./_core')

module.exports = async function handler(request, response) {
  if (request.method !== 'GET') {
    response.status(405).json({ detail: 'Method not allowed' })
    return
  }

  try {
    const query = Array.isArray(request.query.query) ? request.query.query[0] : request.query.query || ''
    const result = await geocodeDestination(query, process.env.KAKAO_REST_API_KEY || '')
    response.status(200).json(result)
  } catch (error) {
    if (error instanceof ApiError) {
      response.status(error.statusCode).json({ detail: error.message })
      return
    }
    response.status(500).json({ detail: 'Internal server error' })
  }
}
