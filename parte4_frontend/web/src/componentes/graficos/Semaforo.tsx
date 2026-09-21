/**
 * Punto de color con texto: verde (ok), ámbar (aviso) o rojo (peligro). Se usa para la frescura del tiempo
 * real y para el estado de los servicios.
 */
import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

import { TEXTO_FRESCURA, type NivelFrescura } from './frescura'

const COLOR: Record<NivelFrescura, string> = {
  ok: 'bg-ok',
  aviso: 'bg-aviso',
  peligro: 'bg-peligro',
}

const TEXTO_COLOR: Record<NivelFrescura, string> = {
  ok: 'text-ok',
  aviso: 'text-aviso',
  peligro: 'text-peligro',
}

interface Props {
  nivel: NivelFrescura
  /** Texto junto al punto; por defecto, el del nivel («al día», «con retraso», «sin datos recientes»). */
  etiqueta?: ReactNode
  /** Descripción para lectores de pantalla (si la etiqueta no lo dice ya). */
  descripcion?: string
  tamano?: 'sm' | 'md' | 'lg'
  /** El punto late (para indicar que el dato se está refrescando). */
  pulso?: boolean
  className?: string
}

const TAMANO_PUNTO: Record<NonNullable<Props['tamano']>, string> = { sm: 'size-2', md: 'size-2.5', lg: 'size-3' }

export function Semaforo({ nivel, etiqueta, descripcion, tamano = 'md', pulso = false, className }: Props) {
  const texto = etiqueta ?? TEXTO_FRESCURA[nivel]
  return (
    <span className={cn('inline-flex items-center gap-2', className)}>
      <span
        role="img"
        aria-label={descripcion ?? `Estado: ${TEXTO_FRESCURA[nivel]}`}
        className={cn('relative inline-flex shrink-0 rounded-full', TAMANO_PUNTO[tamano], COLOR[nivel])}
      >
        {pulso && <span className={cn('absolute inset-0 animate-ping rounded-full opacity-60', COLOR[nivel])} aria-hidden />}
      </span>
      {texto !== null && <span className={cn('font-medium', TEXTO_COLOR[nivel])}>{texto}</span>}
    </span>
  )
}
