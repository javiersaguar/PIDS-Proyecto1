/**
 * Los paneles de un cuadro de Grafana dibujados con los componentes del portal. Todos se mueven igual que el resto
 * de la app: los números recorren el camino hasta el valor nuevo, las áreas y el anillo se deslizan hacia la forma
 * nueva y las barras cambian de ancho con una transición. Con `prefers-reduced-motion`, sin movimiento.
 */
import { AlertTriangle, CheckCircle2, Clock3, Info } from 'lucide-react'
import { useId, type CSSProperties, type ReactNode } from 'react'
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, Tooltip, XAxis, YAxis } from 'recharts'

import type { AlertaPanel, PanelCuadro } from '@/api/observabilidad'
import { Markdown } from '@/componentes/chat/Markdown'
import { useMovimientoReducido } from '@/componentes/datos/useMovimientoReducido'
import { useNumeroAnimado, useValoresAnimados } from '@/componentes/datos/useNumeroAnimado'
import { COLOR_BORDE, colorSerie, ESTILO_TICK } from '@/componentes/graficos/comun'
import { ContenedorGrafico } from '@/componentes/graficos/ContenedorGrafico'
import { TooltipGrafico } from '@/componentes/graficos/TooltipGrafico'
import { Tooltip as Ayuda, TooltipContent, TooltipTrigger } from '@/componentes/ui/tooltip'
import { cn } from '@/lib/utils'
import { MiniSerie } from '@/paginas/panel/MiniSerie'

import { aFilas, altoGrafica, color, colorPorUmbral, formatear } from './formatoUnidad'

const DURACION_MS = 700
const hora = (segundos: number) =>
  new Date(segundos * 1000).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })

function Tarjeta({ panel, indice, children, className }: { panel: PanelCuadro; indice: number; children: ReactNode; className?: string }) {
  const estilo: CSSProperties = { animationDelay: `${Math.min(indice, 12) * 45}ms`, animationFillMode: 'both' }
  return (
    <section
      aria-label={panel.titulo}
      className={cn(
        'flex h-full min-h-0 flex-col overflow-hidden rounded-2xl border border-[#e6edf5] bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04)]',
        'animate-in fade-in-0 slide-in-from-bottom-2 duration-500',
        className,
      )}
      style={estilo}
    >
      <header className="mb-2 flex shrink-0 items-start justify-between gap-2">
        <h3 className="text-[13px] leading-tight font-semibold text-slate-700">{panel.titulo}</h3>
        {panel.descripcion && (
          <Ayuda>
            <TooltipTrigger asChild>
              <button type="button" className="rounded-full text-slate-400 hover:text-slate-600" aria-label={`Qué es «${panel.titulo}»`}>
                <Info className="size-3.5" aria-hidden />
              </button>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">{panel.descripcion}</TooltipContent>
          </Ayuda>
        )}
      </header>
      <div className="relative min-h-0 flex-1 overflow-hidden">{panel.error ? <SinDatos texto={panel.error} /> : children}</div>
    </section>
  )
}

function SinDatos({ texto = 'Sin datos en este periodo' }: { texto?: string }) {
  return <p className="flex h-full items-center justify-center text-xs text-slate-400">{texto}</p>
}

// --- stat -------------------------------------------------------------------------------------------------------

function ValorStat({ panel, valor, grande }: { panel: PanelCuadro; valor: number | null; grande: boolean }) {
  const animado = useNumeroAnimado(valor)
  const tono = colorPorUmbral(panel, valor) ?? '#0f172a'
  // una fecha no se anima: pasaría por días intermedios
  const texto = formatear(panel.unidad === 'dateTimeAsIso' ? valor : animado, panel.unidad)
  const largo = texto.length > 8
  return (
    <span
      className={cn('shrink-0 font-semibold tracking-tight whitespace-nowrap tabular-nums', grande ? (largo ? 'text-2xl leading-none' : 'text-[1.9rem] leading-none') : 'text-sm leading-none')}
      style={{ color: tono }}
    >
      {texto}
    </span>
  )
}

export function PanelStat({ panel, indice }: { panel: PanelCuadro; indice: number }) {
  const valores = panel.valores ?? []
  const principal = valores[0]?.valor ?? null
  const tono = colorPorUmbral(panel, principal) ?? '#2f62c4'
  return (
    <Tarjeta panel={panel} indice={indice}>
      {valores.length === 0 ? (
        <SinDatos />
      ) : valores.length === 1 ? (
        <div className="flex h-full items-end justify-between gap-3 overflow-hidden">
          <ValorStat panel={panel} valor={principal} grande />
          {panel.unidad !== 'dateTimeAsIso' && panel.chispa && panel.chispa.length > 1 && (
            <MiniSerie valores={panel.chispa} color={tono} className="h-10 w-24 min-w-0 shrink" />
          )}
        </div>
      ) : (
        <ul className="flex h-full min-h-0 flex-col justify-start gap-1 overflow-y-auto">
          {valores.map((v, i) => (
            <li key={`${v.nombre}-${i}`} className="flex min-w-0 items-baseline justify-between gap-2">
              <span className="min-w-0 truncate text-xs text-slate-500">{v.nombre}</span>
              <ValorStat panel={panel} valor={v.valor} grande={false} />
            </li>
          ))}
        </ul>
      )}
    </Tarjeta>
  )
}

