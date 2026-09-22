/**
 * En vivo o demostración. La web pública (Vercel) reenvía `/api` al portal del equipo por un túnel de ngrok
 * (`vercel.json`, `make tunel`): si responde, se usa la plataforma de verdad, con su contraseña; si no (el portátil
 * está apagado o el túnel parado), la instantánea grabada. Quien no tenga la contraseña elige la demostración desde el
 * aviso, y la elección se recuerda en esta pestaña.
 */
export type Modo = 'vivo' | 'demo'

const CLAVE = 'pids-modo'
const ESPERA_MS = 3500
/** ngrok gratuito enseña una página de aviso a los navegadores; con esta cabecera la salta. */
export const CABECERA_TUNEL = 'ngrok-skip-browser-warning'

function preferido(): Modo | null {
  try {
    const valor = sessionStorage.getItem(CLAVE)
    return valor === 'vivo' || valor === 'demo' ? valor : null
  } catch {
    return null
  }
}

/** ¿Contesta el portal en vivo? `/api/salud` con JSON `{estado: 'ok'}`; sin túnel, Vercel devuelve la página (HTML). */
export async function vivoDisponible(consultar: typeof fetch = fetch, espera = ESPERA_MS): Promise<boolean> {
  const control = new AbortController()
  const temporizador = setTimeout(() => control.abort(), espera)
  try {
    const respuesta = await consultar('/api/salud', { headers: { [CABECERA_TUNEL]: '1' }, signal: control.signal, cache: 'no-store' })
    if (!respuesta.ok || !(respuesta.headers.get('content-type') ?? '').includes('application/json')) return false
    const cuerpo = (await respuesta.json()) as { estado?: unknown }
    return cuerpo.estado === 'ok'
  } catch {
    return false
  } finally {
    clearTimeout(temporizador)
  }
}

export async function decidirModo(consultar: typeof fetch = fetch): Promise<Modo> {
  if (preferido() === 'demo') return 'demo'
  return (await vivoDisponible(consultar)) ? 'vivo' : 'demo'
}

/** Cambia de modo y recarga (la aplicación arranca de nuevo con el otro `/api`). */
export function elegirModo(modo: Modo): void {
  try {
    sessionStorage.setItem(CLAVE, modo)
  } catch {
    // sin almacenamiento, la recarga vuelve a decidir sola
  }
  window.location.assign('/')
}
