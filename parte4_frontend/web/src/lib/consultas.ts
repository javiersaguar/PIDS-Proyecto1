/**
 * Cliente de TanStack Query del portal, con los valores por defecto comunes a todas las páginas.
 * Los tests crean el suyo con `crearClientePruebas()` (sin reintentos ni caché).
 */
import { QueryClient } from '@tanstack/react-query'

import { ErrorApi } from '@/api/cliente'

/** Un 4xx no se arregla reintentando (401 sesión, 403 privacidad, 404 sin datos, 422 validación). */
export function reintentar(intentos: number, error: unknown): boolean {
  if (error instanceof ErrorApi && error.status >= 400 && error.status < 500) return false
  return intentos < 2
}

export function crearClienteConsultas() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        retry: reintentar,
      },
    },
  })
}
