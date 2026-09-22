/**
 * Captura en directo (botón «Capturar datos» del grafo): viajes reales de un mes de 2020 que el portal envía a la
 * API de captura con un reloj simulado (`parte2_plataforma/simulador/directo.py`).
 *
 *   const info = useInfoCaptura()          // GET /api/operaciones/captura: qué hay preparado y por dónde seguiría
 *   const iniciar = useIniciarCaptura()    // POST /api/operaciones/captura {velocidad} → 202 Simulacion (modo 'directo')
 *   const parar = usePararCaptura()        // DELETE /api/operaciones/captura
 *
 * El estado es el de la simulación (`useSimulacion`, misma clave de TanStack Query): por eso la barra de actividad y
 * el lienzo (T15) la ven y encienden el tramo Simulador → Captura → Redpanda → Spark sin saber nada de esto.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from './cliente'
import { CLAVE_OPERACIONES, CLAVE_SIMULACION } from './operaciones'
import type { Simulacion } from './tipos'

export interface InfoCaptura {
  disponible: boolean
  primer_dia: string | null
  ultimo_dia: string | null
  /** Por dónde iba la última captura de este portal (hora de 2020), si hubo alguna. */
  reloj: string | null
  velocidad_por_defecto: number
  velocidad_maxima: number
  /** Solo en la demostración pública: la captura anima el grafo, pero no envía viajes. */
  demostracion?: boolean
}

/** La `Simulacion` del contrato con los campos de la captura en directo. */
export interface SimulacionCaptura extends Simulacion {
  modo?: 'fichero' | 'directo'
  /** Hora de 2020 por la que va la captura (ISO sin zona). */
  reloj?: string | null
  /** Segundos de 2020 por segundo real. */
  velocidad?: number | null
}

export const CLAVE_CAPTURA = [...CLAVE_OPERACIONES, 'captura'] as const
const RUTA = '/api/operaciones/captura'

/** Las velocidades que ofrece el grafo, en segundos de 2020 por segundo real. */
export const VELOCIDADES = [
  { valor: 60, texto: '1 h por minuto' },
  { valor: 360, texto: '6 h por minuto' },
  { valor: 10, texto: '10 min por minuto' },
] as const

export function useInfoCaptura() {
  return useQuery({
    queryKey: CLAVE_CAPTURA,
    queryFn: () => api<InfoCaptura>(RUTA),
    staleTime: 30_000,
  })
}

function useAlTerminar() {
  const cliente = useQueryClient()
  return {
    onSuccess: (simulacion: SimulacionCaptura | undefined) => {
      if (simulacion) cliente.setQueryData<SimulacionCaptura>(CLAVE_SIMULACION, simulacion)
    },
    onSettled: () => {
      void cliente.invalidateQueries({ queryKey: CLAVE_SIMULACION })
      void cliente.invalidateQueries({ queryKey: CLAVE_CAPTURA })
    },
  }
}

export function useIniciarCaptura() {
  return useMutation({
    mutationFn: (velocidad: number) => api<SimulacionCaptura>(RUTA, { method: 'POST', json: { velocidad } }),
    ...useAlTerminar(),
  })
}

export function usePararCaptura() {
  return useMutation({
    mutationFn: () => api<SimulacionCaptura>(RUTA, { method: 'DELETE' }),
    ...useAlTerminar(),
  })
}

/** `2020-12-01T14:35:00` → `01/12/2020 14:35`. */
export function formatearReloj(iso: string | null | undefined): string | null {
  const partes = iso ? /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(iso) : null
  return partes ? `${partes[3]}/${partes[2]}/${partes[1]} ${partes[4]}:${partes[5]}` : null
}
