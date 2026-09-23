/**
 * El interruptor de los gestos, en el menú de la izquierda: enciende la cámara y el reconocimiento, o los apaga.
 * Dice en qué estado están (apagados, preparando la cámara, activos o con un error).
 */
import { Hand } from 'lucide-react'

import { cn } from '@/lib/utils'

import { useGestos } from './contexto'

const ESTADOS = {
  apagada: { texto: 'Apagados', punto: 'bg-slate-300' },
  cargando: { texto: 'Preparando…', punto: 'bg-amber-400 animate-pulse' },
  activa: { texto: 'Cámara activa', punto: 'bg-emerald-500' },
  error: { texto: 'Sin cámara', punto: 'bg-red-500' },
} as const

export function BotonGestos() {
  const { estado, activar, desactivar } = useGestos()
  const encendido = estado === 'activa' || estado === 'cargando'
  const { texto, punto } = ESTADOS[estado]
  return (
    <button
      type="button"
      aria-pressed={encendido}
      onClick={encendido ? desactivar : activar}
      title={encendido ? 'Apagar la cámara y los gestos' : 'Manejar TAXI AI con gestos de la mano (la imagen no sale del navegador)'}
      className={cn(
        'flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-[13.5px] font-medium transition-colors',
        'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#2563eb]',
        encendido ? 'bg-[#efe9ff] text-[#5b3ae0]' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900',
      )}
    >
      <Hand className="size-4 shrink-0" aria-hidden />
      <span className="min-w-0 flex-1 truncate">Gestos</span>
      <span className="flex shrink-0 items-center gap-1.5 text-[11px] font-normal text-slate-500">
        <span className={cn('size-1.5 rounded-full', punto)} aria-hidden />
        {texto}
      </span>
    </button>
  )
}
