import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // schema/ leží mimo frontend/ (sdílená smlouva) – povolit čtení
    fs: { allow: [".."] },
    // Řez 3: API backendu (uvicorn na 8000) pod /api
    proxy: { "/api": "http://localhost:8000" },
  },
});
