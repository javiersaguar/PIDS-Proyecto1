/**
 * Estado de los servicios para los chips de la cabecera: `GET /api/panel` → `servicios`.
 * Comparte la clave `['panel']` con la página del panel (F3), de modo que una sola petición sirve a las dos.
 * Si el endpoint aún no existe o falla, la cabecera simplemente no muestra nada.
 */
import { useQuery } from '@tanstack/react-query'

import { api } from '@/api/cliente'
import type { Panel, Servicio } from '@/api/tipos'

export const CLAVE_PANEL = ['panel'] as const

export function useEstadoServicios() {
  return useQuery({
    queryKey: CLAVE_PANEL,
    queryFn: () => api<Panel>('/api/panel'),
    select: (panel): Servicio[] => panel.servicios ?? [],
    retry: false,
    staleTime: 30_000,
    refetchInterval: 60_000,
    refetchOnWindowFocus: false,
  })
}
