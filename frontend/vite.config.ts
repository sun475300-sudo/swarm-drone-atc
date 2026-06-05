import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// SDACS 프론트엔드 개발 서버.
// 백엔드 FastAPI는 기본 http://localhost:8000 (CORS가 5173 허용).
// VITE_API_BASE 로 백엔드 주소를 덮어쓸 수 있다.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  test: {
    globals: true,
    environment: "node",
  },
});
