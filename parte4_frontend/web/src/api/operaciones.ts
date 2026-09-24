/**
 * Operaciones (CONTRATOS.md §5, bloque F1 del BFF): cargas históricas en Airflow y el simulador de tiempo real.
 *
 *   useEjecucionesAirflow()                        // GET /api/operaciones/airflow/ejecuciones (cada 15 s)
 *   await lanzarCarga({ mes: '2020-01', muestra: false })   // POST /api/operaciones/airflow/cargas → 202
 *   useSimulacion()                                // GET /api/operaciones/simulacion (cada 2 s mientras está activa)
 *   useFicherosSimulacion()                        // GET /api/operaciones/simulacion/ficheros → string[]
 *   await iniciarSimulacion({ fichero, ritmo, maximo, sinteticos })  // POST /api/operaciones/simulacion → 202 (409 si ya hay una)
 *   await pararSimulacion()                        // DELETE /api/operaciones/simulacion
 *
 * Si Airflow no responde, el BFF puede contestar con un error 502/503 (→ tarjeta de error con «Reintentar») o con
 * una lista vacía; ninguno de los dos rompe la página.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { CLAVE_PANEL } from '@/componentes/shell/servicios'

import { api } from './cliente'
import type { EjecucionAirflow, Panel, Simulacion } from './tipos'

/** Enlaces del menú (§3, `ENLACES_*`) por si `GET /api/panel` no responde: los puertos publicados por defecto. */
export const ENLACES_POR_DEFECTO: Panel['enlaces'] = {
  grafana: 'http://localhost:3000',
  airflow: 'http://localhost:8085',
  chatbot: 'http://localhost:8010',
  chatbot_rag: 'http://localhost:8011',
  api_acceso: 'http://localhost:8002/docs',
  api_captura: 'http://localhost:8001/docs',
  // sin login: solo responden con `make ver` (proxy de solo lectura, docs/seguridad.md)
  spark: 'http://localhost:8090',
  prometheus: 'http://localhost:9091',
  qdrant: 'http://localhost:6333/dashboard',
  seaweed: 'http://localhost:9333',
}

/**
 * Enlaces a las herramientas leídos de `GET /api/panel` (misma clave que la cabecera, una sola petición) y, si el
 * panel no responde o no trae alguno, los valores por defecto. Nunca deja de devolver algo.
 */
export function useEnlaces() {
  const panel = useQuery({
    queryKey: CLAVE_PANEL,
    queryFn: () => api<Panel>('/api/panel'),
    retry: false,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  })
  const recibidos = Object.fromEntries(Object.entries(panel.data?.enlaces ?? {}).filter(([, v]) => typeof v === 'string' && v !== ''))
  const enlaces: Panel['enlaces'] = { ...ENLACES_POR_DEFECTO, ...recibidos }
  return { enlaces, delPanel: Object.keys(recibidos).length > 0, cargando: panel.isPending }
}

export const CLAVE_OPERACIONES = ['operaciones'] as const
export const CLAVE_EJECUCIONES = [...CLAVE_OPERACIONES, 'airflow', 'ejecuciones'] as const
export const CLAVE_SIMULACION = [...CLAVE_OPERACIONES, 'simulacion'] as const
export const CLAVE_FICHEROS = [...CLAVE_OPERACIONES, 'simulacion', 'ficheros'] as const

const RUTA_AIRFLOW = '/api/operaciones/airflow'
const RUTA_SIMULACION = '/api/operaciones/simulacion'

export interface PeticionCarga {
  /** `2020-01` … `2020-12` (el BFF lo valida con `^2020-(0[1-9]|1[0-2])$`). */
  mes: string
  /** Con `true` el DAG carga solo `data/muestra` (999 viajes) en vez de descargar el mes de la TLC. */
  muestra: boolean
}

