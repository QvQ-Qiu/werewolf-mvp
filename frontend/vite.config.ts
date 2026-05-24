import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // process.env 优先：Docker 内 localhost 指向容器自身，需 host.docker.internal
  const apiTarget =
    process.env.VITE_DEV_API_TARGET ||
    env.VITE_DEV_API_TARGET ||
    'http://localhost:8000'
  const wsTarget =
    process.env.VITE_DEV_WS_TARGET ||
    env.VITE_DEV_WS_TARGET ||
    'ws://localhost:8000'

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
        '/ws': {
          target: wsTarget,
          ws: true,
        },
      },
    },
  }
})
