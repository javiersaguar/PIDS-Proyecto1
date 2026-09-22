/**
 * Observabilidad: los cuadros de Grafana con sus datos, para dibujarlos en el portal (`bff/rutas/observabilidad.py`).
 *
 *   const lista = useCuadros()              // GET /api/observabilidad/cuadros → [{uid, titulo, periodo}]
 *   const cuadro = useCuadro('pids-spark')  // GET /api/observabilidad/cuadros/{uid}, cada 30 s como Grafana
 *
 * Al cambiar de cuadro o refrescar se conserva el anterior mientras llega el nuevo: los números y las gráficas se
 * deslizan hacia los valores nuevos en lugar de parpadear.
 */
import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { api } from './cliente'

export const REFRESCO_CUADRO_MS = 30_000

export interface ResumenCuadro {
  uid: string
  titulo: string
  /** Periodo del cuadro, como en Grafana: `6h`, `24h`, `3h`. */
  periodo: string
}

export interface ValorPanel {
  nombre: string
  valor: number | null
}

export interface SeriePanel {
  nombre: string
  /** `[segundos desde la época, valor]`. */
  puntos: [number, number | null][]
}

export interface AlertaPanel {
  nombre: string
  estado: 'firing' | 'pending' | 'inactive' | string
  resumen: string
}

export interface PanelCuadro {
  id: number
  tipo: 'fila' | 'stat' | 'serie' | 'barras' | 'tarta' | 'texto' | 'alertas'
  titulo: string
  descripcion: string
  /** Posición en la rejilla de 24 columnas de Grafana. */
  x: number
  y: number
  ancho: number
  alto: number
  unidad: string
  color: string | null
  umbrales: { color: string; desde: number | null }[]
  mapeos: Record<string, { texto: string | null; color: string | null }>
  colores: Record<string, string>
  texto: string | null
  valores?: ValorPanel[]
  chispa?: number[]
  series?: SeriePanel[]
  alertas?: AlertaPanel[]
  error?: string
}

export interface Cuadro extends ResumenCuadro {
  /** Segundos desde la época de cuando se consultó. */
  actualizado: number
  disponible: boolean
  paneles: PanelCuadro[]
  /** Solo en la demostración: cuándo se grabaron los datos. */
  grabado?: string
}

export function useCuadros() {
  return useQuery({
    queryKey: ['observabilidad', 'cuadros'],
    queryFn: () => api<ResumenCuadro[]>('/api/observabilidad/cuadros'),
    staleTime: 10 * 60_000,
  })
}

export function useCuadro(uid: string) {
  return useQuery({
    queryKey: ['observabilidad', 'cuadro', uid],
    queryFn: () => api<Cuadro>(`/api/observabilidad/cuadros/${encodeURIComponent(uid)}`),
    refetchInterval: REFRESCO_CUADRO_MS,
    staleTime: 10_000,
    placeholderData: keepPreviousData,
  })
}
