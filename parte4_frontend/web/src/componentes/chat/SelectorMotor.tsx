/**
 * Selector del motor de chat (`GET /api/chat/motores`): un control segmentado con el nombre y el modelo de
 * cada motor; los que no están disponibles (Ollama caído, RAG sin instalar) se muestran deshabilitados con
 * el chip «no disponible».
 */
import type { Motor } from '@/api/tipos'
import { Badge } from '@/componentes/ui/badge'
import { cn } from '@/lib/utils'

interface Props {
  motores: Motor[]
  elegido: Motor['id'] | null
  alElegir: (motor: Motor['id']) => void
  deshabilitado?: boolean
}

export function SelectorMotor({ motores, elegido, alElegir, deshabilitado = false }: Props) {
  return (
    <div role="radiogroup" aria-label="Motor del asistente" className="inline-flex rounded-lg border bg-superficie p-0.5">
      {motores.map((motor) => {
        const activo = motor.id === elegido
        return (
          <button
            key={motor.id}
            type="button"
            role="radio"
            aria-checked={activo}
            disabled={deshabilitado || !motor.disponible}
            title={motor.descripcion}
            onClick={() => alElegir(motor.id)}
            className={cn(
              'flex min-w-36 flex-col items-start rounded-md px-3 py-1.5 text-left transition-colors',
              'focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring',
              'disabled:cursor-not-allowed disabled:opacity-60',
              activo ? 'bg-primario text-white shadow-sm' : 'text-foreground hover:bg-muted',
            )}
          >
            <span className="flex items-center gap-2 text-[13px] font-semibold">
              {motor.nombre}
              {!motor.disponible && (
                <Badge variant="outline" className={cn('h-4 px-1.5 text-[10px] font-medium', activo ? 'border-white/40 text-white' : 'text-aviso')}>
                  no disponible
                </Badge>
              )}
            </span>
            <span className={cn('font-mono text-[11px]', activo ? 'text-white/75' : 'text-texto-suave')}>{motor.modelo || '—'}</span>
          </button>
        )
      })}
    </div>
  )
}