export interface PeticionSimulacion {
  fichero: string
  ritmo?: number
  maximo?: number
  /** Viajes inventados a partir del fichero, en vez de enviarlo entero. */
  sinteticos?: number
  semilla?: number
}

/** Tope del BFF (`SIM.MAXIMO_SINTETICOS`): más viajes generados bloquearían la petición. */
export const MAXIMO_SINTETICOS = 200_000

/** Los doce meses que admite el DAG `pids_carga_historica`. */
export const MESES_2020 = Array.from({ length: 12 }, (_, i) => `2020-${String(i + 1).padStart(2, '0')}`)

export interface EstadoMuestra {
  bloqueada: boolean
  motivo: string | null
}

/** Si la muestra de 999 viajes pisaría un histórico ya cargado. */
export function useEstadoMuestra() {
  return useQuery({
    queryKey: [...CLAVE_OPERACIONES, 'airflow', 'muestra'] as const,
    queryFn: () => api<EstadoMuestra>(`${RUTA_AIRFLOW}/muestra`),
    staleTime: 30_000,
  })
}

export function useEjecucionesAirflow() {
  return useQuery({
    queryKey: CLAVE_EJECUCIONES,
    queryFn: () => api<EjecucionAirflow[]>(`${RUTA_AIRFLOW}/ejecuciones`),
    refetchInterval: 15_000,
    staleTime: 10_000,
  })
}

export function lanzarCarga(peticion: PeticionCarga): Promise<EjecucionAirflow> {
  return api<EjecucionAirflow>(`${RUTA_AIRFLOW}/cargas`, { method: 'POST', json: peticion })
}

export function useLanzarCarga() {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: lanzarCarga,
    onSuccess: () => void cliente.invalidateQueries({ queryKey: CLAVE_EJECUCIONES }),
  })
}

/** Estado del simulador; mientras está activo se refresca cada 2 s para mover la barra de progreso. */
export function useSimulacion() {
  return useQuery({
    queryKey: CLAVE_SIMULACION,
    queryFn: () => api<Simulacion>(RUTA_SIMULACION),
    refetchInterval: (consulta) => (consulta.state.data?.activa ? 2_000 : 15_000),
    staleTime: 1_000,
  })
}

export function useFicherosSimulacion() {
  return useQuery({
    queryKey: CLAVE_FICHEROS,
    queryFn: () => api<string[]>(`${RUTA_SIMULACION}/ficheros`),
    staleTime: 5 * 60_000,
  })
}

export function iniciarSimulacion(peticion: PeticionSimulacion): Promise<Simulacion> {
  const cuerpo: PeticionSimulacion = { fichero: peticion.fichero }
  if (peticion.ritmo !== undefined) cuerpo.ritmo = peticion.ritmo
  if (peticion.maximo !== undefined) cuerpo.maximo = peticion.maximo
  if (peticion.sinteticos !== undefined) cuerpo.sinteticos = peticion.sinteticos
  if (peticion.semilla !== undefined) cuerpo.semilla = peticion.semilla
  return api<Simulacion>(RUTA_SIMULACION, { method: 'POST', json: cuerpo })
}

export async function pararSimulacion(): Promise<Simulacion | undefined> {
  return api<Simulacion | undefined>(RUTA_SIMULACION, { method: 'DELETE' })
}

export function useIniciarSimulacion() {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: iniciarSimulacion,
    onSuccess: (simulacion) => {
      cliente.setQueryData<Simulacion>(CLAVE_SIMULACION, simulacion)
    },
    onSettled: () => void cliente.invalidateQueries({ queryKey: CLAVE_SIMULACION }),
  })
}

export function usePararSimulacion() {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: pararSimulacion,
    onSuccess: (simulacion) => {
      if (simulacion) cliente.setQueryData<Simulacion>(CLAVE_SIMULACION, simulacion)
    },
    onSettled: () => void cliente.invalidateQueries({ queryKey: CLAVE_SIMULACION }),
  })
}
