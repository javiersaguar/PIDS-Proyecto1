/**
 * «Capturar datos»: enciende y apaga la captura en directo desde el grafo. Viajes reales de un mes de 2020 entran
 * por la API de captura como si ocurrieran ahora; el lienzo ilumina su camino (T15) y Tiempo real los ve llegar.
 *
 * Una sola simulación a la vez: si hay una de fichero en marcha (Operaciones), el interruptor se bloquea y lo dice.
 */
import { Radio } from 'lucide-react'
import { useState } from 'react'

import { mensajeDeError } from '@/api/cliente'
import {
  formatearReloj, useIniciarCaptura, useInfoCaptura, usePararCaptura, VELOCIDADES, type SimulacionCaptura,
} from '@/api/captura'
import { useSimulacion } from '@/api/operaciones'
import { formatearEntero } from '@/componentes/datos/formato'
import { Switch } from '@/componentes/ui/switch'
import { cn } from '@/lib/utils'

export function CapturaDatos({ className }: { className?: string }) {
  const info = useInfoCaptura()
  const simulacion = useSimulacion()
  const iniciar = useIniciarCaptura()
  const parar = usePararCaptura()
  const [velocidad, setVelocidad] = useState<number>(VELOCIDADES[0].valor)

  const estado = simulacion.data as SimulacionCaptura | undefined
  const capturando = !!estado?.activa && estado.modo === 'directo'
  const otraSimulacion = !!estado?.activa && estado.modo !== 'directo'
  const disponible = info.data?.disponible ?? false
  const ocupado = iniciar.isPending || parar.isPending
  const error = iniciar.error ?? parar.error ?? (!capturando && estado?.modo === 'directo' ? estado.error : null)

  const alCambiar = (encender: boolean) => {
    iniciar.reset()
    parar.reset()
    if (encender) iniciar.mutate(velocidad)
    else parar.mutate()
  }

  let detalle: string
  if (capturando) {
    const reloj = formatearReloj(estado?.reloj)
    detalle = `${reloj ? `${reloj} · ` : ''}${formatearEntero(estado?.enviados ?? 0)} viajes · ${formatearEntero(Math.round(estado?.ritmo ?? 0))}/s`
  } else if (otraSimulacion) {
    detalle = 'Hay una simulación de fichero en marcha (Operaciones)'
  } else if (info.isPending) {
    detalle = 'Comprobando…'
  } else if (!disponible) {
    detalle = 'Sin viajes preparados: make captura-preparar'
  } else {
    const sigue = formatearReloj(info.data?.reloj)
    detalle = sigue ? `Seguiría el ${sigue} de 2020` : 'Viajes reales de 2020, en su orden'
  }

  return (
    <div
      role="group"
      aria-label="Captura en directo"
      className={cn(
        'flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-2xl border border-[#e6edf5] bg-white/90 px-4 py-2.5 text-[13px] shadow-[0_1px_2px_rgba(15,23,42,0.04)]',
        capturando && 'border-emerald-200 bg-emerald-50/70',
        className,
      )}
    >
      <label className="flex items-center gap-2 font-semibold text-slate-700">
        <span className={cn('flex size-6 items-center justify-center rounded-lg', capturando ? 'bg-emerald-500 text-white' : 'bg-[#e8faf2] text-[#17875a]')} aria-hidden>
          <Radio className={cn('size-3.5', capturando && 'animate-pulse')} />
        </span>
        Capturar datos
        <Switch
          checked={capturando}
          disabled={ocupado || otraSimulacion || (!capturando && !disponible)}
          onCheckedChange={alCambiar}
          aria-describedby="captura-detalle"
        />
      </label>
      <select
        aria-label="Velocidad de la captura"
        value={capturando && estado?.velocidad ? estado.velocidad : velocidad}
        disabled={capturando || ocupado}
        onChange={(evento) => setVelocidad(Number(evento.target.value))}
        className="h-7 rounded-lg border border-[#e6edf5] bg-white px-2 text-xs text-slate-600 disabled:opacity-60"
      >
        {VELOCIDADES.map((opcion) => (
          <option key={opcion.valor} value={opcion.valor}>{opcion.texto}</option>
        ))}
        {capturando && estado?.velocidad && !VELOCIDADES.some((o) => o.valor === estado.velocidad) && (
          <option value={estado.velocidad}>×{estado.velocidad}</option>
        )}
      </select>
      <span id="captura-detalle" className={cn('text-xs tabular-nums', capturando ? 'text-emerald-800' : 'text-slate-500')}>
        {detalle}
      </span>
      {info.data?.demostracion && (
        <span className="text-xs text-slate-400">Demostración: se anima el flujo, no se envían viajes</span>
      )}
      {error && (
        <span role="alert" className="basis-full text-xs text-red-600">
          {typeof error === 'string' ? error : mensajeDeError(error)}
        </span>
      )}
    </div>
  )
}
