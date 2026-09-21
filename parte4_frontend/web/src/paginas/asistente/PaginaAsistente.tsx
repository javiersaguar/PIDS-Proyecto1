/**
 * Asistente (§6): chat con el agente de la parte 3 a través del BFF. Selector de motor (Ollama / RAG), hilo con
 * Markdown, pasos de las herramientas en directo (SSE), botón de alternativa tras un rechazo, fuentes y
 * segundos/tokens por turno. Réplica en el portal de la interfaz Chainlit (`parte3_chatbot/app.py`).
 */
import { Bot, Lock, MessageSquarePlus, Sparkles } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { useMotores } from '@/api/chat'
import type { Motor } from '@/api/tipos'
import { Burbuja } from '@/componentes/chat/Burbuja'
import { EntradaMensaje } from '@/componentes/chat/EntradaMensaje'
import { esAsistente } from '@/componentes/chat/tipos'
import { SelectorMotor } from '@/componentes/chat/SelectorMotor'
import { useConversacion } from '@/componentes/chat/useConversacion'
import { EncabezadoPagina, EstadoCargando, EstadoError, EstadoNoDisponible } from '@/componentes/shell'
import { Button } from '@/componentes/ui/button'
import { Card } from '@/componentes/ui/card'

/** Las tres preguntas de ejemplo de `parte3_chatbot/prompts.py` (BIENVENIDA). */
const SUGERENCIAS = [
  '¿Cuántos viajes salieron de JFK el 15 de enero entre las 8 y las 12?',
  '¿Qué barrio tuvo más viajes el 3 de marzo?',
  '¿Cuál fue la propina media en Manhattan la primera semana de febrero?',
]

const AVISO = 'Solo agregados: no puedo darte información de viajes o personas concretas.'

function Bienvenida({ alElegir, deshabilitada }: { alElegir: (texto: string) => void; deshabilitada: boolean }) {
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center gap-4 py-8 text-center">
      <span className="flex size-11 items-center justify-center rounded-full bg-acento text-primario" aria-hidden>
        <Bot className="size-6" />
      </span>
      <div className="space-y-1">
        <h2 className="text-lg">Asistente de datos de taxis (NYC, 2020)</h2>
        <p className="text-texto-suave">
          Pregúntame por volúmenes de viajes, importes medios, propinas o flujos entre barrios. Por ejemplo:
        </p>
      </div>
      <ul className="grid w-full gap-2 text-left" aria-label="Preguntas de ejemplo">
        {SUGERENCIAS.map((sugerencia) => (
          <li key={sugerencia}>
            <button
              type="button"
              onClick={() => alElegir(sugerencia)}
              disabled={deshabilitada}
              className="flex w-full items-center gap-2.5 rounded-lg border bg-superficie px-3 py-2 text-left text-sm transition-colors hover:border-acento hover:bg-acento-suave/50 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Sparkles className="size-4 shrink-0 text-acento" aria-hidden />
              <span>{sugerencia}</span>
            </button>
          </li>
        ))}
      </ul>
      <p className="text-xs text-texto-suave">{AVISO}</p>
    </div>
  )
}

export default function PaginaAsistente() {
  const motores = useMotores()
  const [motorElegido, setMotorElegido] = useState<Motor['id'] | null>(null)
  const listaMotores = motores.data ?? []
  const elegidoDisponible = listaMotores.some((m) => m.id === motorElegido && m.disponible) ? motorElegido : null
  const motor = elegidoDisponible ?? listaMotores.find((m) => m.disponible)?.id ?? null
  const conversacion = useConversacion(motor)
  const hiloRef = useRef<HTMLDivElement>(null)

  // El hilo se mantiene pegado al final según llegan mensajes y pasos.
  useEffect(() => {
    const hilo = hiloRef.current
    if (hilo) hilo.scrollTop = hilo.scrollHeight
  }, [conversacion.mensajes])

  const cambiarMotor = (id: Motor['id']) => {
    if (id === motor) return
    setMotorElegido(id)
    conversacion.reiniciar()
  }

  const ultimoAsistente = conversacion.mensajes.filter(esAsistente).at(-1)
  const puedeEscribir = conversacion.sesion !== null && !conversacion.creandoSesion
  const motivoBloqueo = conversacion.creandoSesion
    ? 'Abriendo la sesión con el asistente…'
    : conversacion.errorSesion
      ? 'No se ha podido abrir la sesión con el asistente'
      : null

  let contenido
  if (motores.isPending) {
    contenido = <EstadoCargando variante="tarjeta" lineas={5} etiqueta="Cargando los motores del asistente…" />
  } else if (motores.isError) {
    contenido = (
      <EstadoError
        titulo="No se han podido cargar los motores del asistente"
        error={motores.error}
        alReintentar={() => void motores.refetch()}
        reintentando={motores.isFetching}
      />
    )
  } else if (!motor) {
    contenido = (
      <EstadoNoDisponible
        servicio="Asistente"
        descripcion="Ningún motor de chat responde ahora mismo (Ollama o RAG). El explorador sigue disponible para consultar los agregados."
        alReintentar={() => void motores.refetch()}
      />
    )
  } else {
    contenido = (
      <Card className="flex h-[calc(100svh-16rem)] min-h-[480px] flex-col gap-0 overflow-hidden py-0">
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b bg-superficie-alterna/60 px-4 py-2">
          <p className="flex items-center gap-2 text-xs text-texto-suave">
            <Lock className="size-3.5 shrink-0 text-enmascarado" aria-hidden />
            <span>
              <span className="font-medium text-foreground">Solo agregados:</span> no puedo darte información de viajes o personas
              concretas.
            </span>
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <SelectorMotor motores={listaMotores} elegido={motor} alElegir={cambiarMotor} deshabilitado={conversacion.enCurso} />
            <Button variant="outline" size="sm" onClick={conversacion.reiniciar} disabled={!motor}>
              <MessageSquarePlus aria-hidden />
              Nueva conversación
            </Button>
          </div>
        </div>

        <div
          ref={hiloRef}
          role="log"
          aria-live="polite"
          aria-relevant="additions text"
          aria-label="Conversación con el asistente"
          className="flex-1 space-y-4 overflow-y-auto px-4 py-4"
        >
          {conversacion.errorSesion ? (
            <EstadoError
              titulo="No se ha podido abrir la sesión con el asistente"
              error={conversacion.errorSesion}
              alReintentar={conversacion.reintentarSesion}
            />
          ) : conversacion.mensajes.length === 0 ? (
            <Bienvenida alElegir={conversacion.enviar} deshabilitada={!puedeEscribir} />
          ) : (
            conversacion.mensajes.map((mensaje) => (
              <Burbuja
                key={mensaje.id}
                mensaje={mensaje}
                esUltimo={mensaje.id === ultimoAsistente?.id}
                ocupado={conversacion.enCurso}
                alAceptarAlternativa={conversacion.aceptarAlternativa}
                alCancelarAlternativa={conversacion.cancelarAlternativa}
              />
            ))
          )}
        </div>

        <div className="border-t bg-superficie px-4 py-3">
          <EntradaMensaje
            alEnviar={conversacion.enviar}
            alDetener={conversacion.detener}
            enCurso={conversacion.enCurso}
            deshabilitada={!puedeEscribir}
            motivo={motivoBloqueo}
          />
        </div>
      </Card>
    )
  }

  return (
    <>
      <EncabezadoPagina
        titulo="Asistente"
        descripcion="Conversación con el agente sobre los agregados publicados, con los pasos de las herramientas en directo."
      />
      {contenido}
    </>
  )
}
