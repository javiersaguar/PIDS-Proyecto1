/**
 * Lienzo de la arquitectura: fondo de puntos, tarjetas y curvas. Al pulsar una pieza se abre
 * una ficha breve (qué es, qué hace y cómo se conecta).
 */
import { useLayoutEffect, useRef, useState } from 'react'
import { Link } from 'react-router'

import type { Panel } from '@/api/tipos'
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/componentes/ui/dialog'
import { cn } from '@/lib/utils'

import { ARISTAS, LIENZO, NODOS, TARJETA, TONOS, type Arista, type Lado, type Nodo } from './nodos'

const DIR: Record<Lado, { x: number; y: number }> = {
  derecha: { x: 1, y: 0 },
  izquierda: { x: -1, y: 0 },
  abajo: { x: 0, y: 1 },
  arriba: { x: 0, y: -1 },
}

function ancla(nodo: Nodo, lado: Lado, desplaza = 0) {
  const cx = nodo.x + TARJETA.ancho / 2
  const cy = nodo.y + TARJETA.alto / 2
  if (lado === 'derecha') return { x: nodo.x + TARJETA.ancho, y: cy + desplaza }
  if (lado === 'izquierda') return { x: nodo.x, y: cy + desplaza }
  if (lado === 'abajo') return { x: cx + desplaza, y: nodo.y + TARJETA.alto }
  return { x: cx + desplaza, y: nodo.y }
}

function puntoCurva(p0: { x: number; y: number }, p1: { x: number; y: number }, p2: { x: number; y: number }, p3: { x: number; y: number }, t: number) {
  const u = 1 - t
  return {
    x: u ** 3 * p0.x + 3 * u ** 2 * t * p1.x + 3 * u * t ** 2 * p2.x + t ** 3 * p3.x,
    y: u ** 3 * p0.y + 3 * u ** 2 * t * p1.y + 3 * u * t ** 2 * p2.y + t ** 3 * p3.y,
  }
}

function trazo(arista: Arista, porId: Map<string, Nodo>) {
  const origen = porId.get(arista.desde)!
  const destino = porId.get(arista.hasta)!
  const p0 = ancla(origen, arista.salida, arista.desplazaSalida ?? 0)
  const p3 = ancla(destino, arista.entrada, arista.desplazaEntrada ?? 0)
  const dist = Math.hypot(p3.x - p0.x, p3.y - p0.y)
  const fuerza = Math.max(36, dist * 0.42)
  const sale = DIR[arista.salida]
  const entra = DIR[arista.entrada]
  const p1 = { x: p0.x + sale.x * fuerza, y: p0.y + sale.y * fuerza }
  const p2 = { x: p3.x + entra.x * fuerza, y: p3.y + entra.y * fuerza }
  const medio = puntoCurva(p0, p1, p2, p3, arista.tEtiqueta ?? 0.5)
  return {
    d: `M${p0.x},${p0.y} C${p1.x},${p1.y} ${p2.x},${p2.y} ${p3.x},${p3.y}`,
    medio,
    color: TONOS[arista.tono].linea,
  }
}

