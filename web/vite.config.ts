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
      // "prompt" y no "autoUpdate": con autoUpdate el SW nuevo toma control y la app se recarga
      // sola, lo que puede pasar a media sesión (con el WodTimer corriendo o series sin guardar).
      // Con "prompt" el usuario decide cuándo — ver components/UpdatePrompt.tsx.
      registerType: "prompt",
      includeAssets: ["favicon.svg", "favicon.ico", "apple-touch-icon-180x180.png"],
      manifest: {
        id: "/",
        name: "NeuroLift",
        short_name: "NeuroLift",
        description: "Tus entrenamientos, tus marcas y tu progreso.",
        lang: "es",
        start_url: "/",
        scope: "/",
        display: "standalone",
        orientation: "portrait",
        background_color: "#121212",
        theme_color: "#121212",
        categories: ["health", "fitness", "sports"],
        // PNG generados con `npm run pwa-assets` (ver pwa-assets.config.ts)
        icons: [
          { src: "/pwa-64x64.png", sizes: "64x64", type: "image/png" },
          { src: "/pwa-192x192.png", sizes: "192x192", type: "image/png" },
          { src: "/pwa-512x512.png", sizes: "512x512", type: "image/png" },
          { src: "/maskable-icon-512x512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
        // Accesos directos al mantener presionado el ícono (Android). Son rutas de atleta: a
        // un coach/admin el RoleGate lo manda a su propio home.
        shortcuts: [
          { name: "Hoy", url: "/", icons: [{ src: "/pwa-192x192.png", sizes: "192x192", type: "image/png" }] },
          {
            name: "Mis entrenos",
            url: "/entrenos",
            icons: [{ src: "/pwa-192x192.png", sizes: "192x192", type: "image/png" }],
          },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,svg,png,ico,woff2}"],
        // De Inter solo se precachea el alfabeto latino (incluye ñ y tildes). Los demás
        // (cirílico, griego, vietnamita, latin-ext) los baja el navegador bajo demanda si algún
        // texto los necesita: precacharlos sumaba ~170 KB a cada instalación sin usarse nunca.
        globIgnores: ["**/inter-{cyrillic,cyrillic-ext,greek,greek-ext,vietnamese,latin-ext}-*.woff2"],
        // El shell se sirve desde caché para que la app abra sin red; los datos de la API
        // NUNCA se cachean aquí (van con token y cambian a cada rato) — de eso se encarga
        // TanStack Query en memoria.
        navigateFallback: "/index.html",
        runtimeCaching: [],
        // Borra los precachés de versiones viejas del SW en vez de dejarlos ocupando espacio
        cleanupOutdatedCaches: true,
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
