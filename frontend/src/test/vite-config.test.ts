import { localApiProxy } from '../../apiProxyConfig'
import { sharedEnvDir } from '../../envConfig'

describe('Vite local integration config', () => {
  it('proxies API requests to the local FastAPI backend in development', () => {
    expect(localApiProxy['/api']).toMatchObject({
      target: 'http://127.0.0.1:8000',
      changeOrigin: true,
    })
  })

  it('loads shared project-root env vars such as VITE_KAKAO_JAVASCRIPT_KEY', () => {
    expect(sharedEnvDir).toBe('..')
  })
})
