/**
 * Cuadro de texto del asistente: Enter envía, Shift+Enter hace un salto de línea; crece hasta seis líneas.
 * Mientras hay una respuesta en curso se deshabilita y el botón pasa a «Detener».
 */
import { LoaderCircle, SendHorizontal, Square } from 'lucide-react'
import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react'

import { Button } from '@/componentes/ui/button'
import { Label } from '@/componentes/ui/label'

interface Props {
  alEnviar: (texto: string) => void
  alDetener?: () => void
  enCurso: boolean
  deshabilitada?: boolean
  /** Motivo por el que no se puede escribir (sesión creándose, motor caído…). */
  motivo?: string | null
  autoFoco?: boolean
}

const ALTURA_MAXIMA = 160

export function EntradaMensaje({ alEnviar, alDetener, enCurso, deshabilitada = false, motivo, autoFoco = false }: Props) {
  const [texto, setTexto] = useState('')
  const areaRef = useRef<HTMLTextAreaElement>(null)
  const idAyuda = useId()
  const bloqueada = deshabilitada || enCurso

  // Altura automática del área de texto según el contenido.
  useEffect(() => {
    const area = areaRef.current
    if (!area) return
    area.style.height = 'auto'
    area.style.height = `${Math.min(area.scrollHeight, ALTURA_MAXIMA)}px`
  }, [texto])

  const enviar = () => {
    const limpio = texto.trim()
    if (!limpio || bloqueada) return
    alEnviar(limpio)
    setTexto('')
    areaRef.current?.focus()
  }

  const alTeclear = (evento: KeyboardEvent<HTMLTextAreaElement>) => {
    if (evento.key === 'Enter' && !evento.shiftKey && !evento.nativeEvent.isComposing) {
      evento.preventDefault()
      enviar()
    }
  }

  return (
    <form
      className="flex items-end gap-2"
      onSubmit={(evento) => {
        evento.preventDefault()
        enviar()
      }}
    >
      <div className="min-w-0 flex-1">
        <Label htmlFor={`${idAyuda}-texto`} className="sr-only">
          Mensaje para el asistente
        </Label>
        <textarea
          id={`${idAyuda}-texto`}
          ref={areaRef}
          value={texto}
          onChange={(evento) => setTexto(evento.target.value)}
          onKeyDown={alTeclear}
          rows={1}
          autoFocus={autoFoco}
          disabled={bloqueada}
          placeholder={motivo ?? 'Escribe tu pregunta sobre los agregados (Enter envía, Shift+Enter salto de línea)'}
          aria-describedby={idAyuda}
          className="block max-h-40 w-full resize-none rounded-lg border border-input bg-superficie px-3 py-2 text-sm leading-relaxed outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-60"
        />
        <p id={idAyuda} className="sr-only">
          Enter envía el mensaje; Shift+Enter añade un salto de línea.
        </p>
      </div>
      {enCurso && alDetener ? (
        <Button type="button" variant="outline" onClick={alDetener} aria-label="Detener la respuesta">
          <Square aria-hidden />
          Detener
        </Button>
      ) : (
        <Button type="submit" disabled={bloqueada || !texto.trim()} aria-label="Enviar el mensaje">
          {enCurso ? <LoaderCircle className="animate-spin" aria-hidden /> : <SendHorizontal aria-hidden />}
          Enviar
        </Button>
      )}
    </form>
  )
}
