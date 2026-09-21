import { afterEach, describe, expect, it, vi } from 'vitest'

import { ErrorApi, alPerderSesion, api, detalleDe } from './cliente'

function respuesta(cuerpo: unknown, status = 200, cabeceras: Record<string, string> = { 'Content-Type': 'application/json' }) {
  return new Response(cuerpo === null ? null : JSON.stringify(cuerpo), { status, headers: cabeceras })
}

describe('api()', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('envía JSON con la cookie y devuelve el cuerpo interpretado', async () => {
    const espia = vi.fn(async () => respuesta({ autenticado: true }))
    vi.stubGlobal('fetch', espia)

    const cuerpo = await api<{ autenticado: boolean }>('/api/sesion', { method: 'POST', json: { clave: 'x' } })

    expect(cuerpo).toEqual({ autenticado: true })
    const [, init] = espia.mock.calls[0] as unknown as [string, RequestInit]
    expect(init.credentials).toBe('include')
    expect(init.body).toBe('{"clave":"x"}')
    expect(new Headers(init.headers).get('Content-Type')).toBe('application/json')
  })

  it('un 204 devuelve undefined', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 204 })))
    await expect(api<void>('/api/sesion', { method: 'DELETE' })).resolves.toBeUndefined()
  })

  it('un error lanza ErrorApi con status, detail y cuerpo', async () => {
    const decision = { detail: 'Consulta rechazada', resultado: 'rechazada', motivos: ['ventana demasiado corta'] }
    vi.stubGlobal('fetch', vi.fn(async () => respuesta(decision, 403)))

    const error = await api('/api/consultas', { method: 'POST', json: {} }).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ErrorApi)
    const e = error as ErrorApi
    expect(e.status).toBe(403)
    expect(e.detail).toBe('Consulta rechazada')
    expect(e.cuerpo).toEqual(decision)
  })

  it('un 401 fuera de /api/sesion avisa a la guardia de sesión', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => respuesta({ detail: 'Sesión no iniciada' }, 401)))
    const manejador = vi.fn()
    const baja = alPerderSesion(manejador)

    await expect(api('/api/panel')).rejects.toMatchObject({ status: 401, detail: 'Sesión no iniciada' })
    expect(manejador).toHaveBeenCalledTimes(1)

    await expect(api('/api/sesion')).rejects.toMatchObject({ status: 401 })
    expect(manejador).toHaveBeenCalledTimes(1)   // en /api/sesion un 401 no es «sesión perdida»
    baja()
  })

  it('sin red lanza ErrorApi con status 0', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('Failed to fetch') }))
    await expect(api('/api/salud')).rejects.toMatchObject({ status: 0, detail: 'No se ha podido conectar con el portal' })
  })
})

describe('detalleDe()', () => {
  it('usa el detail del cuerpo, los mensajes de validación de FastAPI o un texto por código', () => {
    expect(detalleDe({ detail: 'Clave incorrecta' }, 401)).toBe('Clave incorrecta')
    expect(detalleDe({ detail: [{ msg: 'campo obligatorio' }, { msg: 'fecha no válida' }] }, 422)).toBe(
      'campo obligatorio; fecha no válida',
    )
    expect(detalleDe(null, 503)).toBe('Servicio no disponible')
    expect(detalleDe(null, 418)).toBe('Error 418')
  })
})
