/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // In development the browser talks to Vite, which forwards /api to FastAPI.
    // This keeps cookies same-origin (no CORS or third-party cookie problems).
    proxy: { "/api": { target: "http://localhost:8000", changeOrigin: false } },
  },
  test: { environment: "jsdom", globals: true, setupFiles: "./src/test-setup.ts", css: false },
});

