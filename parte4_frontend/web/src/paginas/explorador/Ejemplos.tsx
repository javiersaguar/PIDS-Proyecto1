/**
 * Ejemplos rápidos (chips): rellenan el formulario y lanzan la consulta.
 */
import { Sparkles } from 'lucide-react'

import type { Consulta } from '@/api/tipos'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/componentes/ui/tooltip'

import { EJEMPLOS } from './consulta'

interface Props {
  onElegir: (consulta: Consulta) => void
  disabled?: boolean
}

export function Ejemplos({ onElegir, disabled }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="flex items-center gap-1.5 text-xs font-medium text-texto-suave">
        <Sparkles className="size-3.5 text-acento" aria-hidden />
        Ejemplos
      </span>
      <ul className="flex flex-wrap gap-1.5" aria-label="Ejemplos rápidos">
        {EJEMPLOS.map((ejemplo) => (
          <li key={ejemplo.titulo}>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => onElegir(ejemplo.consulta)}
                  className="inline-flex h-7 items-center rounded-full border bg-superficie px-3 text-xs font-medium transition-colors hover:border-primario/40 hover:bg-muted disabled:opacity-50"
                >
                  {ejemplo.titulo}
                </button>
              </TooltipTrigger>
              <TooltipContent>{ejemplo.descripcion}</TooltipContent>
            </Tooltip>
          </li>
        ))}
      </ul>
    </div>
  )
}
