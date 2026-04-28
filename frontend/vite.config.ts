import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

import { localApiProxy } from './apiProxyConfig'
import { sharedEnvDir } from './envConfig'

export default defineConfig({
  envDir: sharedEnvDir,
  plugins: [react()],
  server: {
    proxy: localApiProxy,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
  },
})
