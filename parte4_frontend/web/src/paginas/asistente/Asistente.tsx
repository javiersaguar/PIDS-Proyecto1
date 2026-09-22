/**
 * TAXI AI: el chat con el agente de la parte 3 a través del BFF, tal como se ve dentro del panel derecho
 * (`componentes/shell/PanelAsistente.tsx`). Ya no es una sección del menú: se abre desde cualquier página con el
 * botón «TAXI AI» y al cerrarlo la conversación sigue viva.
 *
 * Cabecera con el motor y «Nueva conversación», hilo de mensajes (o la bienvenida con tres ejemplos) y el cuadro
 * de texto abajo. Todo en una sola columna, pensado para los 30 rem del panel.
 */
import { BarChart3, CircleDollarSign, MapPin, MessageSquarePlus, Sparkles, X, type LucideIcon } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { useMotores } from '@/api/chat'
import type { Motor } from '@/api/tipos'
import { Burbuja } from '@/componentes/chat/Burbuja'
import { EntradaMensaje } from '@/componentes/chat/EntradaMensaje'
import { esAsistente } from '@/componentes/chat/tipos'
import { SelectorMotor } from '@/componentes/chat/SelectorMotor'
import { useConversacion } from '@/componentes/chat/useConversacion'
import { EstadoCargando, EstadoError, EstadoNoDisponible } from '@/componentes/shell/Estados'
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

interface Props {
  /** Cierra el panel (el chat sigue vivo). Sin él no se pinta el botón de cerrar. */
  alCerrar?: () => void
}

function Casillas({ alElegir, deshabilitada }: { alElegir: (texto: string) => void; deshabilitada: boolean }) {
  return (
    <ul className="mt-5 grid gap-2" aria-label="Preguntas de ejemplo">
      {SUGERENCIAS.map(({ icono: Icono, titulo, texto }) => (
        <li key={texto}>
          <button
            type="button"
            onClick={() => alElegir(texto)}
            disabled={deshabilitada}
            className="flex w-full items-start gap-3 rounded-2xl border border-[#eceaf3] bg-white p-3 text-left shadow-[0_10px_28px_-18px_rgba(15,23,42,0.35)] transition hover:border-[#ddd6fe] disabled:cursor-not-allowed disabled:opacity-60"
          >
            <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-[#efe9ff] text-[#6d4aff]" aria-hidden>
              <Icono className="size-4" />
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-semibold text-slate-900">{titulo}</span>
              <span className="mt-0.5 block text-[13px] leading-snug text-slate-500">{texto}</span>
            </span>
          </button>
        </li>
      ))}
    </ul>
  )
}

export function Asistente({ alCerrar }: Props) {
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
      <div className="flex flex-1 items-center justify-center px-5">
        <EstadoCargando variante="tarjeta" lineas={4} etiqueta="Cargando los motores del asistente…" />
      </div>
    )
  } else if (motores.isError) {
    cuerpo = (
      <div className="flex flex-1 items-center justify-center px-5">
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
      <div className="flex flex-1 items-center justify-center px-5">
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
          className={hayMensajes ? 'min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-5' : 'px-5'}
        >
          {hayMensajes ? (
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
          ) : (
            <div className="mb-6 text-center">
              <h3 className="text-2xl leading-tight font-semibold tracking-tight text-slate-900">¿Qué quieres saber hoy?</h3>
              <p className="mx-auto mt-2 max-w-sm text-[15px] leading-relaxed text-slate-500">
                Pregunta por volúmenes de viajes, importes, propinas o flujos entre barrios de Nueva York en 2020.
              </p>
              <p className="mx-auto mt-2 max-w-sm text-sm text-slate-400">{AVISO}</p>
            </div>
          )}
        </div>
        <div className="px-5 pb-5">
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
    <div className="flex h-full min-h-0 flex-col bg-[radial-gradient(ellipse_at_top,#f3eefc_0%,#f8f7fc_38%,#ffffff_72%)]">
      <header className="flex items-center justify-between gap-3 border-b border-[#eceaf3] px-5 py-3.5">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-[#6d4aff] text-white shadow-sm" aria-hidden>
            <Sparkles className="size-4" />
          </span>
          <div className="min-w-0 leading-tight">
            <h2 className="text-[15px] font-semibold tracking-tight text-slate-900">TAXI AI</h2>
            <p className="truncate text-xs text-slate-500">Asistente de datos</p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {motor && (
            <Button variant="ghost" size="sm" className="text-slate-500" onClick={conversacion.reiniciar}>
              <MessageSquarePlus aria-hidden />
              <span className="max-sm:sr-only">Nueva conversación</span>
            </Button>
          )}
          {alCerrar && (
            <Button variant="ghost" size="icon" className="text-slate-500" onClick={alCerrar} aria-label="Cerrar el asistente">
              <X aria-hidden />
            </Button>
          )}
        </div>
      </header>
      {cuerpo}
    </div>
  )
}
