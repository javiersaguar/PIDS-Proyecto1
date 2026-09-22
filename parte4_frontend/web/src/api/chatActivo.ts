/**
 * El asistente del portal no pasa por TanStack Query (la respuesta es un flujo SSE), así que el grafo no se
 * entera solo. Quien envía un mensaje lo marca aquí mientras dura el turno; `useActividad` lo lee.
 */
import { useSyncExternalStore } from 'react'

import type { Motor } from './tipos'

export interface ChatsLocales {
  ollama: boolean
  rag: boolean
}

const VACIO: ChatsLocales = { ollama: false, rag: false }
const oyentes = new Set<() => void>()
let motor: Motor['id'] | null = null
let foto: ChatsLocales = VACIO

function publicar(): void {
  const siguiente: ChatsLocales = { ollama: motor === 'ollama', rag: motor === 'rag' }
  if (siguiente.ollama === foto.ollama && siguiente.rag === foto.rag) return
  foto = siguiente.ollama || siguiente.rag ? siguiente : VACIO
  oyentes.forEach((oyente) => oyente())
}

/** `motor` mientras ese asistente responde; `null` al terminar el turno. */
export function marcarChatActivo(activo: Motor['id'] | null): void {
  motor = activo
  publicar()
}

export function chatsLocales(): ChatsLocales {
  return foto
}

export function useChatsLocales(): ChatsLocales {
  return useSyncExternalStore(
    (oyente) => {
      oyentes.add(oyente)
      return () => oyentes.delete(oyente)
    },
    chatsLocales,
    () => VACIO,
  )
}
