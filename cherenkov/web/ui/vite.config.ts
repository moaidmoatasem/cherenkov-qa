import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig} from 'vite';

export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modify—file watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
      // Disable file watching when DISABLE_HMR is true to save CPU during agent edits.
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
      proxy: {
        '/api/v1': {
          target: 'http://127.0.0.1:8001',
          changeOrigin: true,
        },
        // EnterpriseWorkspace's three panels (SlaDashboard, CompliancePanel,
        // SupportPortal) call the backend's `/api/enterprise/*` router, which
        // is deliberately registered outside the `/api/v1` prefix (see
        // cherenkov/web/routes/enterprise_routes.py). Without this entry those
        // requests fall through to this dev/preview server itself, which has
        // no matching route and serves the SPA's index.html back with a 200 --
        // the fetch then throws "Unexpected token '<' ... is not valid JSON"
        // straight onto the Enterprise Command Center screen.
        '/api/enterprise': {
          target: 'http://127.0.0.1:8001',
          changeOrigin: true,
        },
        '/ws/live': {
          target: 'ws://127.0.0.1:8001',
          ws: true,
        }
      }
    },
  };
});
