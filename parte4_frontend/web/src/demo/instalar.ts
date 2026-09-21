/**
 * Modo demostración: sustituye `fetch` para que las peticiones a `/api` las conteste `BffDemo` con la instantánea
 * grabada en vez de un BFF. El resto de peticiones (los propios ficheros de la instantánea, fuentes…) salen
 * normalmente. Se importa antes que la aplicación (`entrada.ts`), que así no sabe que no hay servidor.
 */
import { Instantanea } from './datos'
import { BffDemo, type Contestacion, type EventoSse } from './rutas'

const RETARDO_MS = 150                  // lo que tarda de media el BFF real en contestar a una consulta
const RETARDO_PASO_MS = 700             // entre eventos del asistente, para que se vean los pasos en directo

const fetchOriginal = window.fetch.bind(window)
const base = new URL(`${import.meta.env.BASE_URL}demo/`, window.location.href)

const datos = new Instantanea(async (ruta) => {
  const respuesta = await fetchOriginal(new URL(ruta, base))
  if (!respuesta.ok) throw new Error(`No se ha podido cargar la instantánea (${ruta}: HTTP ${respuesta.status})`)
  return respuesta.json()
})
const bff = new BffDemo(datos)

function esperar(ms: number, señal?: AbortSignal | null): Promise<void> {
  return new Promise((resolver, rechazar) => {
    if (señal?.aborted) return rechazar(new DOMException('Petición cancelada', 'AbortError'))
    const temporizador = setTimeout(resolver, ms)
    señal?.addEventListener('abort', () => {
      clearTimeout(temporizador)
      rechazar(new DOMException('Petición cancelada', 'AbortError'))
    }, { once: true })
  })
}

/** El flujo `text/event-stream` del asistente, con un retardo entre eventos. */
function flujo(eventos: EventoSse[], señal?: AbortSignal | null): ReadableStream<Uint8Array> {
  const codificador = new TextEncoder()
  return new ReadableStream({
    async start(control) {
      try {
        for (const { evento, datos: cuerpo } of eventos) {
          await esperar(RETARDO_PASO_MS, señal)
          control.enqueue(codificador.encode(`event: ${evento}\ndata: ${JSON.stringify(cuerpo)}\n\n`))
        }
        control.close()
      } catch (error) {
        control.error(error)
      }
    },
  })
}

function respuesta(contestacion: Contestacion, señal?: AbortSignal | null): Response {
  if (contestacion.tipo === 'sse') {
    return new Response(flujo(contestacion.eventos, señal), { headers: { 'Content-Type': 'text/event-stream' } })
  }
  if (contestacion.estado === 204) return new Response(null, { status: 204 })
  return new Response(JSON.stringify(contestacion.cuerpo), {
    status: contestacion.estado,
    headers: { 'Content-Type': 'application/json' },
  })
}

async function cuerpoDe(entrada: RequestInfo | URL, init?: RequestInit): Promise<unknown> {
  const texto = init?.body !== undefined ? init.body : entrada instanceof Request ? await entrada.clone().text() : null
  if (typeof texto !== 'string' || !texto) return null
  try {
    return JSON.parse(texto)
  } catch {
    return texto
  }
}

window.fetch = async (entrada: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
  const url = new URL(entrada instanceof Request ? entrada.url : String(entrada), window.location.href)
  if (url.origin !== window.location.origin || !url.pathname.startsWith('/api/')) return fetchOriginal(entrada, init)
  const señal = init?.signal ?? (entrada instanceof Request ? entrada.signal : null)
  await esperar(RETARDO_MS, señal)
  try {
    const contestacion = await bff.atender({
      metodo: (init?.method ?? (entrada instanceof Request ? entrada.method : 'GET')).toUpperCase(),
      ruta: url.pathname.replace(/\/+$/, ''),
      parametros: url.searchParams,
      cuerpo: await cuerpoDe(entrada, init),
    })
    return respuesta(contestacion, señal)
  } catch (error) {
    console.error('Modo demostración:', error)
    return respuesta({ tipo: 'json', estado: 503, cuerpo: { detail: 'La demostración no ha podido cargar sus datos' } })
  }
}
