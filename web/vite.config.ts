import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Proxying /api keeps the browser on one origin, so no CORS in dev and the
// same relative URLs work in a production build.
//
// APPLY_TRACK_API points this at a different port, which is what you want when
// a second copy is already running against your real data.
//
// Declared rather than pulling in @types/node for one lookup.
declare const process: { env: Record<string, string | undefined> };
const target = process.env.APPLY_TRACK_API ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target, changeOrigin: true },
    },
  },
});
