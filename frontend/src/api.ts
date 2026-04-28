type QueryValue = string | number | boolean | null | undefined

type QueryParams = Record<string, QueryValue>

const DEFAULT_API_BASE_URL = '/api'

export function buildApiUrl(path: string, params: QueryParams = {}, baseUrl = import.meta.env.VITE_API_BASE_URL): string {
  const normalizedBaseUrl = normalizeApiBaseUrl(baseUrl || DEFAULT_API_BASE_URL)
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const url = `${normalizedBaseUrl}${normalizedPath}`
  const query = new URLSearchParams()

  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined) {
      query.set(key, String(value))
    }
  })

  const queryString = query.toString()
  return queryString ? `${url}?${queryString}` : url
}

function normalizeApiBaseUrl(baseUrl: string): string {
  const trimmed = baseUrl.trim().replace(/\/$/, '')
  if (!trimmed) {
    return DEFAULT_API_BASE_URL
  }
  return trimmed.endsWith('/api') ? trimmed : `${trimmed}/api`
}
