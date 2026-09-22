/**
 * Lo que hacen los gestos dentro de TAXI AI (tabla de `config/gestos.json`):
 *   👍 confirmar   ejecuta la alternativa pendiente (la que propone el asistente tras un rechazo)
 *   ✋ cancelar    calla la lectura; si no, descarta la alternativa; si no, corta la respuesta en curso
 *   ✌️ siguiente   hace la siguiente pregunta de ejemplo (las de `preguntas`, dando la vuelta)
 *   👌 leer        lee en voz alta la última respuesta
 * Confirmar y preguntar esperan a que el chat esté libre: el gesto que abre el panel se atiende en cuanto hay
 * sesión, y uno que llega mientras el asistente responde, al terminar.
 */
import { useEffect, useRef } from 'react'
import { toast } from 'sonner'

import { esAsistente } from '@/componentes/chat/tipos'
import type { Conversacion } from '@/componentes/chat/useConversacion'
import { useAlGesto, useGestos, type EventoGesto } from '@/gestos/contexto'
import { GESTOS, PREGUNTAS_GESTO, type Accion } from '@/gestos/tabla'
import { callar, leerEnVozAlta } from '@/gestos/voz'

const EN_EL_CHAT: ReadonlySet<Accion> = new Set(['confirmar', 'cancelar', 'siguiente', 'leer'])
const INMEDIATAS: ReadonlySet<Accion> = new Set(['cancelar', 'leer'])
/** Un gesto que espera al chat caduca pasado este tiempo: no se ejecuta algo que ya nadie recuerda haber pedido. */
const CADUCA_MS = 10_000

// Un gesto no se atiende dos veces aunque el chat se desmonte y se vuelva a montar.
let ultimoAtendido = 0

export function useGestosChat(conversacion: Conversacion): void {
  const { ultimo } = useGestos()
  const pendiente = useRef<EventoGesto | null>(null)
  const indice = useRef(0)
  const libre = conversacion.sesion !== null && !conversacion.creandoSesion && !conversacion.enCurso

  const atender = (evento: EventoGesto) => {
    ultimoAtendido = evento.id
    const ultimoAsistente = conversacion.mensajes.filter(esAsistente).at(-1)
    const conAlternativa = ultimoAsistente?.respuesta?.alternativa && !ultimoAsistente.alternativaResuelta ? ultimoAsistente : null
    switch (GESTOS[evento.gesto].accion) {
      case 'confirmar':
        if (conAlternativa) conversacion.aceptarAlternativa(conAlternativa.id)
        else toast('No hay ninguna alternativa pendiente', { description: 'Aparece cuando el asistente rechaza una petición individual.' })
        break
      case 'cancelar':
        if (callar()) break
        if (conAlternativa) conversacion.cancelarAlternativa(conAlternativa.id)
        else if (conversacion.enCurso) conversacion.detener()
        break
      case 'siguiente': {
        const pregunta = PREGUNTAS_GESTO[indice.current % PREGUNTAS_GESTO.length]
        indice.current += 1
        conversacion.enviar(pregunta)
        break
      }
      case 'leer':
        if (!ultimoAsistente?.texto) toast('Todavía no hay ninguna respuesta que leer')
        else if (!leerEnVozAlta(ultimoAsistente.texto)) toast('Este navegador no puede leer en voz alta')
        break
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
