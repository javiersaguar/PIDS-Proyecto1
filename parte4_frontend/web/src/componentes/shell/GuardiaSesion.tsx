/**
 * Guardia de sesión (§4): consulta `GET /api/sesion` y, si no hay sesión, manda a `/acceso`.
 * También atiende los 401 que el cliente HTTP detecta en cualquier otra ruta (sesión caducada).
 */
import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router'

import { alPerderSesion } from '@/api/cliente'
import { CLAVE_SESION, useSesion } from '@/api/sesion'
import type { EstadoSesion } from '@/api/tipos'

import { EstadoCargando, EstadoError } from './Estados'

export function GuardiaSesion() {
  const sesion = useSesion()
  const cliente = useQueryClient()
  const navegar = useNavigate()
  const ubicacion = useLocation()

  useEffect(
    () =>
      alPerderSesion(() => {
        cliente.setQueryData<EstadoSesion>(CLAVE_SESION, { autenticado: false })
        void navegar('/acceso', { replace: true, state: { caducada: true } })
      }),
    [cliente, navegar],
  )

  if (sesion.isPending) {
    return <EstadoCargando variante="pantalla" etiqueta="Comprobando la sesión…" />
  }
  if (sesion.isError) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-fondo p-6">
        <EstadoError
          className="w-full max-w-lg"
          titulo="El portal no responde"
          error={sesion.error}
          alReintentar={() => void sesion.refetch()}
          reintentando={sesion.isFetching}
        />
      </div>
    )
  }
  if (!sesion.data.autenticado) {
    return <Navigate to="/acceso" replace state={{ desde: ubicacion.pathname }} />
  }
  return <Outlet />
}
