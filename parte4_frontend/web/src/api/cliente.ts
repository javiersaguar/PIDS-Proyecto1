/**
 * Cliente HTTP del BFF: `fetch` con la cookie de sesión, JSON y errores tipados.
 *
 *   const catalogo = await api<Catalogo>('/api/catalogo')
 *   await api<void>('/api/sesion', { method: 'POST', json: { clave } })
 *
 * Un 401 en cualquier ruta distinta de `/api/sesion` significa que la sesión ha caducado: se avisa a la guardia
 * de sesión (que navega a `/acceso`) o, si nadie escucha, se redirige con el navegador.
 */

export class ErrorApi extends Error {
  /** Código HTTP de la respuesta (0 si la petición no llegó a salir o no hubo respuesta). */
  readonly status: number
  /** El `detail` del cuerpo `{"detail": "…"}` o, si no venía, un texto genérico según el código. */
  readonly detail: string
  /** El cuerpo tal cual (JSON ya interpretado o texto), por si la página necesita más que el `detail`:
   *  por ejemplo, la `Decision` de un 403 de `POST /api/consultas`. */
  readonly cuerpo: unknown

  constructor(status: number, detail: string, cuerpo: unknown = null) {
    super(detail)
    this.name = 'ErrorApi'
    this.status = status
    this.detail = detail
    this.cuerpo = cuerpo
  }
}

export type OpcionesApi = Omit<RequestInit, 'body'> & {
  /** Cuerpo de la petición; si no es una cadena se serializa como JSON. */
  body?: BodyInit | null
  /** Atajo: objeto que se envía como JSON (`Content-Type: application/json`). */
  json?: unknown
}

const RUTA_SESION = '/api/sesion'
const TEXTOS_POR_CODIGO: Record<number, string> = {
  400: 'Petición incorrecta',
  401: 'Sesión no iniciada',
  403: 'Consulta rechazada por el filtro de privacidad',
  404: 'Recurso no encontrado',
  409: 'Ya hay una operación en curso',
  422: 'Datos no válidos',
  500: 'Error interno del servidor',
  502: 'El servicio de destino no responde',
  503: 'Servicio no disponible',
  504: 'El servicio de destino ha tardado demasiado',
}

type ManejadorSesionPerdida = () => void
let manejadorSesionPerdida: ManejadorSesionPerdida | null = null

/**
 * Registra quién atiende la pérdida de sesión (la guardia de sesión). Devuelve la función para darse de baja.
 * Sin manejador registrado, el cliente redirige a `/acceso` con `window.location`.
 */
export function alPerderSesion(manejador: ManejadorSesionPerdida): () => void {
  manejadorSesionPerdida = manejador
  return () => {
    if (manejadorSesionPerdida === manejador) manejadorSesionPerdida = null
  }
}

function sesionPerdida(): void {
  if (manejadorSesionPerdida) {
    manejadorSesionPerdida()
  } else if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/acceso')) {
    window.location.assign('/acceso')
  }
}

function esRutaDeSesion(ruta: string): boolean {
  const camino = ruta.split('?')[0].replace(/\/+$/, '')
  return camino === RUTA_SESION || camino.endsWith(RUTA_SESION)
}

async function leerCuerpo(respuesta: Response): Promise<unknown> {
  const texto = await respuesta.text().catch(() => '')
  if (!texto) return null
  try {
    return JSON.parse(texto) as unknown
  } catch {
    return texto
  }
}

/** Texto legible de un error: el `detail` del BFF (cadena o lista de errores de validación de FastAPI). */
export function detalleDe(cuerpo: unknown, status: number): string {
  if (cuerpo && typeof cuerpo === 'object' && 'detail' in cuerpo) {
    const detail = (cuerpo as { detail: unknown }).detail
    if (typeof detail === 'string' && detail) return detail
    if (Array.isArray(detail)) {
      const mensajes = detail
        .map((e) => (e && typeof e === 'object' && 'msg' in e ? String((e as { msg: unknown }).msg) : ''))
        .filter(Boolean)
      if (mensajes.length) return mensajes.join('; ')
    }
  }
  if (typeof cuerpo === 'string' && cuerpo.length > 0 && cuerpo.length < 200) return cuerpo
  return TEXTOS_POR_CODIGO[status] ?? `Error ${status}`
}

/**
 * Llama al BFF y devuelve el JSON de la respuesta (o `undefined` en un 204).
 * Lanza `ErrorApi` con `status`, `detail` y `cuerpo` si la respuesta no es 2xx o si la red falla.
 */
export async function api<T>(ruta: string, init: OpcionesApi = {}): Promise<T> {
  const { json, ...resto } = init
  const cabeceras = new Headers(resto.headers)
  cabeceras.set('Accept', 'application/json')
  let body = resto.body
  if (json !== undefined) {
    body = JSON.stringify(json)
    cabeceras.set('Content-Type', 'application/json')
  } else if (typeof body === 'string' && !cabeceras.has('Content-Type')) {
    cabeceras.set('Content-Type', 'application/json')
  }

  let respuesta: Response
  try {
    respuesta = await fetch(ruta, { ...resto, body, headers: cabeceras, credentials: 'include' })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ErrorApi(0, 'No se ha podido conectar con el portal', null)
  }

  if (respuesta.status === 401 && !esRutaDeSesion(ruta)) {
    sesionPerdida()
  }
  if (!respuesta.ok) {
    const cuerpo = await leerCuerpo(respuesta)
    throw new ErrorApi(respuesta.status, detalleDe(cuerpo, respuesta.status), cuerpo)
  }
  if (respuesta.status === 204 || respuesta.headers.get('content-length') === '0') {
    return undefined as T
  }
  const texto = await respuesta.text()
  return (texto ? JSON.parse(texto) : undefined) as T
}

/** Mensaje para mostrar al usuario a partir de cualquier error (ErrorApi, Error o desconocido). */
export function mensajeDeError(error: unknown): string {
  if (error instanceof ErrorApi) return error.detail
  if (error instanceof Error && error.message) return error.message
  return 'Error desconocido'
}
