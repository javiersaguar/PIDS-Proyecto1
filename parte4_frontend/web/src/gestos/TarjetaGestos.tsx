/**
 * La tarjeta de la cámara: el vídeo en espejo (como un espejo de verdad) con los 21 puntos de la mano encima, el gesto
 * que ve el modelo con su confianza y una barra que se llena mientras se sostiene, la chuleta de los seis gestos y a
 * dónde ha ido el último. Se puede plegar a una pastilla para que no tape la página; el vídeo sigue funcionando.
 */
import { ChevronDown, ChevronUp, Hand, Lock, RefreshCw, X } from 'lucide-react'
import { useEffect, useRef, useState, type RefObject } from 'react'

import { Button } from '@/componentes/ui/button'
import { cn } from '@/lib/utils'

import { useGestos, useLectura } from './contexto'
import { CONFIANZA_MINIMA, GESTOS, LISTA_GESTOS } from './tabla'

/** Las conexiones de la mano de MediaPipe (HAND_CONNECTIONS): pulgar, dedos y palma. */
const CONEXIONES: [number, number][] = [
  [0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [5, 6], [6, 7], [7, 8], [5, 9], [9, 10], [10, 11], [11, 12],
  [9, 13], [13, 14], [14, 15], [15, 16], [13, 17], [0, 17], [17, 18], [18, 19], [19, 20],
]

interface Props {
  videoRef: RefObject<HTMLVideoElement | null>
  panelAbierto: boolean
  elevada: boolean
}

function Esqueleto({ aspecto }: { aspecto: number }) {
  const lienzo = useRef<HTMLCanvasElement>(null)
  const { puntos, gesto, confianza } = useLectura()
  useEffect(() => {
    const ctx = lienzo.current?.getContext('2d')
    if (!ctx || !lienzo.current) return
    const { width, height } = lienzo.current
    ctx.clearRect(0, 0, width, height)
    if (!puntos) return
    // en espejo, igual que el vídeo: x → 1 - x
    const a = (i: number) => [(1 - puntos[i][0]) * width, puntos[i][1] * height] as const
    const seguro = gesto !== null && confianza >= CONFIANZA_MINIMA
    ctx.lineWidth = 3
    ctx.strokeStyle = seguro ? 'rgba(109, 74, 255, 0.9)' : 'rgba(255, 255, 255, 0.85)'
    for (const [i, j] of CONEXIONES) {
      const [x1, y1] = a(i)
      const [x2, y2] = a(j)
      ctx.beginPath()
      ctx.moveTo(x1, y1)
      ctx.lineTo(x2, y2)
      ctx.stroke()
    }
    ctx.fillStyle = seguro ? '#6d4aff' : '#ffffff'
    puntos.forEach((_, i) => {
      const [x, y] = a(i)
      ctx.beginPath()
      ctx.arc(x, y, i === 0 ? 5 : 3.5, 0, Math.PI * 2)
      ctx.fill()
    })
  }, [puntos, gesto, confianza])
  return <canvas ref={lienzo} width={640} height={Math.round(640 / aspecto)} className="pointer-events-none absolute inset-0 size-full" aria-hidden />
}

function LecturaActual() {
  const { gesto, confianza, progreso, puntos } = useLectura()
  const datos = gesto ? GESTOS[gesto] : null
  const seguro = datos !== null && confianza >= CONFIANZA_MINIMA
  return (
    <div className="flex items-center gap-2.5" aria-live="off">
      <span className={cn('flex size-9 shrink-0 items-center justify-center rounded-xl text-lg transition-colors', seguro ? 'bg-[#efe9ff]' : 'bg-slate-100')} aria-hidden>
        {seguro ? datos.emoji : '·'}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[13px] font-semibold text-slate-800">
          {!puntos ? 'Enseña la mano a la cámara' : seguro ? datos.titulo : 'Sin gesto claro'}
        </p>
        <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-label="Gesto sostenido"
             aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progreso * 100)}>
          <span className="block h-full rounded-full bg-[#6d4aff] transition-[width] duration-200 ease-out motion-reduce:transition-none"
                style={{ width: `${progreso * 100}%` }} />
        </div>
      </div>
      <span className="w-10 text-right text-xs font-medium text-slate-500 tabular-nums">
        {puntos ? `${Math.round(confianza * 100)} %` : '—'}
      </span>
    </div>
  )
}

