import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/*
 * A interface fala com a API **pela mesma origem**, e isso não é conveniência.
 *
 * O cookie de sessão é `HttpOnly` com `SameSite=Lax`, e a API não tem CORS
 * configurado. Servir a interface numa origem diferente exigiria abrir CORS no
 * backend e afrouxar o cookie para `SameSite=None; Secure` — ou seja, mexer na
 * postura de segurança do servidor para acomodar o cliente. Em HTTP local, nem
 * funcionaria.
 *
 * Com o proxy, o navegador vê um endereço só. Nada muda no backend.
 */
const API = process.env.GIH_API_URL || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // acessível de fora do contêiner
    port: 5173,
    proxy: {
      "/api": { target: API, changeOrigin: false },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/testes/preparar.js",
    globals: true,
  },
});
