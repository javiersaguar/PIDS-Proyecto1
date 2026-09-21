/**
 * Utilidades para los tests de la SPA (F0, F3 y F4):
 *
 *   simularApi({ 'GET /api/sesion': { autenticado: true }, 'GET /api/panel': { status: 404 } })
 *   renderizarRutas('/explorador')                 // toda la aplicación, en memoria, en esa ruta
 *   renderizarConProveedores(<MiComponente />)      // un componente suelto con TanStack Query y tooltips
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, type RenderOptions } from '@testing-library/react'
import { useState, type ReactElement, type ReactNode } from 'react'
import { MemoryRouter, RouterProvider } from 'react-router'
import { vi } from 'vitest'

import { TooltipProvider } from '@/componentes/ui/tooltip'
import { crearEnrutadorEnMemoria } from '@/rutas'

/** Cliente de consultas para tests: sin reintentos ni caché entre tests. */
export function crearClientePruebas() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
      mutations: { retry: false },
    },
  })
}

export function Proveedores({ children, cliente }: { children: ReactNode; cliente?: QueryClient }) {
  const [clienteConsultas] = useState(() => cliente ?? crearClientePruebas())
  return (
    <QueryClientProvider client={clienteConsultas}>
      <TooltipProvider>{children}</TooltipProvider>
    </QueryClientProvider>
  )
}

interface OpcionesRender extends Omit<RenderOptions, 'wrapper'> {
  /** Ruta inicial del `MemoryRouter` que envuelve al componente (por defecto `/`). */
  ruta?: string
  cliente?: QueryClient
}

/** Renderiza un componente suelto con TanStack Query, tooltips y un `MemoryRouter`. */
export function renderizarConProveedores(ui: ReactElement, { ruta = '/', cliente, ...opciones }: OpcionesRender = {}) {
  return render(ui, {
    wrapper: ({ children }) => (
      <Proveedores cliente={cliente}>
        <MemoryRouter initialEntries={[ruta]}>{children}</MemoryRouter>
      </Proveedores>
    ),
    ...opciones,
  })
}

/** Renderiza la aplicación completa (rutas reales) empezando en `ruta`. Devuelve también el enrutador. */
export function renderizarRutas(ruta = '/', cliente?: QueryClient) {
  const enrutador = crearEnrutadorEnMemoria([ruta])
  const resultado = render(
    <Proveedores cliente={cliente}>
      <RouterProvider router={enrutador} />
    </Proveedores>,
  )
  return { ...resultado, enrutador }
}

/** Respuesta simulada: un cuerpo JSON directo, o `{ status, json }` para otros códigos (204 sin cuerpo). */
export type RespuestaSimulada = { status?: number; json?: unknown } | unknown

type Manejador = RespuestaSimulada | ((init: RequestInit, url: URL) => RespuestaSimulada)

function esConEstado(r: unknown): r is { status?: number; json?: unknown } {
  return !!r && typeof r === 'object' && ('status' in r || 'json' in r) && Object.keys(r).every((k) => k === 'status' || k === 'json')
}

/**
 * Sustituye `fetch` por un doble que responde según `'MÉTODO /ruta'` (sin query). Lo que no esté declarado
 * responde 404 `{detail}`. Devuelve el espía para comprobar las llamadas (`espia.mock.calls`).
 */
export function simularApi(respuestas: Record<string, Manejador>) {
  const espia = vi.fn(async (entrada: RequestInfo | URL, init: RequestInit = {}) => {
    const url = new URL(typeof entrada === 'string' ? entrada : entrada instanceof URL ? entrada.href : entrada.url, 'http://localhost')
    const metodo = (init.method ?? 'GET').toUpperCase()
    const manejador = respuestas[`${metodo} ${url.pathname}`]
    const bruto = typeof manejador === 'function' ? (manejador as (i: RequestInit, u: URL) => RespuestaSimulada)(init, url) : manejador
    if (bruto instanceof Response) return bruto
    if (manejador === undefined) return respuestaJson({ detail: 'Recurso no encontrado' }, 404)
    if (esConEstado(bruto)) return respuestaJson(bruto.json, bruto.status ?? 200)
    return respuestaJson(bruto, 200)
  })
  vi.stubGlobal('fetch', espia)
  return espia
}

export function respuestaJson(cuerpo: unknown, status = 200): Response {
  if (status === 204 || cuerpo === undefined) {
    return new Response(null, { status })
  }
  return new Response(JSON.stringify(cuerpo), { status, headers: { 'Content-Type': 'application/json' } })
}

/** Cuerpo JSON de la llamada n-ésima (por defecto la última) al `fetch` simulado. */
export function cuerpoEnviado(espia: ReturnType<typeof simularApi>, indice = -1): unknown {
  const llamada = espia.mock.calls.at(indice)
  const init = llamada?.[1] as RequestInit | undefined
  return typeof init?.body === 'string' ? JSON.parse(init.body) : undefined
}
