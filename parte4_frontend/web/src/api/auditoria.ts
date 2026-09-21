/**
 * Privacidad y auditoría (CONTRATOS.md §5, bloque F1 del BFF), con TanStack Query:
 *
 *   useCatalogo()                                    // GET /api/catalogo (reglas E3 de la API de acceso)
 *   useAuditoriaResumen(24)                          // GET /api/auditoria/resumen?horas=24
 *   useDecisiones({ horas: 24, resultado: 'rechazada', cliente: 'chatbot', limite: 100 })
 *   useCargas()                                      // GET /api/auditoria/cargas
 *
 * `disponible: false` en el resumen significa que MongoDB (usuario `pids_auditor`) no responde: la página lo
 * muestra como «MongoDB no disponible» y no pide las decisiones.
 */
import { useQuery } from '@tanstack/react-query'

import { api } from './cliente'
import type { AuditoriaResumen, Carga, Catalogo, DecisionAuditada } from './tipos'

export const CLAVE_CATALOGO = ['catalogo'] as const
export const CLAVE_AUDITORIA = ['auditoria'] as const

export interface FiltrosDecisiones {
  horas: number
  resultado?: string
  cliente?: string
  limite?: number
}

/** Las horas que ofrece la página (1 h, 8 h, 24 h, 7 días). */
export const HORAS_AUDITORIA = [1, 8, 24, 168] as const

export function useCatalogo() {
  return useQuery({
    queryKey: CLAVE_CATALOGO,
    queryFn: () => api<Catalogo>('/api/catalogo'),
    staleTime: 10 * 60_000,
  })
}

export function useAuditoriaResumen(horas: number) {
  return useQuery({
    queryKey: [...CLAVE_AUDITORIA, 'resumen', horas],
    queryFn: () => api<AuditoriaResumen>(`/api/auditoria/resumen?horas=${horas}`),
    staleTime: 15_000,
    refetchInterval: 60_000,
  })
}

/** Construye la query string sin parámetros vacíos, para que el BFF no reciba `resultado=`. */
export function rutaDecisiones({ horas, resultado, cliente, limite = 100 }: FiltrosDecisiones): string {
  const parametros = new URLSearchParams({ horas: String(horas), limite: String(limite) })
  if (resultado) parametros.set('resultado', resultado)
  if (cliente) parametros.set('cliente', cliente)
  return `/api/auditoria/decisiones?${parametros.toString()}`
}

export function useDecisiones(filtros: FiltrosDecisiones, activo = true) {
  return useQuery({
    queryKey: [...CLAVE_AUDITORIA, 'decisiones', filtros],
    queryFn: () => api<DecisionAuditada[]>(rutaDecisiones(filtros)),
    enabled: activo,
    staleTime: 15_000,
  })
}

export function useCargas() {
  return useQuery({
    queryKey: [...CLAVE_AUDITORIA, 'cargas'],
    queryFn: () => api<Carga[]>('/api/auditoria/cargas'),
    staleTime: 60_000,
  })
}
