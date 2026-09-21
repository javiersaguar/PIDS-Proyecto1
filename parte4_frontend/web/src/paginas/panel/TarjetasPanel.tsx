/**
 * Las cuatro tarjetas KPI del panel: viajes del último día publicado, barrios con datos, decisiones de las
 * últimas 24 h y frescura del tiempo real. Las dos últimas dependen de Prometheus: si no está disponible se
 * muestra «no disponible» en ellas sin tocar las demás.
 */
import { Activity, CalendarDays, MapPinned, ShieldCheck } from 'lucide-react'

import type { PanelExtendido } from '@/api/panel'
import { ChipResultado, Frescura, TarjetaKpi } from '@/componentes/datos'
import { formatearEntero, formatearFecha, formatearPorcentaje } from '@/componentes/datos/formato'
import { EstadoNoDisponible } from '@/componentes/shell'

interface Props {
  panel: PanelExtendido
  /** `dataUpdatedAt` de la consulta, para que el contador de frescura avance. */
  actualizadoEn: number
}

function barrioPrincipal(porBarrio: Record<string, number>, total: number): string | null {
  const entradas = Object.entries(porBarrio)
  if (!entradas.length || total <= 0) return null
  const [barrio, viajes] = entradas.reduce((max, actual) => (actual[1] > max[1] ? actual : max))
  return `${barrio} concentra el ${formatearPorcentaje((viajes / total) * 100)}`
}

function NoDisponibleCompacto({ servicio = 'Prometheus' }: { servicio?: string }) {
  return (
    <EstadoNoDisponible
      servicio={servicio}
      descripcion={servicio === 'Prometheus' ? 'Sin estado ni contadores mientras no responda.' : 'Sin cifras del último día mientras no responda.'}
      className="py-4"
    />
  )
}

export function TarjetasPanel({ panel, actualizadoEn }: Props) {
  const historico = panel.ultimo_dia?.historico ?? null
  const barrios = historico ? Object.keys(historico.por_barrio).length : 0
  const decisiones = panel.consultas_24h
  const totalDecisiones = decisiones ? decisiones.permitida + decisiones.enmascarada + decisiones.rechazada : 0
  const prometheus = panel.prometheus_disponible !== false
  const acceso = panel.acceso_disponible !== false

  return (
    <section aria-label="Indicadores" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <TarjetaKpi
        titulo="Viajes del último día publicado"
        icono={CalendarDays}
        valor={!acceso && !historico ? <NoDisponibleCompacto servicio="API de acceso" /> : historico ? formatearEntero(historico.total) : 'Sin datos'}
        descripcion={
          historico
            ? `${formatearFecha(historico.dia)} · histórico · solo grupos visibles`
            : acceso
              ? 'No hay agregados históricos publicados todavía.'
              : undefined
        }
      />
      <TarjetaKpi
        titulo="Barrios con datos"
        icono={MapPinned}
        valor={!acceso && !historico ? <NoDisponibleCompacto servicio="API de acceso" /> : historico ? formatearEntero(barrios) : 'Sin datos'}
        descripcion={
          historico
            ? (barrioPrincipal(historico.por_barrio, historico.total) ?? 'Grupos visibles del último día')
            : acceso
              ? 'Sin último día publicado.'
              : undefined
        }
      />
      <TarjetaKpi
        titulo="Decisiones · últimas 24 h"
        icono={ShieldCheck}
        valor={prometheus && decisiones ? formatearEntero(totalDecisiones) : undefined}
        descripcion={prometheus && decisiones ? 'Consultas a la API de acceso, por resultado' : undefined}
        pie={
          prometheus && decisiones ? (
            <ul className="flex flex-wrap gap-1.5" aria-label="Decisiones por resultado">
              <li>
                <ChipResultado resultado="permitida" cantidad={formatearEntero(decisiones.permitida)} />
              </li>
              <li>
                <ChipResultado resultado="enmascarada" cantidad={formatearEntero(decisiones.enmascarada)} />
              </li>
              <li>
                <ChipResultado resultado="rechazada" cantidad={formatearEntero(decisiones.rechazada)} />
              </li>
            </ul>
          ) : (
            <NoDisponibleCompacto />
          )
        }
      />
      <TarjetaKpi
        titulo="Frescura del tiempo real"
        icono={Activity}
        valor={
          prometheus ? (
            <Frescura
              variante="grande"
              segundos={panel.frescura_tiempo_real?.segundos ?? null}
              instante={panel.frescura_tiempo_real?.instante ?? null}
              actualizadoEn={actualizadoEn}
            />
          ) : (
            <NoDisponibleCompacto />
          )
        }
      />
    </section>
  )
}
