/**
 * Tarjeta de indicador (KPI): título pequeño, cifra grande y una línea de contexto. Admite un estado
 * (`ok`, `aviso`, `peligro`) que colorea la cifra, y un pie libre (chips, semáforo, enlaces).
 */
import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

import { Card, CardContent } from '@/componentes/ui/card'
import { Skeleton } from '@/componentes/ui/skeleton'
import { cn } from '@/lib/utils'

export type EstadoKpi = 'ok' | 'aviso' | 'peligro' | 'neutro'

const COLOR_ESTADO: Record<EstadoKpi, string> = {
  ok: 'text-ok',
  aviso: 'text-aviso',
  peligro: 'text-peligro',
  neutro: 'text-primario',
}

interface Props {
  titulo: string
  /** La cifra o el contenido principal; si es texto o número se pinta grande y con dígitos tabulares. */
  valor?: ReactNode
  /** Línea de contexto bajo la cifra (fecha del dato, fuente…). */
  descripcion?: ReactNode
  icono?: LucideIcon
  estado?: EstadoKpi
  /** Contenido libre al pie (chips, semáforo…). */
  pie?: ReactNode
  /** Sustituye el contenido por un skeleton. */
  cargando?: boolean
  className?: string
}

export function TarjetaKpi({ titulo, valor, descripcion, icono: Icono, estado = 'neutro', pie, cargando, className }: Props) {
  const valorSimple = typeof valor === 'string' || typeof valor === 'number'
  return (
    <Card size="sm" className={cn('sombra-tarjeta', className)}>
      <CardContent className="flex h-full flex-col gap-2">
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs font-medium tracking-wide text-texto-suave uppercase">{titulo}</p>
          {Icono && <Icono className="size-4 shrink-0 text-texto-suave" aria-hidden />}
        </div>
        {cargando ? (
          <div className="space-y-2" role="status" aria-label={`Cargando ${titulo}`}>
            <Skeleton className="h-8 w-2/5" />
            <Skeleton className="h-3.5 w-3/5" />
          </div>
        ) : (
          <>
            {valor !== undefined &&
              (valorSimple ? (
                <p className={cn('cifra text-2xl leading-tight font-semibold', COLOR_ESTADO[estado])}>{valor}</p>
              ) : (
                <div className="min-w-0">{valor}</div>
              ))}
            {descripcion && <p className="text-xs text-texto-suave">{descripcion}</p>}
            {pie && <div className="mt-auto pt-1">{pie}</div>}
          </>
        )}
      </CardContent>
    </Card>
  )
}
