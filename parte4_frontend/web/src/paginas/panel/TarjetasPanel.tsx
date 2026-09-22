/**
 * Las cuatro tarjetas del panel. La cifra va en una sola línea; al lado, barras de lo que la compone.
 * La frescura no usa la frase larga: el número y la unidad quedan juntos. Cuando el panel se refresca y una
 * cifra cambia, el número recorre el camino hasta el valor nuevo (`useNumeroAnimado`) y las barras con él.
 */
import { Activity, MapPinned, Route, ShieldCheck, type LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

import type { PanelExtendido } from '@/api/panel'
import { describirAntiguedad, formatearEntero } from '@/componentes/datos/formato'
import { useSegundosDesde } from '@/componentes/datos/useAhora'
import { useNumeroAnimado } from '@/componentes/datos/useNumeroAnimado'
import { Semaforo } from '@/componentes/graficos/Semaforo'
import { nivelFrescura, TEXTO_FRESCURA, type NivelFrescura } from '@/componentes/graficos/frescura'
import { cn } from '@/lib/utils'

import { MiniBarras } from './MiniBarras'
import { MiniSerie } from './MiniSerie'

const VERDE = '#17875a'
const AZUL = '#2f62c4'

const ONDA: Record<NivelFrescura, number[]> = {
  ok: [8, 12, 10, 16, 14, 22, 20, 28],
  aviso: [14, 16, 13, 15, 12, 14, 13, 15],
  peligro: [28, 24, 26, 18, 16, 12, 10, 6],
}

const TONO_FRESCURA: Record<NivelFrescura, { icono: string; serie: string }> = {
  ok: { icono: 'bg-[#e8faf2] text-[#17875a]', serie: '#3dbe8b' },
  aviso: { icono: 'bg-[#fff6e4] text-[#b7791f]', serie: '#f0b429' },
  peligro: { icono: 'bg-[#fff1ea] text-[#c45c32]', serie: '#e8926a' },
}

function serieDescendente(porBarrio: Record<string, number> | undefined): number[] {
  if (!porBarrio) return []
  return Object.values(porBarrio).sort((a, b) => b - a)
}

function esCifra(valor: string): boolean {
  return valor === 'Sin dato' || valor === 'Sin datos' || /^[\d.]+$/.test(valor)
}

function Kpi({
  titulo,
  valor,
  icono: Icono,
  iconoClase,
  grafico,
  detalle,
  etiqueta,
}: {
  titulo: string
  valor: ReactNode
  icono: LucideIcon
  iconoClase: string
  grafico?: ReactNode
  detalle?: ReactNode
  etiqueta?: string
}) {
  const texto = typeof valor === 'string'
  const grande = texto && esCifra(valor)
  return (
    <article className="flex items-center gap-3 rounded-2xl border border-[#e6edf5] bg-white px-4 py-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_10px_28px_rgba(15,23,42,0.05)] sm:px-5">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2.5">
          <span className={cn('flex size-9 shrink-0 items-center justify-center rounded-xl', iconoClase)} aria-hidden>
            <Icono className="size-4" strokeWidth={2.25} />
          </span>
          <p className="text-sm font-medium text-slate-500">{titulo}</p>
        </div>
        <div className="mt-3 min-w-0" aria-label={etiqueta}>
          {texto ? (
            <p className={cn(grande ? 'cifra text-[1.7rem] leading-none font-semibold tracking-tight whitespace-nowrap text-slate-900' : 'text-sm leading-snug font-medium text-amber-700')}>
              {valor}
            </p>
          ) : (
            valor
          )}
        </div>
        {detalle && <div className="mt-2">{detalle}</div>}
      </div>
      {grafico}
    </article>
  )
}

function PartesTiempo({ segundos }: { segundos: number }) {
  const s = Math.max(0, Math.floor(segundos))
  const partes: { n: string; u: string }[] = []
  if (s < 60) partes.push({ n: String(s), u: 's' })
  else if (s < 3600) {
    const min = Math.floor(s / 60)
    const resto = s % 60
    partes.push({ n: String(min), u: 'min' })
    if (resto) partes.push({ n: String(resto), u: 's' })
  } else if (s < 86400) {
    const horas = Math.floor(s / 3600)
    const resto = Math.floor((s % 3600) / 60)
    partes.push({ n: String(horas), u: 'h' })
    if (resto) partes.push({ n: String(resto), u: 'min' })
  } else partes.push({ n: String(Math.floor(s / 86400)), u: 'd' })

  return (
    <p className="flex items-baseline gap-x-2 whitespace-nowrap text-slate-900">
      {partes.map((parte) => (
        <span key={parte.u + parte.n} className="inline-flex items-baseline gap-0.5">
          <span className="cifra text-[1.7rem] leading-none font-semibold tracking-tight">{parte.n}</span>
          <span className="text-sm font-medium text-slate-400">{parte.u}</span>
        </span>
      ))}
    </p>
  )
}

function KpiFrescura({ segundos, actualizadoEn, disponible }: { segundos: number | null; actualizadoEn: number; disponible: boolean }) {
  const transcurridos = useSegundosDesde(actualizadoEn)
  const actuales = segundos == null ? null : segundos + (transcurridos ?? 0)
  const nivel = nivelFrescura(actuales)
  const tono = TONO_FRESCURA[nivel]

  if (!disponible) {
    return <Kpi titulo="Frescura" valor="Prometheus no disponible" icono={Activity} iconoClase="bg-slate-100 text-slate-400" />
  }

  return (
    <Kpi
      titulo="Frescura"
      icono={Activity}
      iconoClase={tono.icono}
      etiqueta={actuales == null ? 'Sin dato' : describirAntiguedad(actuales)}
      valor={actuales == null ? 'Sin dato' : <PartesTiempo segundos={actuales} />}
      grafico={<MiniSerie valores={ONDA[nivel]} color={tono.serie} />}
      detalle={<Semaforo nivel={nivel} etiqueta={TEXTO_FRESCURA[nivel]} tamano="sm" className="text-xs" />}
    />
  )
}

interface Props {
  panel: PanelExtendido
  /** `dataUpdatedAt` de la consulta, para que el contador de frescura avance. */
  actualizadoEn: number
}

export function TarjetasPanel({ panel, actualizadoEn }: Props) {
  const historico = panel.ultimo_dia?.historico ?? null
  const barrios = historico ? Object.keys(historico.por_barrio).length : 0
  const decisiones = panel.consultas_24h
  const totalDecisiones = decisiones ? decisiones.permitida + decisiones.enmascarada + decisiones.rechazada : 0
  const prometheus = panel.prometheus_disponible !== false
  const acceso = panel.acceso_disponible !== false
  const serie = serieDescendente(historico?.por_barrio)
  const sinDia = !acceso && !historico
  const viajesAnimados = useNumeroAnimado(historico?.total ?? null)
  const decisionesAnimadas = useNumeroAnimado(prometheus && decisiones ? totalDecisiones : null)

  return (
    <section aria-label="Indicadores" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Kpi
        titulo="Viajes"
        valor={sinDia ? 'API de acceso no disponible' : historico ? formatearEntero(viajesAnimados) : 'Sin datos'}
        icono={Route}
        iconoClase="bg-[#e8faf2] text-[#17875a]"
        grafico={historico ? <MiniBarras valores={serie} color={VERDE} /> : undefined}
      />
      <Kpi
        titulo="Barrios"
        valor={sinDia ? 'API de acceso no disponible' : historico ? formatearEntero(barrios) : 'Sin datos'}
        icono={MapPinned}
        iconoClase="bg-[#eaf2ff] text-[#2f62c4]"
        grafico={historico ? <MiniBarras valores={serie} color={AZUL} /> : undefined}
      />
      <Kpi
        titulo="Decisiones"
        valor={prometheus && decisiones ? formatearEntero(decisionesAnimadas) : 'Prometheus no disponible'}
        icono={ShieldCheck}
        iconoClase={prometheus && decisiones ? 'bg-[#e7f8f8] text-[#0e7c7c]' : 'bg-slate-100 text-slate-400'}
        grafico={
          prometheus && decisiones ? (
            <MiniBarras valores={[decisiones.permitida, decisiones.enmascarada, decisiones.rechazada]} colores={['#17875a', '#6d4eae', '#c45c32']} />
          ) : undefined
        }
      />
      <KpiFrescura segundos={panel.frescura_tiempo_real?.segundos ?? null} actualizadoEn={actualizadoEn} disponible={prometheus} />
    </section>
  )
}
