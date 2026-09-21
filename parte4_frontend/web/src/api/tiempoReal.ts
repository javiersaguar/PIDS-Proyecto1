/**
 * Tiempo real: `GET /api/tiempo-real?horas=6` con TanStack Query, refrescado cada 30 s.
 *
 *   const tiempoReal = useTiempoReal(6)     // tiempoReal.data: TiempoReal · tiempoReal.dataUpdatedAt para «hace X s»
 */
import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { api } from './cliente'
import type { TiempoReal } from './tipos'

export const INTERVALO_TIEMPO_REAL_MS = 30_000
export const HORAS_TIEMPO_REAL = [6, 12, 24] as const
export type HorasTiempoReal = (typeof HORAS_TIEMPO_REAL)[number]

export const claveTiempoReal = (horas: number) => ['tiempo-real', horas] as const

// `acceso_disponible` ya forma parte del contrato (§5): el alias se conserva para la página.
export type TiempoRealExtendido = TiempoReal

export function consultarTiempoReal(horas: number): Promise<TiempoRealExtendido> {
  return api<TiempoRealExtendido>(`/api/tiempo-real?horas=${horas}`)
}

/** Al cambiar de 6 a 12 o 24 horas se conserva la respuesta anterior mientras llega la nueva (sin parpadeo). */
export function useTiempoReal(horas: number) {
  return useQuery({
    queryKey: claveTiempoReal(horas),
    queryFn: () => consultarTiempoReal(horas),
    staleTime: 15_000,
    refetchInterval: INTERVALO_TIEMPO_REAL_MS,
    refetchOnWindowFocus: false,
    placeholderData: keepPreviousData,
  })
}