function Ficha({ nodo, enlaces, alCerrar }: { nodo: Nodo; enlaces: Panel['enlaces']; alCerrar: () => void }) {
  const tono = TONOS[nodo.tono]
  const Icono = nodo.icono
  return (
    <Dialog open onOpenChange={(abierto) => !abierto && alCerrar()}>
      <DialogContent showCloseButton={false} className="max-h-[85vh] gap-0 overflow-y-auto p-0 sm:max-w-2xl">
        <div className={cn('sticky top-0 z-10 flex items-start gap-3 px-5 pt-5 pr-20 pb-4 relative', tono.fondo)}>
          <DialogClose className="absolute top-3 right-3 rounded-lg px-2 py-1 text-xs font-medium text-slate-500 hover:bg-white/70 hover:text-slate-800">
            Cerrar
          </DialogClose>
          <span className={cn('flex size-11 shrink-0 items-center justify-center rounded-xl bg-white shadow-sm', tono.texto)} aria-hidden>
            <Icono className="size-5" />
          </span>
          <DialogHeader className="gap-1">
            <DialogTitle className="text-lg text-primario">{nodo.nombre ?? nodo.titulo}</DialogTitle>
            <DialogDescription>
              {nodo.tecnologia}
              <span className={cn('ml-2 inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold', tono.pastilla)}>{nodo.datos}</span>
            </DialogDescription>
          </DialogHeader>
        </div>
        <div className="space-y-4 px-5 py-4">
          <Bloque titulo="Qué es" parrafos={nodo.queEs} />
          <Bloque titulo="Qué hace" parrafos={nodo.queHace} />
          <Bloque titulo="Cómo se conecta aquí" parrafos={nodo.comoConecta} />
        </div>
        {(nodo.enlaces || nodo.ruta) && (
          <div className="flex flex-wrap gap-2 border-t px-5 py-3">
            {nodo.ruta && (
              <Link to={nodo.ruta.to} className="rounded-full bg-[#eaf2ff] px-3 py-1.5 text-xs font-semibold text-[#2f62c4] hover:bg-[#dce9ff]">
                {nodo.ruta.texto}
              </Link>
            )}
            {nodo.enlaces?.map((enlace) => (
              <a
                key={enlace.clave}
                href={enlaces[enlace.clave]}
                target="_blank"
                rel="noreferrer"
                className="rounded-full bg-[#eaf2ff] px-3 py-1.5 text-xs font-semibold text-[#2f62c4] hover:bg-[#dce9ff]"
              >
                {enlace.texto}
              </a>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

function Bloque({ titulo, parrafos }: { titulo: string; parrafos: string[] }) {
  return (
    <div className="space-y-1.5">
      <h3 className="text-[13px] font-semibold text-[#2f62c4]">{titulo}</h3>
      {parrafos.map((parrafo) => (
        <p key={parrafo} className="leading-relaxed text-texto">
          {parrafo}
        </p>
      ))}
    </div>
  )
}

export function Lienzo({ enlaces }: { enlaces: Panel['enlaces'] }) {
  const marco = useRef<HTMLDivElement>(null)
  const [ajuste, setAjuste] = useState(1)
  const [activoId, setActivoId] = useState<string | null>(null)
  const porId = new Map(NODOS.map((nodo) => [nodo.id, nodo]))
  const curvas = ARISTAS.map((arista) => ({ arista, ...trazo(arista, porId) }))
  const activo = NODOS.find((nodo) => nodo.id === activoId) ?? null

  useLayoutEffect(() => {
    const el = marco.current
    if (!el) return
    const medir = () => {
      const { width, height } = el.getBoundingClientRect()
      if (width < 40 || height < 40) return
      const siguiente = Math.min((width - 28) / LIENZO.ancho, (height - 28) / LIENZO.alto)
      setAjuste(Math.max(0.35, Math.min(siguiente, 1.05)))
    }
    medir()
    const obs = new ResizeObserver(medir)
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  return (
    <div ref={marco} className="relative h-full w-full overflow-hidden" role="region" aria-label="Arquitectura de la plataforma">
      <div className="fondo-marea absolute inset-0" aria-hidden />
      <div className="fondo-puntos absolute inset-0" aria-hidden />
      <div className="orbita orbita-azul" aria-hidden />
      <div className="orbita orbita-verde" aria-hidden />
      <div className="orbita orbita-cielo" aria-hidden />

      <div
        className="absolute top-1/2 left-1/2"
        style={{ width: LIENZO.ancho, height: LIENZO.alto, transform: `translate(-50%, -50%) scale(${ajuste})` }}
      >
        <svg className="pointer-events-none absolute inset-0 overflow-visible" width={LIENZO.ancho} height={LIENZO.alto} aria-hidden>
          <defs>
            {(Object.keys(TONOS) as (keyof typeof TONOS)[]).map((tono) => (
              <marker key={tono} id={`punta-${tono}`} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                <path d="M0,1.2 L9,5 L0,8.8 z" fill={TONOS[tono].linea} />
              </marker>
            ))}
          </defs>
          {curvas.map(({ arista, d, medio, color }) => {
            const ancho = arista.etiqueta.length * 6.3 + 18
            return (
              <g key={`${arista.desde}-${arista.hasta}`}>
                <path d={d} fill="none" stroke={color} strokeWidth={2} markerEnd={`url(#punta-${arista.tono})`} />
                <rect x={medio.x - ancho / 2} y={medio.y - 11} width={ancho} height={22} rx={11} fill="white" stroke={color} strokeOpacity={0.45} />
                <text x={medio.x} y={medio.y + 4} textAnchor="middle" fill={color} style={{ fontSize: 11, fontWeight: 600 }}>
                  {arista.etiqueta}
                </text>
              </g>
            )
          })}
        </svg>

        {NODOS.map((nodo) => {
          const tono = TONOS[nodo.tono]
          const Icono = nodo.icono
          const seleccionado = nodo.id === activoId
          return (
            <button
              key={nodo.id}
              type="button"
              onClick={() => setActivoId(nodo.id)}
              className="absolute flex flex-col rounded-2xl border border-[#e7eef6] bg-white px-3.5 py-3 text-left shadow-[0_8px_24px_rgba(15,23,42,0.06)] transition hover:-translate-y-0.5 hover:shadow-[0_14px_32px_rgba(15,23,42,0.1)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#60a5fa]"
              style={{
                left: nodo.x,
                top: nodo.y,
                width: TARJETA.ancho,
                height: TARJETA.alto,
                boxShadow: seleccionado ? `0 0 0 2px white, 0 0 0 4px ${tono.linea}` : undefined,
              }}
            >
              <span className="flex min-w-0 items-start gap-2.5">
                <span className={cn('flex size-9 shrink-0 items-center justify-center rounded-xl', tono.fondo, tono.texto)} aria-hidden>
                  <Icono className="size-4" />
                </span>
                <span className="min-w-0">
                  <span className="block text-[13.5px] leading-tight font-semibold text-slate-800">{nodo.titulo}</span>
                  <span className="mt-0.5 block text-[11.5px] leading-snug text-slate-500">{nodo.subtitulo}</span>
                </span>
              </span>
              <span className="mt-auto flex items-center justify-between gap-2 border-t border-dashed border-slate-200 pt-1.5">
                <span className="truncate text-[11px] text-slate-400">{nodo.tecnologia}</span>
                <span className={cn('shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold', tono.pastilla)}>{nodo.datos}</span>
              </span>
            </button>
          )
        })}
      </div>

      {activo && <Ficha nodo={activo} enlaces={enlaces} alCerrar={() => setActivoId(null)} />}
    </div>
  )
}
