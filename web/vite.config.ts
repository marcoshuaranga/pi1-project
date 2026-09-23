import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// VITE_PROXY_TARGET lets the dev server reach the API by container name
// (e.g. http://api:8000) when running inside docker compose.
const proxyTarget = process.env.VITE_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": {
        target: proxyTarget,
        changeOrigin: true,
        ws: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
