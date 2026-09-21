/**
 * «Pasos»: las herramientas que el agente ha ejecutado en el turno (eventos `paso` del SSE), en directo.
 * Mientras la respuesta está en curso el desplegable se abre solo y muestra el paso en ejecución; al terminar
 * se pliega, salvo que el usuario lo haya tocado (igual que los pasos de Chainlit).
 */
import { LoaderCircle, Wrench } from 'lucide-react'
import { useState } from 'react'

import type { EventoPaso } from '@/api/tipos'

import { Desplegable } from './Desplegable'
import { abreviar, argumentosEnLinea, formatearSegundos, jsonLegible } from './formato'

interface Props {
  pasos: EventoPaso[]
  enCurso: boolean
}

export function Pasos({ pasos, enCurso }: Props) {
  const [manual, setManual] = useState<boolean | null>(null)
  if (pasos.length === 0 && !enCurso) return null
  const abierto = manual ?? enCurso
  const ultimo = pasos.at(-1)

  return (
    <Desplegable
      titulo={`Pasos (${pasos.length})`}
      abierto={abierto}
      alCambiar={setManual}
      extra={
        enCurso && (
          <span className="inline-flex items-center gap-1 text-texto-suave">
            <LoaderCircle className="size-3 animate-spin" aria-hidden />
            {ultimo ? `${ultimo.nombre} terminado, pensando…` : 'consultando…'}
          </span>
        )
      }
    >
      {pasos.length === 0 ? (
        <p className="pl-5 text-texto-suave">Todavía no se ha ejecutado ninguna herramienta.</p>
      ) : (
        <ol className="space-y-1 border-l-2 border-borde pl-3" aria-label="Herramientas ejecutadas">
          {pasos.map((paso, indice) => (
            <li key={`${paso.nombre}-${indice}`} className="rounded-md bg-superficie-alterna/60 px-2 py-1.5">
              <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                <Wrench className="size-3 text-texto-suave" aria-hidden />
                <code className="rounded bg-superficie px-1 py-0.5 font-mono text-[11.5px] font-medium text-primario">{paso.nombre}</code>
                <span className="min-w-0 flex-1 truncate text-texto-suave" title={argumentosEnLinea(paso.argumentos)}>
                  {abreviar(argumentosEnLinea(paso.argumentos), 110) || 'sin argumentos'}
                </span>
                <span className="cifra shrink-0 text-texto-suave">{formatearSegundos(paso.segundos)}</span>
              </div>
              {paso.resultado && (
                <details className="mt-1">
                  <summary className="cursor-pointer text-texto-suave hover:text-foreground">Resultado</summary>
                  <pre className="mt-1 max-h-56 overflow-auto rounded bg-superficie p-2 font-mono text-[11px] leading-relaxed whitespace-pre-wrap">
                    {jsonLegible(paso.resultado)}
                  </pre>
                </details>
              )}
            </li>
          ))}
        </ol>
      )}
    </Desplegable>
  )
}
