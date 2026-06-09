import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 개발 서버는 3000 포트 (FastAPI CORS allow_origins 와 일치).
// /api·/auth·/health·/ws 는 백엔드(8000)로 프록시 → 동일 출처처럼 사용.
const API_TARGET = process.env.VITE_API_TARGET || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api": { target: API_TARGET, changeOrigin: true },
      "/auth": { target: API_TARGET, changeOrigin: true },
      "/health": { target: API_TARGET, changeOrigin: true },
      "/ws": { target: API_TARGET, ws: true, changeOrigin: true },
    },
  },
  test: {
    environment: "node",
  },
});
