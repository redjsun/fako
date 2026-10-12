import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// O config roda no Node; declarado aqui para não depender de @types/node só por isso.
declare const process: { env: Record<string, string | undefined> };

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": {
        // No compose, API_URL=http://api:8000; fora do Docker, a API no host.
        target: process.env.API_URL ?? "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
