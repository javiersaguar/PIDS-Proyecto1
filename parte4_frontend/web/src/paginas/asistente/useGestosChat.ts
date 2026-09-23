/**
 * Lo que hacen los gestos dentro de TAXI AI (tabla de `config/gestos.json`):
 *   ✌️ siguiente   hace una pregunta al azar (la da el BFF con las plantillas de `config/gestos.json`; en la
 *                  demostración, una de las grabadas). No son las de las casillas de ejemplo.
 *   👍 motor       pasa de Ollama a DeepSeek y al revés (empieza una conversación nueva, como el selector); si el otro
 *                  motor no está disponible, lo dice y no cambia
 *   👌 leer        lee en voz alta la última respuesta; si ya está leyendo, la calla
 * Preguntar y cambiar de motor esperan a que el chat esté libre: el gesto que abre el panel se atiende en cuanto hay
 * sesión, y uno que llega mientras el asistente responde, al terminar. ✋ (secciones), 🤘 y ✊ los atiende el esqueleto
 * de la app (`gestos/AtajosGestos.tsx`).
 */
import { useEffect, useRef } from 'react'
import { toast } from 'sonner'

import { pedirPregunta } from '@/api/gestos'
import { esAsistente } from '@/componentes/chat/tipos'
import type { Conversacion } from '@/componentes/chat/useConversacion'
import { useAlGesto, useGestos, type EventoGesto } from '@/gestos/contexto'
import { GESTOS, PREGUNTAS_GESTO, type Accion } from '@/gestos/tabla'
import { callar, hablando, leerEnVozAlta } from '@/gestos/voz'

const EN_EL_CHAT: ReadonlySet<Accion> = new Set(['siguiente', 'motor', 'leer'])
const INMEDIATAS: ReadonlySet<Accion> = new Set(['leer'])
/** Un gesto que espera al chat caduca pasado este tiempo: no se ejecuta algo que ya nadie recuerda haber pedido. */
const CADUCA_MS = 10_000

// Un gesto no se atiende dos veces aunque el chat se desmonte y se vuelva a montar.
let ultimoAtendido = 0

export function useGestosChat(conversacion: Conversacion, alCambiarMotor: () => void): void {
  const { ultimo } = useGestos()
  const pendiente = useRef<EventoGesto | null>(null)
  const indice = useRef(0)
  const anterior = useRef<string | null>(null)
  const libre = conversacion.sesion !== null && !conversacion.creandoSesion && !conversacion.enCurso

  const atender = (evento: EventoGesto) => {
    ultimoAtendido = evento.id
    switch (GESTOS[evento.gesto].accion) {
      case 'siguiente': {
        // si el BFF no contesta, una de las de siempre
        const deReserva = () => {
          indice.current += 1
          return PREGUNTAS_GESTO[(indice.current - 1) % PREGUNTAS_GESTO.length]
        }
        void pedirPregunta(anterior.current)
          .then(({ pregunta }) => pregunta, deReserva)
          .then((pregunta) => {
            anterior.current = pregunta
            conversacion.enviar(pregunta)
          })
        break
      }
      case 'motor':
        alCambiarMotor()
        break
      case 'leer': {
        if (hablando()) {
          callar()
          break
        }
        const ultimoAsistente = conversacion.mensajes.filter(esAsistente).at(-1)
        if (!ultimoAsistente?.texto) toast('Todavía no hay ninguna respuesta que leer')
        else if (!leerEnVozAlta(ultimoAsistente.texto)) toast('Este navegador no puede leer en voz alta')
        break
      }
    }
  }

  // El gesto que ha abierto el panel se emitió antes de que este chat existiera.
  useEffect(() => {
    const evento = ultimo()
    if (evento && evento.id > ultimoAtendido && EN_EL_CHAT.has(GESTOS[evento.gesto].accion)) pendiente.current = evento
  }, [ultimo])

  useAlGesto((evento) => {
    const accion = GESTOS[evento.gesto].accion
    if (!EN_EL_CHAT.has(accion) || evento.id <= ultimoAtendido) return
    if (libre || INMEDIATAS.has(accion)) atender(evento)
    else pendiente.current = evento
  })

  useEffect(() => {
    const evento = pendiente.current
    if (!libre || !evento) return
    pendiente.current = null
    if (evento.id > ultimoAtendido && Date.now() - evento.instante < CADUCA_MS) atender(evento)
  })
}
