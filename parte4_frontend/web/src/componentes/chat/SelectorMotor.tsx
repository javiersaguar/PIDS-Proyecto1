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
    <div role="radiogroup" aria-label="Motor del asistente" className="inline-flex flex-wrap items-center gap-1">
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
              'inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-left text-xs transition-colors',
              'focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring',
              'disabled:cursor-not-allowed disabled:opacity-50',
              activo ? 'bg-[#f3eefe] font-medium text-[#5b21b6]' : 'text-slate-500 hover:bg-slate-50 hover:text-slate-800',
            )}
          >
            <span>{motor.nombre}</span>
            <span className={cn('font-mono text-[11px]', activo ? 'text-[#7c3aed]' : 'text-slate-400')}>{motor.modelo || '—'}</span>
            {!motor.disponible && (
              <Badge variant="outline" className="h-4 px-1.5 text-[10px] font-medium text-aviso">
                no disponible
              </Badge>
            )}
          </button>
        )
      })}
    </div>
  )
}
