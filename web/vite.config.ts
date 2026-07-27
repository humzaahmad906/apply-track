import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Proxying /api keeps the browser on one origin, so no CORS in dev and the
// same relative URLs work in a production build.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
