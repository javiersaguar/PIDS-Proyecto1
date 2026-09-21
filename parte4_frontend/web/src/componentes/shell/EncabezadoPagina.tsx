/**
 * Cabecera de cada página: título, descripción y un hueco para acciones (botones, filtros, refresco).
 */
import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

interface Props {
  titulo: string
  descripcion?: ReactNode
  /** Acciones alineadas a la derecha (botones, selectores…). */
  acciones?: ReactNode
  className?: string
}

export function EncabezadoPagina({ titulo, descripcion, acciones, className }: Props) {
  return (
    <header className={cn('mb-6 flex flex-wrap items-start justify-between gap-4', className)}>
      <div className="min-w-0 space-y-1">
        <h1 className="text-2xl">{titulo}</h1>
        {descripcion && <p className="max-w-3xl text-texto-suave">{descripcion}</p>}
      </div>
      {acciones && <div className="flex shrink-0 flex-wrap items-center gap-2">{acciones}</div>}
    </header>
  )
}
