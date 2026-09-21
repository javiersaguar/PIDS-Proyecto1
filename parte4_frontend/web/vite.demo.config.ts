/**
 * Modo demostración: la misma SPA, sin BFF. Es lo que se publica en Vercel (`vercel.json` en la raíz).
 *
 *   npm run build -- --config vite.demo.config.ts     # → dist/, con la instantánea de public/demo
 *   npx vite preview --config vite.demo.config.ts     # http://127.0.0.1:4190
 *
 * Cambia el punto de entrada de `index.html` (`src/main.tsx` → `src/demo/entrada.ts`, que instala el sustituto del BFF
 * y luego carga `src/main.tsx` sin cambios) y usa el puerto 4190, que no choca con el portal (8020) ni con el
 * servidor de desarrollo (5173). El modo con datos reales sigue siendo `vite.config.ts` con el BFF.
 */
import { fileURLToPath, URL } from 'node:url'
import { mergeConfig, type Plugin } from 'vite'

import base from './vite.config.ts'

const PUERTO_DEMO = 4190

function entradaDemo(): Plugin {
  return {
    name: 'pids-entrada-demo',
    transformIndexHtml: {
      order: 'pre',
      handler: (html) => html.replace('/src/main.tsx', '/src/demo/entrada.ts'),
    },
  }
}

export default mergeConfig(base, {
  plugins: [entradaDemo()],
  server: {
    port: PUERTO_DEMO,
    strictPort: true,
    // src/demo/privacidad.ts importa las reglas de config/privacidad.json, fuera de la carpeta web
    fs: { allow: [fileURLToPath(new URL('.', import.meta.url)), fileURLToPath(new URL('../../config', import.meta.url))] },
  },
  preview: { port: PUERTO_DEMO, strictPort: true, host: '127.0.0.1' },
})
