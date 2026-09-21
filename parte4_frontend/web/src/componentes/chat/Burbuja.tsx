/**
 * Un mensaje del hilo. El del usuario va a la derecha (marino); el del asistente, a la izquierda, con el
 * Markdown, los pasos en directo, las fuentes, la línea de segundos/tokens y, tras un rechazo con
 * alternativa, los botones «✅ Consultar la alternativa» / «✖ Cancelar» (los mismos que Chainlit).
 */
import { Bot, Lock, TriangleAlert, User } from 'lucide-react'

import { Button } from '@/componentes/ui/button'
import { cn } from '@/lib/utils'

import { formatearNumero, formatearSegundos } from './formato'
import { Fuentes } from './Fuentes'
import { Markdown } from './Markdown'
import { Pasos } from './Pasos'
import { esRechazo, TEXTO_BLOQUEO, type MensajeAsistente, type MensajeChat } from './tipos'

interface Props {
  mensaje: MensajeChat
  /** Es la última respuesta del hilo: solo ahí se ofrecen los botones de la alternativa. */
  esUltimo: boolean
  /** Hay otra respuesta en curso (los botones se deshabilitan). */
  ocupado: boolean
  alAceptarAlternativa: (idMensaje: string) => void
  alCancelarAlternativa: (idMensaje: string) => void
}

export function Burbuja({ mensaje, esUltimo, ocupado, alAceptarAlternativa, alCancelarAlternativa }: Props) {
  if (mensaje.rol === 'usuario') {
    return (
      <article className="flex justify-end gap-3" aria-label="Mensaje del usuario">
        <div className="max-w-[75%] rounded-xl rounded-tr-sm bg-primario px-4 py-2.5 text-[14px] leading-relaxed text-white whitespace-pre-wrap wrap-break-word">
          {mensaje.texto}
        </div>
        <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-superficie-alterna text-primario" aria-hidden>
          <User className="size-4" />
        </span>
      </article>
    )
  }
  return (
    <BurbujaAsistente
      mensaje={mensaje}
      esUltimo={esUltimo}
      ocupado={ocupado}
      alAceptarAlternativa={alAceptarAlternativa}
      alCancelarAlternativa={alCancelarAlternativa}
    />
  )
}

function IndicadorEscribiendo({ texto }: { texto: string }) {
  return (
    <div className="flex items-center gap-2 text-texto-suave" role="status" aria-label={texto}>
      <span className="flex items-center gap-1" aria-hidden>
        <span className="size-1.5 animate-bounce rounded-full bg-texto-suave [animation-delay:-0.3s]" />
        <span className="size-1.5 animate-bounce rounded-full bg-texto-suave [animation-delay:-0.15s]" />
        <span className="size-1.5 animate-bounce rounded-full bg-texto-suave" />
      </span>
      <span className="text-xs">{texto}</span>
    </div>
  )
}

function BurbujaAsistente({
  mensaje,
  esUltimo,
  ocupado,
  alAceptarAlternativa,
  alCancelarAlternativa,
}: Omit<Props, 'mensaje'> & { mensaje: MensajeAsistente }) {
  const { respuesta } = mensaje
  const rechazo = esRechazo(mensaje)
  const alternativaPendiente = !!respuesta?.alternativa && !mensaje.alternativaResuelta && esUltimo
  const textoEscribiendo = mensaje.pasos.length ? 'Preparando la respuesta…' : 'El asistente está pensando…'
  const bloqueo = respuesta?.bloqueo ? TEXTO_BLOQUEO[respuesta.bloqueo] ?? respuesta.bloqueo : null

  return (
    <article className="flex gap-3" aria-label="Mensaje del asistente" aria-busy={mensaje.enCurso || undefined}>
      <span
        className={cn(
          'mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full text-primario',
          mensaje.local ? 'bg-superficie-alterna' : 'bg-acento-suave text-acento',
        )}
        aria-hidden
      >
        <Bot className="size-4" />
      </span>
      <div className="min-w-0 max-w-[85%] flex-1 space-y-1.5">
        <div
          className={cn(
            'rounded-xl rounded-tl-sm border bg-superficie px-4 py-3 text-[14px] sombra-tarjeta',
            rechazo && 'border-aviso/40 bg-aviso/5',
            mensaje.error && !mensaje.texto && 'border-peligro/30 bg-peligro/5',
            mensaje.local && 'border-dashed bg-transparent shadow-none',
          )}
        >
          {rechazo && (
            <p className="mb-2 inline-flex items-center gap-1.5 rounded-md bg-aviso/10 px-2 py-0.5 text-xs font-medium text-aviso">
              <Lock className="size-3" aria-hidden />
              Filtro de privacidad
            </p>
          )}
          {mensaje.texto ? (
            <Markdown texto={mensaje.texto} />
          ) : mensaje.enCurso ? (
            <IndicadorEscribiendo texto={textoEscribiendo} />
          ) : null}
          {mensaje.error && (
            <p role="alert" className={cn('flex items-start gap-2 text-peligro', mensaje.texto && 'mt-2 border-t pt-2')}>
              <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
              <span>{mensaje.error}</span>
            </p>
          )}
        </div>

        <Pasos pasos={mensaje.pasos} enCurso={mensaje.enCurso} />
        {respuesta && <Fuentes fuentes={respuesta.fuentes} />}

        {respuesta && (
          <p className="cifra flex flex-wrap items-center gap-x-2 text-xs text-texto-suave">
            <span>{formatearSegundos(respuesta.segundos)}</span>
            {respuesta.tokens !== null && respuesta.tokens !== undefined && (
              <>
                <span aria-hidden>·</span>
                <span>{formatearNumero(respuesta.tokens)} tokens</span>
              </>
            )}
            {respuesta.pasos_llm > 0 && (
              <>
                <span aria-hidden>·</span>
                <span>
                  {respuesta.pasos_llm} {respuesta.pasos_llm === 1 ? 'llamada' : 'llamadas'} al modelo
                </span>
              </>
            )}
            {bloqueo && (
              <>
                <span aria-hidden>·</span>
                <span className="text-aviso">{bloqueo}</span>
              </>
            )}
          </p>
        )}

        {respuesta?.alternativa && (
          <div className={cn('rounded-lg border px-3 py-2 text-xs', alternativaPendiente ? 'border-acento/60 bg-acento-suave/60' : 'border-dashed')}>
            <p className="text-foreground">
              <span className="font-medium">Alternativa agregada:</span>{' '}
              <span className="italic">{respuesta.alternativa_descripcion ?? 'la consulta más cercana que sí respeta las reglas'}</span>
            </p>
            {alternativaPendiente ? (
              <div className="mt-2 flex flex-wrap gap-2">
                <Button size="sm" onClick={() => alAceptarAlternativa(mensaje.id)} disabled={ocupado}>
                  ✅ Consultar la alternativa
                </Button>
                <Button size="sm" variant="outline" onClick={() => alCancelarAlternativa(mensaje.id)} disabled={ocupado}>
                  ✖ Cancelar
                </Button>
              </div>
            ) : (
              <p className="mt-1 text-texto-suave">
                {mensaje.alternativaResuelta === 'aceptada'
                  ? 'Consultada.'
                  : mensaje.alternativaResuelta === 'cancelada'
                    ? 'Descartada.'
                    : 'Ya no está pendiente: ha llegado otro turno.'}
              </p>
            )}
          </div>
        )}
      </div>
    </article>
  )
}