function Chuleta() {
  const { gesto, confianza } = useLectura()
  return (
    <ul className="grid grid-cols-2 gap-x-1 gap-y-0.5" aria-label="Qué hace cada gesto">
      {LISTA_GESTOS.map((g) => {
        const activo = g === gesto && confianza >= CONFIANZA_MINIMA
        return (
          <li key={g} title={GESTOS[g].texto}
              className={cn('flex min-w-0 items-center gap-1.5 rounded-lg px-1.5 py-0.5 text-[11px] text-slate-600 transition-colors', activo && 'bg-[#efe9ff] text-[#5b3ae0]')}>
            <span aria-hidden>{GESTOS[g].emoji}</span>
            <span className="truncate">{GESTOS[g].titulo}</span>
          </li>
        )
      })}
    </ul>
  )
}

export function TarjetaGestos({ videoRef, panelAbierto, elevada }: Props) {
  const { estado, error, destino, activar, desactivar } = useGestos()
  const [plegada, setPlegada] = useState(false)
  // el recuadro toma la proporción de la cámara: así los puntos dibujados caen sobre la mano
  const [aspecto, setAspecto] = useState(4 / 3)
  const { gesto, confianza } = useLectura()
  const datosPastilla = gesto && confianza >= CONFIANZA_MINIMA ? GESTOS[gesto] : null

  return (
    <section
      aria-label="Gestos con la cámara"
      className={cn(
        'fixed z-40 w-64 rounded-2xl border border-[#eceaf3] bg-white/95 p-3 shadow-[0_18px_48px_-20px_rgba(15,23,42,0.45)] backdrop-blur',
        'animate-in fade-in-0 slide-in-from-bottom-2 duration-300 motion-reduce:animate-none',
        panelAbierto
          ? 'right-[calc(min(100vw,30rem)+0.75rem)] bottom-4 max-sm:top-3 max-sm:right-3 max-sm:bottom-auto'
          : elevada ? 'right-3 bottom-52' : 'right-3 bottom-28',
      )}
    >
      <header className="flex items-center gap-2">
        <span className="flex size-7 items-center justify-center rounded-lg bg-[#6d4aff] text-white" aria-hidden>
          <Hand className="size-3.5" />
        </span>
        <div className="min-w-0 flex-1 leading-tight">
          <p className="text-[13px] font-semibold text-slate-900">Gestos</p>
          <p className="truncate text-[11px] text-slate-500">
            {plegada && datosPastilla ? `${datosPastilla.emoji} ${datosPastilla.titulo}` : 'Modelo de la parte 1 · 96,5 %'}
          </p>
        </div>
        <Button variant="ghost" size="icon" className="size-7 text-slate-500" onClick={() => setPlegada((p) => !p)}
                aria-label={plegada ? 'Mostrar la cámara' : 'Plegar la cámara'} aria-expanded={!plegada}>
          {plegada ? <ChevronUp aria-hidden /> : <ChevronDown aria-hidden />}
        </Button>
        <Button variant="ghost" size="icon" className="size-7 text-slate-500" onClick={desactivar} aria-label="Apagar la cámara y los gestos">
          <X aria-hidden />
        </Button>
      </header>

      {/* El vídeo sigue montado aunque la tarjeta esté plegada: si se oculta, el navegador deja de darle fotogramas. */}
      <div className={cn('relative mt-2.5 overflow-hidden rounded-xl bg-slate-900', plegada && 'pointer-events-none absolute size-px opacity-0')}
           style={plegada ? undefined : { aspectRatio: aspecto }}>
        <video ref={videoRef} muted playsInline className="size-full -scale-x-100 object-fill" aria-label="Vídeo de la cámara (no sale del navegador)"
               onLoadedMetadata={(e) => setAspecto(e.currentTarget.videoWidth / e.currentTarget.videoHeight || 4 / 3)} />
        {estado === 'activa' && <Esqueleto aspecto={aspecto} />}
        {estado === 'cargando' && (
          <p className="absolute inset-0 flex items-center justify-center p-4 text-center text-xs text-white/85" role="status">
            Preparando la cámara y el modelo…
          </p>
        )}
        {estado === 'error' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 p-4 text-center text-xs text-white/90" role="alert">
            <p>{error}</p>
            <Button size="sm" variant="secondary" onClick={activar}>
              <RefreshCw aria-hidden />
              Reintentar
            </Button>
          </div>
        )}
      </div>

      {!plegada && (
        <div className="mt-2.5 grid grid-cols-1 gap-2.5">
          {estado === 'activa' && <LecturaActual />}
          <Chuleta />
          <p className="flex items-start gap-1.5 text-[11px] leading-snug text-slate-500">
            <Lock className="mt-px size-3 shrink-0" aria-hidden />
            <span className="min-w-0">
              La imagen no sale de este navegador: solo la etiqueta y la confianza.
              {destino === 'plataforma' && ' El último gesto entró en la plataforma (API de captura → Redpanda).'}
              {destino === 'navegador' && ' El último gesto se ha quedado en el navegador.'}
            </span>
          </p>
        </div>
      )}
    </section>
  )
}
