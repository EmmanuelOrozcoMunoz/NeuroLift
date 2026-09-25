import { defineConfig, minimal2023Preset } from "@vite-pwa/assets-generator/config";

// Genera los PNG que el manifest y iOS necesitan a partir de los SVG de public/ (iOS ignora
// un apple-touch-icon en SVG y Android arma mejor la splash screen con PNG). Se corre a mano
// con `npm run pwa-assets` cuando cambie el ícono; los PNG resultantes se versionan.
export default defineConfig({
  headLinkOptions: { preset: "2023" },
  preset: {
    ...minimal2023Preset,
    // El fondo del SVG ya es el color de la app: sin padding extra para "any" ni para iOS
    transparent: { ...minimal2023Preset.transparent, padding: 0 },
    maskable: { ...minimal2023Preset.maskable, padding: 0, resizeOptions: { background: "#121212" } },
    apple: { ...minimal2023Preset.apple, padding: 0, resizeOptions: { background: "#121212" } },
  },
  images: ["public/icon.svg"],
});
