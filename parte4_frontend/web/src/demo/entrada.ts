/**
 * Punto de entrada de la web pública (`vite.demo.config.ts` lo pone en lugar de `src/main.tsx`). Decide el modo
 * (`modo.ts`): en vivo, si el portal del equipo contesta por el túnel; si no, la demostración con el sustituto del BFF.
 * Después, el aviso del modo y la aplicación de siempre, sin cambios.
 */
import { decidirModo } from './modo'

const modo = await decidirModo()
if (modo === 'vivo') await import('./vivo')
else await import('./instalar')
const { montarAviso } = await import('./aviso')
montarAviso(modo)
await import('@/main')
