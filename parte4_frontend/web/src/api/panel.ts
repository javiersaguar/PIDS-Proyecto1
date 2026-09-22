/**
 * Panel de inicio: `GET /api/panel` con TanStack Query.
 *
 *   const panel = usePanel()                          // panel.data: Panel · se refresca solo cada 60 s
 *   const panel = usePanel({ intervaloMs: 20_000 })   // más a menudo mientras la plataforma trabaja
 *
 * Comparte la clave `['panel']` con los chips de la cabecera (`useEstadoServicios`) y con `useActividad`, de modo
 * que una sola petición sirve a la página y al shell; con varios observadores manda el intervalo más corto.
 */
import { useQuery } from '@tanstack/react-query'

import { CLAVE_PANEL } from '@/componentes/shell/servicios'

import { api } from './cliente'
import type { Panel, UltimoDia } from './tipos'

export const INTERVALO_PANEL_MS = 60_000
/** Con una carga, una simulación o Spark publicando: el BFF cachea el último día 60 s, pero la frescura y las
 * decisiones (Prometheus) y el último día de tiempo real cambian antes. */
export const INTERVALO_PANEL_ACTIVO_MS = 20_000

// `acceso_disponible` y `ultimo_dia.*.grupos_enmascarados` ya forman parte del contrato (§5): los alias se
// conservan para los componentes del panel.
export type UltimoDiaExtendido = UltimoDia
export type PanelExtendido = Panel

export function consultarPanel(): Promise<PanelExtendido> {
  return api<PanelExtendido>('/api/panel')
}

export function usePanel({ intervaloMs = INTERVALO_PANEL_MS }: { intervaloMs?: number } = {}) {
  return useQuery({
    queryKey: CLAVE_PANEL,
    queryFn: consultarPanel,
    staleTime: Math.min(30_000, intervaloMs),
    refetchInterval: intervaloMs,
    refetchOnWindowFocus: false,
  })
}
