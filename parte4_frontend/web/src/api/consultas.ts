/**
 * Explorador de agregados: catálogo, zonas y consultas (`/api/catalogo`, `/api/zonas`, `/api/consultas`).
 *
 *   const catalogo = useCatalogo()                       // niveles, métricas, barrios, k y rango máximo
 *   const zonas = useZonas('jfk')                        // sugerencias del buscador (GET /api/zonas?texto=jfk)
 *   const consultar = useConsulta()                      // mutación: consultar.mutate(consulta)
 *   const resultado = useResultadoConsulta(consulta)     // la misma consulta como query, con caché por consulta
 *
 * `POST /api/consultas` devuelve el mismo código y cuerpo que la API de acceso: un 403 llega como `ErrorApi`
 * cuyo `cuerpo` es la `Decision` (motivos y alternativa) y un 422 como `ErrorApi` con el `detail` de validación.
 * `decisionDe(error)` extrae la `Decision` de un error, o `null` si no es un rechazo.
 */
import { keepPreviousData, useMutation, useQuery } from '@tanstack/react-query'

import { api, ErrorApi } from './cliente'
import type { Catalogo, Consulta, Decision, Respuesta, Zona } from './tipos'

export const CLAVE_CATALOGO = ['catalogo'] as const
export const claveZonas = (texto: string) => ['zonas', texto] as const
export const claveConsulta = (consulta: Consulta) => ['consulta', consulta] as const

export function consultarCatalogo(): Promise<Catalogo> {
  return api<Catalogo>('/api/catalogo')
}

/** Zonas cuyo nombre contiene `texto` (todas si está vacío; la API devuelve como mucho 300). */
export function buscarZonas(texto = ''): Promise<Zona[]> {
  const limpio = texto.trim()
  const ruta = limpio ? `/api/zonas?texto=${encodeURIComponent(limpio)}` : '/api/zonas'
  return api<Zona[]>(ruta)
}

export function ejecutarConsulta(consulta: Consulta): Promise<Respuesta> {
  return api<Respuesta>('/api/consultas', { method: 'POST', json: consulta })
}

/** La `Decision` de un 403 de `POST /api/consultas`; `null` si el error es de otro tipo. */
export function decisionDe(error: unknown): Decision | null {
  if (!(error instanceof ErrorApi) || error.status !== 403) return null
  const cuerpo = error.cuerpo
  if (cuerpo && typeof cuerpo === 'object' && (cuerpo as Decision).resultado === 'rechazada') {
    const decision = cuerpo as Partial<Decision>
    return {
      resultado: 'rechazada',
      motivos: Array.isArray(decision.motivos) ? decision.motivos.map(String) : [],
      alternativa: decision.alternativa ?? null,
    }
  }
  return { resultado: 'rechazada', motivos: [error.detail], alternativa: null }
}

/** El catálogo cambia solo al redesplegar la plataforma: se cachea un buen rato. */
export function useCatalogo() {
  return useQuery({
    queryKey: CLAVE_CATALOGO,
    queryFn: consultarCatalogo,
    staleTime: 10 * 60_000,
  })
}

/**
 * Sugerencias de zonas para el buscador. Con `texto` vacío devuelve todas las zonas (sirve para resolver el
 * nombre de una zona a partir de su id). Mientras llega la respuesta nueva se conserva la anterior.
 */
export function useZonas(texto: string, { habilitado = true }: { habilitado?: boolean } = {}) {
  const limpio = texto.trim()
  return useQuery({
    queryKey: claveZonas(limpio),
    queryFn: () => buscarZonas(limpio),
    enabled: habilitado,
    staleTime: 10 * 60_000,
    placeholderData: keepPreviousData,
  })
}

/** La consulta como mutación (`consultar.mutate(consulta)`), para lanzarla de forma imperativa. */
export function useConsulta() {
  return useMutation({
    mutationFn: ejecutarConsulta,
    retry: false,
  })
}

/**
 * La consulta como query, con caché por consulta: es lo que usa el explorador, cuyo estado vive en la URL.
 * No se reintenta (cada intento queda en la auditoría de la API) y un 403 aparece como `error`.
 */
export function useResultadoConsulta(consulta: Consulta | null) {
  return useQuery({
    queryKey: consulta ? claveConsulta(consulta) : ['consulta', 'vacia'],
    queryFn: () => ejecutarConsulta(consulta as Consulta),
    enabled: consulta !== null,
    retry: false,
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: false,
  })
}
