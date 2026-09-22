/**
 * Matriz origen → destino (mapa de calor) para los flujos entre barrios. Es una tabla HTML accesible
 * (`<th scope>`), con las celdas coloreadas por intensidad (escala logarítmica, porque Manhattan→Manhattan
 * aplasta al resto) y las celdas enmascaradas en violeta con «oculto».
 */
import { Lock } from 'lucide-react'
import { useMemo } from 'react'

import { formatearEntero, pluralizar } from '@/componentes/datos/formato'
import { cn } from '@/lib/utils'

export interface CeldaFlujo {
  origen: string
  destino: string
  /** Suma de los grupos visibles; `null` si no hay ninguno visible. */
  valor: number | null
  /** Grupos enmascarados en la celda (nunca se suman). */
  enmascarados: number
  visibles: number
}

interface Props {
  celdas: readonly CeldaFlujo[]
  formatearValor?: (valor: number) => string
  /** Descripción accesible de la tabla. */
  titulo: string
  className?: string
}

function ordenarBarrios(celdas: readonly CeldaFlujo[], clave: 'origen' | 'destino'): string[] {
  const totales = new Map<string, number>()
  for (const c of celdas) totales.set(c[clave], (totales.get(c[clave]) ?? 0) + (c.valor ?? 0))
  return [...totales.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'es')).map(([b]) => b)
}

export function MatrizFlujos({ celdas, formatearValor = formatearEntero, titulo, className }: Props) {
  const { origenes, destinos, porClave, maximo } = useMemo(() => {
    const porClave = new Map<string, CeldaFlujo>()
    let maximo = 0
    for (const c of celdas) {
      porClave.set(`${c.origen}→${c.destino}`, c)
      if (c.valor !== null) maximo = Math.max(maximo, c.valor)
    }
    return { origenes: ordenarBarrios(celdas, 'origen'), destinos: ordenarBarrios(celdas, 'destino'), porClave, maximo }
  }, [celdas])

  if (celdas.length === 0) return null

  const intensidad = (valor: number) => (maximo <= 0 ? 0 : Math.log1p(valor) / Math.log1p(maximo))

  return (
    <div className={cn('overflow-x-auto', className)}>
      <table className="w-full border-separate border-spacing-1 text-xs" aria-label={titulo}>
        <thead>
          <tr>
            <th scope="col" className="px-2 py-1 text-left font-medium text-texto-suave">
              Origen ↓ · Destino →
            </th>
            {destinos.map((d) => (
              <th key={d} scope="col" className="px-2 py-1 text-center font-semibold text-foreground">
                {d}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {origenes.map((o) => (
            <tr key={o}>
              <th scope="row" className="px-2 py-1 text-left font-semibold whitespace-nowrap text-foreground">
                {o}
              </th>
              {destinos.map((d) => {
                const celda = porClave.get(`${o}→${d}`)
                if (!celda || (celda.valor === null && celda.enmascarados === 0)) {
                  return (
                    <td key={d} className="h-10 min-w-16 rounded-md bg-superficie-alterna/60 text-center text-texto-suave" title={`${o} → ${d}: sin grupos`}>
                      —
                    </td>
                  )
                }
                if (celda.valor === null) {
                  return (
                    <td
                      key={d}
                      data-enmascarada="true"
                      className="h-10 min-w-16 rounded-md border border-enmascarado/30 bg-enmascarado-suave text-center font-semibold text-enmascarado"
                      title={`${o} → ${d}: ${pluralizar(celda.enmascarados, 'grupo enmascarado', 'grupos enmascarados')} por privacidad`}
                    >
                      <span className="inline-flex items-center gap-1">
                        <Lock className="size-3" aria-hidden />
                        {'oculto'}
                      </span>
                    </td>
                  )
                }
                const fuerza = intensidad(celda.valor)
                const parcial = celda.enmascarados > 0
                return (
                  <td
                    key={d}
                    className={cn('cifra h-10 min-w-16 rounded-md text-center font-medium', fuerza > 0.6 ? 'text-white' : 'text-foreground')}
                    style={{ background: `color-mix(in srgb, var(--primario) ${Math.round(8 + fuerza * 92)}%, white)` }}
                    title={`${o} → ${d}: ${formatearValor(celda.valor)} viajes en ${pluralizar(celda.visibles, 'grupo visible', 'grupos visibles')}${
                      parcial ? ` · ${pluralizar(celda.enmascarados, 'grupo enmascarado', 'grupos enmascarados')} no incluidos` : ''
                    }`}
                  >
                    {formatearValor(celda.valor)}
                    {parcial && <span className="ml-1 align-middle text-enmascarado" aria-label="con grupos enmascarados">*</span>}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 flex flex-wrap items-center gap-3 text-xs text-texto-suave">
        <span className="inline-flex items-center gap-1">
          <span className="inline-block size-3 rounded-sm" style={{ background: 'color-mix(in srgb, var(--primario) 12%, white)' }} aria-hidden /> pocos viajes
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block size-3 rounded-sm bg-primario" aria-hidden /> muchos viajes (escala logarítmica)
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block size-3 rounded-sm border border-enmascarado/40 bg-enmascarado-suave" aria-hidden /> enmascarado (&lt;10)
        </span>
        <span>* celda con algún grupo enmascarado no incluido en la suma</span>
      </p>
    </div>
  )
}
