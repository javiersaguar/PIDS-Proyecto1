/**
 * Modo en vivo: las peticiones a `/api` salen de verdad (Vercel las reenvía al portal por el túnel) con la cabecera
 * que evita la página de aviso de ngrok. La sesión y la contraseña son las del portal de siempre.
 */
import { CABECERA_TUNEL } from './modo'

const fetchOriginal = window.fetch.bind(window)

window.fetch = (entrada: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
  const url = new URL(entrada instanceof Request ? entrada.url : String(entrada), window.location.href)
  if (url.origin !== window.location.origin || !url.pathname.startsWith('/api/')) return fetchOriginal(entrada, init)
  const cabeceras = new Headers(init?.headers ?? (entrada instanceof Request ? entrada.headers : undefined))
  cabeceras.set(CABECERA_TUNEL, '1')
  return fetchOriginal(entrada, { ...init, headers: cabeceras })
}
