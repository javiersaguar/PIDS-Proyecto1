/**
 * Asistente (§6): chat con el agente de la parte 3 a través del BFF.
 * Lienzo limpio: pregunta, caja de texto y tres ejemplos. El hilo aparece al escribir.
 */
import { BarChart3, CircleDollarSign, MapPin, MessageSquarePlus, type LucideIcon } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { useMotores } from '@/api/chat'
import type { Motor } from '@/api/tipos'
import { Burbuja } from '@/componentes/chat/Burbuja'
import { EntradaMensaje } from '@/componentes/chat/EntradaMensaje'
import { esAsistente } from '@/componentes/chat/tipos'
import { SelectorMotor } from '@/componentes/chat/SelectorMotor'
import { useConversacion } from '@/componentes/chat/useConversacion'
import { EstadoCargando, EstadoError, EstadoNoDisponible } from '@/componentes/shell'
import { Button } from '@/componentes/ui/button'

/** Las tres preguntas de ejemplo de `parte3_chatbot/prompts.py` (BIENVENIDA). */
const SUGERENCIAS: { icono: LucideIcon; titulo: string; texto: string }[] = [
  {
    icono: BarChart3,
    titulo: 'Volumen de viajes',
    texto: '¿Cuántos viajes salieron de JFK el 15 de enero entre las 8 y las 12?',
  },
  {
    icono: MapPin,
    titulo: 'Barrio con más viajes',
    texto: '¿Qué barrio tuvo más viajes el 3 de marzo?',
  },
  {
    icono: CircleDollarSign,
    titulo: 'Propinas',
    texto: '¿Cuál fue la propina media en Manhattan la primera semana de febrero?',
  },
]

const AVISO = 'Solo agregados: no puedo darte información de viajes o personas concretas.'

function Casillas({ alElegir, deshabilitada }: { alElegir: (texto: string) => void; deshabilitada: boolean }) {
  return (
    <ul className="mt-4 grid gap-3 sm:grid-cols-3" aria-label="Preguntas de ejemplo">
      {SUGERENCIAS.map(({ icono: Icono, titulo, texto }) => (
        <li key={texto}>
          <button
            type="button"
            onClick={() => alElegir(texto)}
            disabled={deshabilitada}
            className="flex h-full w-full flex-col items-start gap-3 rounded-2xl border border-[#eceaf3] bg-white p-4 text-left shadow-[0_10px_28px_-18px_rgba(15,23,42,0.35)] transition hover:border-[#ddd6fe] disabled:cursor-not-allowed disabled:opacity-60"
          >
            <span className="flex size-9 items-center justify-center rounded-xl bg-[#efe9ff] text-[#6d4aff]" aria-hidden>
              <Icono className="size-4" />
            </span>
            <span>
              <span className="block text-sm font-semibold text-slate-900">{titulo}</span>
              <span className="mt-1 block text-[13px] leading-snug text-slate-500">{texto}</span>
            </span>
          </button>
        </li>
      ))}
    </ul>
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
  const hayMensajes = conversacion.mensajes.length > 0

  const compositor = (
    <EntradaMensaje
      alEnviar={conversacion.enviar}
      alDetener={conversacion.detener}
      enCurso={conversacion.enCurso}
      deshabilitada={!puedeEscribir}
      motivo={motivoBloqueo}
      complemento={
        <SelectorMotor motores={listaMotores} elegido={motor} alElegir={cambiarMotor} deshabilitado={conversacion.enCurso} />
      }
    />
  )

  let cuerpo
  if (motores.isPending) {
    cuerpo = (
      <div className="flex flex-1 items-center justify-center px-6">
        <EstadoCargando variante="tarjeta" lineas={4} etiqueta="Cargando los motores del asistente…" />
      </div>
    )
  } else if (motores.isError) {
    cuerpo = (
      <div className="flex flex-1 items-center justify-center px-6">
        <EstadoError
          titulo="No se han podido cargar los motores del asistente"
          error={motores.error}
          alReintentar={() => void motores.refetch()}
          reintentando={motores.isFetching}
        />
      </div>
    )
  } else if (!motor) {
    cuerpo = (
      <div className="flex flex-1 items-center justify-center px-6">
        <EstadoNoDisponible
          servicio="Asistente"
          descripcion="Ningún motor de chat responde ahora mismo (Ollama o RAG). El explorador sigue disponible para consultar los agregados."
          alReintentar={() => void motores.refetch()}
        />
      </div>
    )
  } else {
    cuerpo = (
      <div className={hayMensajes ? 'flex min-h-0 flex-1 flex-col overflow-hidden' : 'flex min-h-0 flex-1 flex-col overflow-y-auto'}>
        <div className={hayMensajes ? 'hidden' : 'flex-1'} />
        <div
          ref={hayMensajes ? hiloRef : undefined}
          role={hayMensajes ? 'log' : undefined}
          aria-live={hayMensajes ? 'polite' : undefined}
          aria-relevant={hayMensajes ? 'additions text' : undefined}
          aria-label={hayMensajes ? 'Conversación con el asistente' : undefined}
          className={hayMensajes ? 'min-h-0 flex-1 overflow-y-auto px-6 py-6' : 'px-6'}
        >
          {hayMensajes ? (
            <div className="mx-auto w-full max-w-3xl space-y-4">
              {conversacion.mensajes.map((mensaje) => (
                <Burbuja
                  key={mensaje.id}
                  mensaje={mensaje}
                  esUltimo={mensaje.id === ultimoAsistente?.id}
                  ocupado={conversacion.enCurso}
                  alAceptarAlternativa={conversacion.aceptarAlternativa}
                  alCancelarAlternativa={conversacion.cancelarAlternativa}
                />
              ))}
            </div>
          ) : (
            <div className="mx-auto mb-8 w-full max-w-3xl text-center">
              <h2 className="text-[2rem] leading-tight font-semibold tracking-tight text-slate-900">¿Qué quieres saber hoy?</h2>
              <p className="mx-auto mt-3 max-w-xl text-[15px] leading-relaxed text-slate-500">
                Pregunta por volúmenes de viajes, importes, propinas o flujos entre barrios de Nueva York en 2020.
              </p>
              <p className="mx-auto mt-2 max-w-xl text-sm text-slate-400">{AVISO}</p>
            </div>
          )}
        </div>
        <div className="mx-auto w-full max-w-3xl px-6 pb-6">
          {conversacion.errorSesion && !hayMensajes ? (
            <EstadoError
              titulo="No se ha podido abrir la sesión con el asistente"
              error={conversacion.errorSesion}
              alReintentar={conversacion.reintentarSesion}
            />
          ) : (
            compositor
          )}
          {!hayMensajes && !conversacion.errorSesion && (
            <Casillas alElegir={conversacion.enviar} deshabilitada={!puedeEscribir} />
          )}
        </div>
        <div className={hayMensajes ? 'hidden' : 'flex-1'} />
      </div>
    )
  }

  return (
    <div className="relative flex h-full min-h-0 flex-col bg-[radial-gradient(ellipse_at_top,#f3eefc_0%,#f8f7fc_38%,#ffffff_72%)]">
      <h1 className="sr-only">Asistente</h1>
      {motor && (
        <div className="absolute top-4 right-6 z-10">
          <Button variant="ghost" size="sm" className="text-slate-500" onClick={conversacion.reiniciar}>
            <MessageSquarePlus aria-hidden />
            Nueva conversación
          </Button>
        </div>
      )}
      {cuerpo}
    </div>
  )
}
