/**
 * Panel de inicio: `GET /api/panel` con TanStack Query.
 *
 *   const panel = usePanel()      // panel.data: Panel · se refresca solo cada 60 s
 *
 * Comparte la clave `['panel']` con los chips de la cabecera (`useEstadoServicios`), de modo que una sola
 * petición sirve a la página y al shell.
 */
import { useQuery } from '@tanstack/react-query'

import { CLAVE_PANEL } from '@/componentes/shell/servicios'

import { api } from './cliente'
import type { Panel, UltimoDia } from './tipos'

export const INTERVALO_PANEL_MS = 60_000

// `acceso_disponible` y `ultimo_dia.*.grupos_enmascarados` ya forman parte del contrato (§5): los alias se
// conservan para los componentes del panel.
export type UltimoDiaExtendido = UltimoDia
export type PanelExtendido = Panel

export function consultarPanel(): Promise<PanelExtendido> {
  return api<PanelExtendido>('/api/panel')
}

export function usePanel() {
  return useQuery({
    queryKey: CLAVE_PANEL,
    queryFn: consultarPanel,
    staleTime: 30_000,
    refetchInterval: INTERVALO_PANEL_MS,
    refetchOnWindowFocus: false,
  })
}
