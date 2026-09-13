import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'GRADIENT_');
  return {
    plugins: [react()],
    server: {
      port: 5173, strictPort: true,
      proxy: {
        '/api': {
          target: env.GRADIENT_BACKEND_URL || 'http://127.0.0.1:8787',
          ws: true,
          // Preserve browser Host/Origin so FastAPI can enforce same-origin access.
          changeOrigin: false,
          rewrite: (path) => path.replace(/^\/api/, ''),
          headers: env.GRADIENT_API_TOKEN ? { Authorization: `Bearer ${env.GRADIENT_API_TOKEN}` } : {},
        },
      },
    },
  };
});
