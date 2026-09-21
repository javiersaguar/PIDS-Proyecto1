/**
 * «Fuentes (n)»: los documentos que el motor RAG ha usado para responder (`EventoRespuesta.fuentes`).
 */
import { FileText } from 'lucide-react'

import type { EventoRespuesta } from '@/api/tipos'
import { Badge } from '@/componentes/ui/badge'

import { Desplegable } from './Desplegable'

interface Props {
  fuentes: EventoRespuesta['fuentes']
}

export function Fuentes({ fuentes }: Props) {
  if (!fuentes?.length) return null
  return (
    <Desplegable titulo={`Fuentes (${fuentes.length})`}>
      <ul className="space-y-1 border-l-2 border-borde pl-3" aria-label="Fuentes consultadas">
        {fuentes.map((fuente, indice) => (
          <li key={`${fuente.fuente}-${indice}`} className="flex flex-wrap items-center gap-x-2 gap-y-0.5 rounded-md bg-superficie-alterna/60 px-2 py-1.5">
            <FileText className="size-3 text-texto-suave" aria-hidden />
            <span className="font-medium text-foreground">{fuente.titulo || fuente.fuente}</span>
            {fuente.titulo && <span className="truncate font-mono text-[11px] text-texto-suave">{fuente.fuente}</span>}
            {fuente.tipo && (
              <Badge variant="outline" className="h-4 px-1.5 text-[10px]">
                {fuente.tipo}
              </Badge>
            )}
          </li>
        ))}
      </ul>
    </Desplegable>
  )
}
