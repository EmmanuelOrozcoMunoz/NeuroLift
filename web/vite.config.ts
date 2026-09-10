import { fileURLToPath, URL } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg"],
      manifest: {
        name: "NeuroLift",
        short_name: "NeuroLift",
        description: "Tus entrenamientos, tus marcas y tu progreso.",
        lang: "es",
        start_url: "/",
        scope: "/",
        display: "standalone",
        orientation: "portrait",
        background_color: "#0b0f14",
        theme_color: "#0b0f14",
        icons: [
          { src: "/icon.svg", sizes: "192x192 512x512", type: "image/svg+xml" },
          { src: "/icon-maskable.svg", sizes: "192x192 512x512", type: "image/svg+xml", purpose: "maskable" },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,svg,woff2}"],
        // El shell se sirve desde caché para que la app abra sin red; los datos de la API
        // NUNCA se cachean aquí (van con token y cambian a cada rato) — de eso se encarga
        // TanStack Query en memoria.
        navigateFallback: "/index.html",
        runtimeCaching: [],
      },
    }),
  ],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    // host: true -> expone el dev server en la red local para poder probar desde el celular
    host: true,
    // Vite rechaza por defecto peticiones con un Host header que no reconoce (protección
    // contra DNS rebinding). Necesario para servir detrás de un túnel (Cloudflare/ngrok),
    // cuyo dominio cambia cada vez que se reinicia. Solo aplica al servidor de DESARROLLO.
    allowedHosts: true,
  },
  build: {
    target: "es2022",
  },
});
