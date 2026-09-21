/**
 * Cuadro de texto del asistente: Enter envía, Shift+Enter hace un salto de línea; crece hasta seis líneas.
 * Mientras hay una respuesta en curso se deshabilita y el botón pasa a «Detener».
 * `complemento` se pinta a la izquierda del botón (el selector de motor).
 */
import { ArrowUp, LoaderCircle, Square } from 'lucide-react'
import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'

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
  complemento?: ReactNode
}

const ALTURA_MAXIMA = 160

export function EntradaMensaje({
  alEnviar,
  alDetener,
  enCurso,
  deshabilitada = false,
  motivo,
  autoFoco = false,
  complemento,
}: Props) {
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
      className="rounded-2xl border border-[#e7e3f4] bg-white px-4 pt-3 pb-2.5 shadow-[0_12px_40px_-18px_rgba(76,58,140,0.45)] focus-within:border-[#c4b5fd]"
      onSubmit={(evento) => {
        evento.preventDefault()
        enviar()
      }}
    >
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
        placeholder={motivo ?? 'Pregunta lo que quieras…'}
        aria-describedby={idAyuda}
        className="block max-h-40 min-h-10 w-full resize-none bg-transparent px-1 py-1.5 text-[15px] leading-relaxed text-slate-800 outline-none placeholder:text-slate-400 disabled:cursor-not-allowed disabled:opacity-60"
      />
      <p id={idAyuda} className="sr-only">
        Enter envía el mensaje; Shift+Enter añade un salto de línea.
      </p>
      <div className="mt-1 flex items-center justify-between gap-2">
        <div className="min-w-0">{complemento}</div>
        {enCurso && alDetener ? (
          <Button type="button" variant="outline" size="icon" onClick={alDetener} aria-label="Detener la respuesta">
            <Square aria-hidden />
          </Button>
        ) : (
          <Button
            type="submit"
            size="icon-lg"
            disabled={bloqueada || !texto.trim()}
            aria-label="Enviar el mensaje"
            className="rounded-xl bg-[#6d4aff]! text-white! hover:bg-[#5b3ae0]!"
          >
            {enCurso ? <LoaderCircle className="animate-spin" aria-hidden /> : <ArrowUp aria-hidden />}
          </Button>
        )}
      </div>
    </form>
  )
}
