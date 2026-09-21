/**
 * Los cuatro estados obligatorios de toda página (§6): cargando, error, sin datos y servicio no disponible.
 * F3 y F4 los reutilizan tal cual desde `@/componentes/shell`.
 */
import { Inbox, RefreshCw, TriangleAlert, Unplug } from 'lucide-react'
import type { ReactNode } from 'react'

import { mensajeDeError } from '@/api/cliente'
import { Button } from '@/componentes/ui/button'
import { Card, CardContent } from '@/componentes/ui/card'
import { Skeleton } from '@/componentes/ui/skeleton'
import { cn } from '@/lib/utils'

interface PropsCargando {
  /** Número de líneas de skeleton (por defecto 3). */
  lineas?: number
  /** Texto para lectores de pantalla y tooltips. */
  etiqueta?: string
  /** `tarjeta` pinta los skeletons dentro de una tarjeta; `pantalla` centra un indicador a pantalla completa. */
  variante?: 'lineas' | 'tarjeta' | 'pantalla'
  className?: string
}

export function EstadoCargando({ lineas = 3, etiqueta = 'Cargando…', variante = 'lineas', className }: PropsCargando) {
  if (variante === 'pantalla') {
    return (
      <div role="status" aria-label={etiqueta} className={cn('flex min-h-svh items-center justify-center bg-fondo', className)}>
        <div className="flex items-center gap-3 text-texto-suave">
          <span className="size-2.5 animate-pulse rounded-full bg-acento" />
          <span>{etiqueta}</span>
        </div>
      </div>
    )
  }
  const contenido = (
    <div className="space-y-2.5">
      {Array.from({ length: lineas }, (_, i) => (
        <Skeleton key={i} className={cn('h-4', i === 0 ? 'w-2/5' : i % 3 === 2 ? 'w-3/5' : 'w-full')} />
      ))}
    </div>
  )
  return (
    <div role="status" aria-label={etiqueta} className={className}>
      {variante === 'tarjeta' ? (
        <Card>
          <CardContent>{contenido}</CardContent>
        </Card>
      ) : (
        contenido
      )}
    </div>
  )
}

interface PropsError {
  /** El error (normalmente un `ErrorApi`, del que se muestra el `detail`). */
  error: unknown
  titulo?: string
  /** Si se indica, se muestra el botón «Reintentar». */
  alReintentar?: () => void
  reintentando?: boolean
  className?: string
}

export function EstadoError({ error, titulo = 'No se ha podido cargar', alReintentar, reintentando, className }: PropsError) {
  return (
    <Card role="alert" className={cn('border-l-4 border-l-peligro ring-peligro/20', className)}>
      <CardContent className="flex items-start gap-3">
        <TriangleAlert className="mt-0.5 size-5 shrink-0 text-peligro" aria-hidden />
        <div className="min-w-0 flex-1 space-y-1">
          <p className="font-medium text-foreground">{titulo}</p>
          <p className="text-texto-suave break-words">{mensajeDeError(error)}</p>
        </div>
        {alReintentar && (
          <Button variant="outline" size="sm" onClick={alReintentar} disabled={reintentando}>
            <RefreshCw className={cn(reintentando && 'animate-spin')} aria-hidden />
            Reintentar
          </Button>
        )}
      </CardContent>
    </Card>
  )
}

interface PropsVacio {
  titulo?: string
  descripcion?: ReactNode
  icono?: ReactNode
  /** Acción opcional (por ejemplo, un botón para cambiar los filtros). */
  accion?: ReactNode
  className?: string
}

export function EstadoVacio({ titulo = 'Sin datos', descripcion, icono, accion, className }: PropsVacio) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed px-6 py-10 text-center', className)}>
      <span className="text-texto-suave">{icono ?? <Inbox className="size-7" aria-hidden />}</span>
      <p className="font-medium">{titulo}</p>
      {descripcion && <p className="max-w-md text-texto-suave">{descripcion}</p>}
      {accion && <div className="mt-2">{accion}</div>}
    </div>
  )
}

interface PropsNoDisponible {
  /** Nombre del servicio que no responde (Prometheus, Airflow, Ollama, MongoDB…). */
  servicio: string
  descripcion?: ReactNode
  alReintentar?: () => void
  className?: string
}

export function EstadoNoDisponible({ servicio, descripcion, alReintentar, className }: PropsNoDisponible) {
  return (
    <div
      role="status"
      className={cn('flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-aviso/40 bg-aviso/5 px-6 py-10 text-center', className)}
    >
      <Unplug className="size-7 text-aviso" aria-hidden />
      <p className="font-medium">{servicio} no disponible</p>
      <p className="max-w-md text-texto-suave">
        {descripcion ?? 'El servicio no responde en este momento. El resto del portal sigue funcionando.'}
      </p>
      {alReintentar && (
        <Button variant="outline" size="sm" className="mt-2" onClick={alReintentar}>
          <RefreshCw aria-hidden />
          Reintentar
        </Button>
      )}
    </div>
  )
}
