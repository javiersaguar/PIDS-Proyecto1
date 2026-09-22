/**
 * Un cuadro de Grafana con la misma disposición que en Grafana: la rejilla de 24 columnas y la posición de cada
 * panel (`gridPos`). En pantallas estrechas los paneles se apilan en el orden en que se leen. Cada panel entra con
 * un pequeño retraso respecto al anterior, como las tarjetas del panel principal.
 */
import type { CSSProperties } from 'react'

import type { Cuadro, PanelCuadro } from '@/api/observabilidad'

import { altoPanel } from './formatoUnidad'
import { PanelAlertas, PanelBarras, PanelSerie, PanelStat, PanelTarta, PanelTexto } from './Paneles'

const COMPONENTES = {
  stat: PanelStat,
  serie: PanelSerie,
  barras: PanelBarras,
  tarta: PanelTarta,
  texto: PanelTexto,
  alertas: PanelAlertas,
} as const

function posicion(panel: PanelCuadro): CSSProperties {
  return {
    '--columna': `${panel.x + 1} / span ${panel.ancho}`,
    '--fila': `${panel.y + 1} / span ${panel.alto}`,
    '--alto': `${altoPanel(panel.alto)}px`,
  } as CSSProperties
}

export function CuadroNativo({ cuadro }: { cuadro: Cuadro }) {
  const paneles = [...cuadro.paneles].sort((a, b) => a.y - b.y || a.x - b.x)
  const orden = new Map(paneles.filter((p) => p.tipo !== 'fila').map((p, i) => [p.id, i]))
  return (
    <div className="@container">
      <div className="grid grid-cols-1 gap-3 @3xl:grid-cols-24 @3xl:auto-rows-[28px]">
        {paneles.map((panel) => {
          const clases = '@3xl:[grid-column:var(--columna)] @3xl:[grid-row:var(--fila)]'
          if (panel.tipo === 'fila') {
            return (
              <h2
                key={panel.id}
                style={posicion(panel)}
                className={`${clases} flex items-end pt-2 text-xs font-semibold tracking-wide text-slate-500 uppercase first:pt-0`}
              >
                {panel.titulo}
              </h2>
            )
          }
          const Componente = COMPONENTES[panel.tipo]
          if (!Componente) return null
          return (
            <div key={panel.id} style={posicion(panel)} className={`${clases} flex min-h-(--alto) min-w-0 flex-col *:flex-1 @3xl:min-h-0`}>
              <Componente panel={panel} indice={orden.get(panel.id) ?? 0} />
            </div>
          )
        })}
      </div>
    </div>
  )
}
