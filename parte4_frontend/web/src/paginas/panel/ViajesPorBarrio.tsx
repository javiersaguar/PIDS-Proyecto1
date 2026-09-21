/**
 * Viajes por barrio: cada barrio es una barra. No es una serie temporal.
 * Histórico y tiempo real se alternan con el control segmentado.
 */
import { BarChart3 } from 'lucide-react'
import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, LabelList, Tooltip, XAxis, YAxis } from 'recharts'

import type { PanelExtendido, UltimoDiaExtendido } from '@/api/panel'
import { formatearDecimal, formatearEntero, formatearFecha } from '@/componentes/datos/formato'
import { ContenedorGrafico } from '@/componentes/graficos/ContenedorGrafico'
import { EstadoNoDisponible, EstadoVacio } from '@/componentes/shell'

import { SelectorSegmentado } from './SelectorSegmentado'

type ClaveFuente = 'historico' | 'tiempo_real'

const TITULO_FUENTE: Record<ClaveFuente, string> = { historico: 'Histórico', tiempo_real: 'Tiempo real' }
const AZUL = '#3b82f6'

interface Punto {
  etiqueta: string
  valor: number
}

function puntosDe(dia: UltimoDiaExtendido): Punto[] {
  return Object.entries(dia.por_barrio)
    .map(([etiqueta, valor]) => ({ etiqueta, valor }))
    .sort((a, b) => b.valor - a.valor || a.etiqueta.localeCompare(b.etiqueta, 'es'))
}

function formatearEje(valor: number): string {
  if (!Number.isFinite(valor)) return ''
  if (Math.abs(valor) >= 1000) {
    const miles = valor / 1000
    return `${formatearDecimal(miles, Math.abs(miles) >= 10 ? 0 : 1)} mil`
  }
  return formatearEntero(valor)
}

function TooltipViajes({ active, payload }: { active?: boolean; payload?: ReadonlyArray<{ payload?: Punto }> }) {
  const punto = payload?.[0]?.payload
  if (!active || !punto) return null
  return (
    <div className="rounded-lg bg-slate-900 px-3 py-1.5 text-white shadow-lg">
      <p className="text-[11px] font-medium text-slate-300">{punto.etiqueta}</p>
      <p className="cifra text-sm font-semibold">{formatearEntero(punto.valor)}</p>
    </div>
  )
}

function Grafico({ dia, fuente, accesoDisponible }: { dia: UltimoDiaExtendido | null; fuente: ClaveFuente; accesoDisponible: boolean }) {
  if (!dia && !accesoDisponible) {
    return <EstadoNoDisponible servicio="API de acceso" descripcion="Sin cifras del último día mientras la API de acceso no responda." className="border-0 bg-transparent py-8" />
  }
  if (!dia || Object.keys(dia.por_barrio).length === 0) {
    return (
      <EstadoVacio
        titulo={`Sin datos de ${TITULO_FUENTE[fuente].toLowerCase()}`}
        descripcion={fuente === 'tiempo_real' ? 'Arranca el simulador en Operaciones para ver viajes en tiempo real.' : 'No hay agregados publicados para esta fuente.'}
        className="border-0 bg-transparent"
      />
    )
  }

  const puntos = puntosDe(dia)
  const titulo = `Viajes por barrio el ${formatearFecha(dia.dia)} (${TITULO_FUENTE[fuente].toLowerCase()})`
  const alto = Math.max(220, puntos.length * 40 + 28)

  return (
    <figure className="w-full" aria-label={titulo} role="img">
      <ContenedorGrafico altura={alto}>
        {({ ancho }) => (
          <BarChart layout="vertical" width={ancho} height={alto} data={puntos} margin={{ top: 4, right: 76, bottom: 0, left: 0 }} barCategoryGap={8}>
            <CartesianGrid stroke="#e7eef6" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} tickFormatter={formatearEje} />
            <YAxis type="category" dataKey="etiqueta" width={96} tick={{ fontSize: 12, fill: '#475569' }} axisLine={false} tickLine={false} />
            <Tooltip cursor={{ fill: '#f8fafc' }} content={TooltipViajes} />
            <Bar dataKey="valor" name="Viajes" fill={AZUL} radius={[0, 8, 8, 0]} maxBarSize={18} isAnimationActive={false} background={{ fill: '#f4f7fb', radius: 8 }}>
              <LabelList
                dataKey="valor"
                position="right"
                fill="#1e293b"
                fontSize={12}
                fontWeight={600}
                formatter={(valor: unknown) => formatearEntero(typeof valor === 'number' ? valor : Number(valor))}
              />
            </Bar>
          </BarChart>
        )}
      </ContenedorGrafico>
    </figure>
  )
}

export function ViajesPorBarrio({ ultimoDia, accesoDisponible = true }: { ultimoDia: PanelExtendido['ultimo_dia']; accesoDisponible?: boolean }) {
  const hayTiempoReal = !!ultimoDia?.tiempo_real
  const [fuente, setFuente] = useState<ClaveFuente>('historico')
  const historico = ultimoDia?.historico ?? null
  const tiempoReal = ultimoDia?.tiempo_real ?? null

  return (
    <section className="rounded-2xl border border-[#e6edf5] bg-white px-5 py-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_10px_28px_rgba(15,23,42,0.05)]">
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2.5">
          <span className="flex size-9 items-center justify-center rounded-xl bg-[#eaf2ff] text-[#2f62c4]" aria-hidden>
            <BarChart3 className="size-4" />
          </span>
          <h2 className="text-[15px] text-slate-900">Viajes por barrio</h2>
        </div>
        <p className="flex items-center gap-2 text-xs font-medium text-slate-500 sm:mx-auto">
          <span className="size-2 rounded-full bg-[#3b82f6]" aria-hidden />
          Viajes
        </p>
        {hayTiempoReal && (
          <SelectorSegmentado
            etiqueta="Fuente de los datos"
            valor={fuente}
            opciones={[
              { valor: 'historico', texto: 'Histórico' },
              { valor: 'tiempo_real', texto: 'Tiempo real' },
            ]}
            alCambiar={setFuente}
          />
        )}
      </div>
      {fuente === 'tiempo_real' && hayTiempoReal ? (
        <Grafico dia={tiempoReal} fuente="tiempo_real" accesoDisponible={accesoDisponible} />
      ) : (
        <Grafico dia={historico} fuente="historico" accesoDisponible={accesoDisponible} />
      )}
    </section>
  )
}
