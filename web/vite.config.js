import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/*
 * A interface fala com a API pela mesma origem: o cookie de sessão é HttpOnly com
 * SameSite=Lax e a API não abre CORS. Em desenvolvimento, o Vite repassa /api para
 * GIH_API_URL; em produção, quem serve o dist/ faz o mesmo papel.
 */
const API = process.env.GIH_API_URL || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: { "/api": { target: API, changeOrigin: false } },
  },
  preview: {
    proxy: { "/api": { target: API, changeOrigin: false } },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
