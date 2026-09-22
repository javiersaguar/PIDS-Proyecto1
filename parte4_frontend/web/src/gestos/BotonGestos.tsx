/** El interruptor de los gestos, en la cabecera de TAXI AI: enciende la cámara y el reconocimiento, o los apaga. */
import { Hand } from 'lucide-react'

import { Button } from '@/componentes/ui/button'
import { cn } from '@/lib/utils'

import { useGestos } from './contexto'

export function BotonGestos() {
  const { estado, activar, desactivar } = useGestos()
  const encendido = estado === 'activa' || estado === 'cargando'
  return (
    <Button
      variant="ghost"
      size="sm"
      aria-pressed={encendido}
      onClick={encendido ? desactivar : activar}
      title={encendido ? 'Apagar la cámara y los gestos' : 'Controlar TAXI AI con gestos de la mano (la imagen no sale del navegador)'}
      className={cn('text-slate-500', encendido && 'bg-[#efe9ff] text-[#5b3ae0] hover:bg-[#e4dbff]')}
    >
      <Hand aria-hidden className={cn(estado === 'cargando' && 'animate-pulse')} />
      <span className="max-sm:sr-only">Gestos</span>
    </Button>
  )
}