// --- serie temporal ----------------------------------------------------------------------------------------------

export function PanelSerie({ panel, indice }: { panel: PanelCuadro; indice: number }) {
  const reducido = useMovimientoReducido()
  const id = useId().replace(/:/g, '')
  const series = (panel.series ?? []).filter((s) => s.puntos.some(([, v]) => v != null))
  const filas = aFilas(series)
  const colorDe = (nombre: string, i: number) => color(panel.colores[nombre]) ?? colorSerie(i)
  const conLeyenda = series.length > 1
  const altura = altoGrafica(panel.alto, conLeyenda)
  return (
    <Tarjeta panel={panel} indice={indice}>
      {series.length === 0 ? (
        <SinDatos />
      ) : (
        <div className="flex h-full flex-col">
          {conLeyenda && (
            <ul className="mb-1 flex flex-wrap gap-x-3 gap-y-0.5 text-[11px] text-slate-500">
              {series.map((s, i) => (
                <li key={s.nombre} className="flex items-center gap-1.5">
                  <span className="size-2 rounded-full" style={{ backgroundColor: colorDe(s.nombre, i) }} aria-hidden />
                  {s.nombre}
                </li>
              ))}
            </ul>
          )}
          <figure role="img" aria-label={panel.titulo} className="min-h-0 flex-1">
            <ContenedorGrafico altura={altura}>
              {({ ancho }) => (
                <AreaChart width={ancho} height={altura} data={filas} margin={{ top: 6, right: 6, bottom: 0, left: 0 }}>
                  <defs>
                    {series.map((s, i) => (
                      <linearGradient key={s.nombre} id={`${id}-${i}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={colorDe(s.nombre, i)} stopOpacity={0.26} />
                        <stop offset="100%" stopColor={colorDe(s.nombre, i)} stopOpacity={0} />
                      </linearGradient>
                    ))}
                  </defs>
                  <CartesianGrid stroke={COLOR_BORDE} strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="t" type="number" domain={['dataMin', 'dataMax']} tickFormatter={hora} tick={ESTILO_TICK}
                         axisLine={false} tickLine={false} minTickGap={48} />
                  <YAxis tickFormatter={(v: number) => formatear(v, panel.unidad, true)} tick={ESTILO_TICK} axisLine={false}
                         tickLine={false} width={68} />
                  <Tooltip
                    cursor={{ stroke: COLOR_BORDE }}
                    content={<TooltipGrafico formatearValor={(v) => formatear(v, panel.unidad)} formatearEtiqueta={(t) => hora(Number(t))} />}
                  />
                  {series.map((s, i) => (
                    <Area
                      key={s.nombre}
                      type="monotone"
                      dataKey={s.nombre}
                      name={s.nombre}
                      stroke={colorDe(s.nombre, i)}
                      strokeWidth={2}
                      fill={`url(#${id}-${i})`}
                      dot={false}
                      activeDot={{ r: 4 }}
                      connectNulls
                      isAnimationActive={!reducido}
                      animationDuration={DURACION_MS}
                      animationEasing="ease-out"
                    />
                  ))}
                </AreaChart>
              )}
            </ContenedorGrafico>
          </figure>
        </div>
      )}
    </Tarjeta>
  )
}

// --- barras ------------------------------------------------------------------------------------------------------

export function PanelBarras({ panel, indice }: { panel: PanelCuadro; indice: number }) {
  const conMapeos = Object.keys(panel.mapeos).length > 0
  const valores = [...(panel.valores ?? [])].filter((v) => v.valor != null)
  valores.sort(conMapeos ? (a, b) => a.nombre.localeCompare(b.nombre) : (a, b) => (b.valor ?? 0) - (a.valor ?? 0))
  const animados = useValoresAnimados(valores.map((v) => v.valor ?? 0))
  const maximo = conMapeos ? 1 : Math.max(...valores.map((v) => v.valor ?? 0), 0) || 1
  return (
    <Tarjeta panel={panel} indice={indice}>
      {valores.length === 0 ? (
        <SinDatos />
      ) : (
        <ul className="@container grid h-full content-start gap-2 overflow-y-auto pr-1">
          {valores.map((v, i) => {
            const mapeo = conMapeos ? panel.mapeos[String(Math.round(v.valor ?? 0))] : undefined
            const tono = color(mapeo?.color) ?? colorPorUmbral(panel, v.valor) ?? colorSerie(i)
            const mostrado = animados[i] ?? v.valor ?? 0
            const fraccion = conMapeos ? 1 : Math.max(0.015, (v.valor ?? 0) / maximo)
            return (
              <li key={`${v.nombre}-${i}`} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-2 gap-y-1 text-xs @sm:grid-cols-[minmax(0,9rem)_1fr_auto]">
                <span className="truncate text-slate-600" title={v.nombre}>{v.nombre}</span>
                <span className="order-last col-span-2 h-2.5 overflow-hidden rounded-full bg-slate-100 @sm:order-none @sm:col-span-1">
                  <span
                    className="block h-full rounded-full transition-[width] duration-700 ease-out motion-reduce:transition-none"
                    style={{ width: `${fraccion * 100}%`, backgroundColor: tono }}
                  />
                </span>
                <span className="min-w-14 text-right font-medium tabular-nums" style={{ color: mapeo ? tono : undefined }}>
                  {mapeo?.texto ?? formatear(mostrado, panel.unidad)}
                </span>
              </li>
            )
          })}
        </ul>
      )}
    </Tarjeta>
  )
}

// --- tarta -------------------------------------------------------------------------------------------------------

export function PanelTarta({ panel, indice }: { panel: PanelCuadro; indice: number }) {
  const reducido = useMovimientoReducido()
  const valores = (panel.valores ?? []).filter((v) => (v.valor ?? 0) > 0).sort((a, b) => (b.valor ?? 0) - (a.valor ?? 0))
  const total = valores.reduce((suma, v) => suma + (v.valor ?? 0), 0)
  const lado = Math.min(altoGrafica(panel.alto, false), 168)
  return (
    <Tarjeta panel={panel} indice={indice}>
      {valores.length === 0 ? (
        <SinDatos />
      ) : (
        <div className="grid h-full grid-cols-[auto_minmax(0,1fr)] items-center gap-3">
          <PieChart width={lado} height={lado}>
            <Pie data={valores} dataKey="valor" nameKey="nombre" innerRadius="58%" outerRadius="88%" paddingAngle={2}
                 stroke="none" isAnimationActive={!reducido} animationDuration={DURACION_MS} animationEasing="ease-out">
              {valores.map((v, i) => <Cell key={`${v.nombre}-${i}`} fill={color(panel.colores[v.nombre]) ?? colorSerie(i)} />)}
            </Pie>
            <Tooltip content={<TooltipGrafico formatearValor={(v) => formatear(v, panel.unidad)} />} />
          </PieChart>
          <ul className="grid gap-1.5 text-xs">
            {valores.map((v, i) => (
              <li key={`${v.nombre}-${i}`} className="grid gap-0.5">
                <span className="flex min-w-0 items-center gap-1.5 text-slate-600">
                  <span className="size-2 shrink-0 rounded-full" style={{ backgroundColor: color(panel.colores[v.nombre]) ?? colorSerie(i) }} aria-hidden />
                  <span className="truncate" title={v.nombre}>{v.nombre}</span>
                </span>
                <span className="pl-3.5 font-medium whitespace-nowrap tabular-nums">
                  {formatear(v.valor, panel.unidad)} <span className="text-slate-400">· {Math.round(((v.valor ?? 0) / total) * 100)} %</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Tarjeta>
  )
}

// --- texto y alertas ---------------------------------------------------------------------------------------------

export function PanelTexto({ panel, indice }: { panel: PanelCuadro; indice: number }) {
  return (
    <Tarjeta panel={panel} indice={indice} className="bg-[#f6f9ff]">
      <Markdown texto={panel.texto ?? ''} className="text-[13px] text-slate-600" />
    </Tarjeta>
  )
}

const ESTADOS: Record<string, { texto: string; clase: string; icono: typeof CheckCircle2 }> = {
  firing: { texto: 'Disparada', clase: 'bg-red-50 text-red-700', icono: AlertTriangle },
  pending: { texto: 'Pendiente', clase: 'bg-amber-50 text-amber-700', icono: Clock3 },
  inactive: { texto: 'Normal', clase: 'bg-emerald-50 text-emerald-700', icono: CheckCircle2 },
}

export function PanelAlertas({ panel, indice }: { panel: PanelCuadro; indice: number }) {
  const alertas: AlertaPanel[] = panel.alertas ?? []
  return (
    <Tarjeta panel={panel} indice={indice}>
      {alertas.length === 0 ? (
        <SinDatos texto="Sin reglas de alerta" />
      ) : (
        <ul className="grid gap-2 overflow-y-auto">
          {alertas.map((alerta) => {
            const estado = ESTADOS[alerta.estado] ?? ESTADOS.inactive
            const Icono = estado.icono
            return (
              <li key={alerta.nombre} className="flex items-start gap-2.5">
                <span className={cn('mt-0.5 inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold', estado.clase)}>
                  <Icono className="size-3" aria-hidden />
                  {estado.texto}
                </span>
                <span className="min-w-0">
                  <span className="block text-[13px] font-medium text-slate-700">{alerta.nombre}</span>
                  {alerta.resumen && <span className="block text-xs text-slate-500">{alerta.resumen}</span>}
                </span>
              </li>
            )
          })}
        </ul>
      )}
    </Tarjeta>
  )
}
