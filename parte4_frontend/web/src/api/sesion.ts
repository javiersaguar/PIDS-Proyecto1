/**
 * Sesión del portal (§4): `GET/POST/DELETE /api/sesion` con TanStack Query.
 *
 *   const { data } = useSesion()            // { autenticado: boolean }
 *   const entrar = useIniciarSesion()       // entrar.mutate(clave)
 *   const salir = useCerrarSesion()         // salir.mutate()
 *
 * Las funciones sueltas (`iniciarSesion`, `cerrarSesion`) hacen la petición sin tocar la caché; los hooks,
 * además, dejan la caché coherente (y la vacían al salir, para no conservar datos de la sesión anterior).
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from './cliente'
import type { EstadoSesion } from './tipos'

export const CLAVE_SESION = ['sesion'] as const
const RUTA = '/api/sesion'

export function consultarSesion(): Promise<EstadoSesion> {
  return api<EstadoSesion>(RUTA)
}

export async function iniciarSesion(clave: string): Promise<void> {
  await api<void>(RUTA, { method: 'POST', json: { clave } })
}

export async function cerrarSesion(): Promise<void> {
  await api<void>(RUTA, { method: 'DELETE' })
}

/** Estado de la sesión. No reintenta (un fallo aquí es que el BFF no responde) y se refresca al volver a la pestaña. */
export function useSesion() {
  return useQuery({
    queryKey: CLAVE_SESION,
    queryFn: consultarSesion,
    retry: false,
    staleTime: 60_000,
    refetchOnWindowFocus: true,
  })
}

export function useIniciarSesion() {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: iniciarSesion,
    onSuccess: () => {
      cliente.setQueryData<EstadoSesion>(CLAVE_SESION, { autenticado: true })
    },
  })
}

export function useCerrarSesion() {
  const cliente = useQueryClient()
  return useMutation({
    mutationFn: cerrarSesion,
    onSettled: () => {
      // Se vacía todo (no solo la sesión): ninguna cifra de la sesión anterior debe quedar en memoria.
      cliente.clear()
      cliente.setQueryData<EstadoSesion>(CLAVE_SESION, { autenticado: false })
    },
  })
}
