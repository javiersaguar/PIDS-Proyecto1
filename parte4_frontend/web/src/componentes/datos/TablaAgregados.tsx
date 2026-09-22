/**
 * Tabla ordenable de filas de agregados (`Fila` del §5). Las columnas dependen del nivel y de las métricas
 * pedidas; los grupos enmascarados llevan el chip violeta «enmascarado por privacidad» y `oculto`, sin cifras.
 * El total del pie suma solo los grupos visibles: los enmascarados se cuentan, nunca se suman.
 */
import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'

import type { Fila, Metrica, Nivel } from '@/api/tipos'
import { TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from '@/componentes/ui/table'
import { cn } from '@/lib/utils'

import {
  columnasDe,
  compararPor,
  esEnmascarada,
  textoCelda,
  totalesDe,
  type ClaveColumna,
  type Columna,
  type Direccion,
} from './agregados'
import { ChipEnmascarado } from './ChipResultado'
import { formatearEntero, pluralizar } from './formato'

export interface Orden {
  clave: ClaveColumna
  direccion: Direccion
}

interface Props {
  filas: readonly Fila[]
  nivel: Nivel
  /** Métricas pedidas en la consulta (`n_viajes` se incluye siempre). */
  metricas?: readonly Metrica[]
  ordenInicial?: Orden
  /** Pie con el total de viajes de los grupos visibles. */
  conTotal?: boolean
  /** Texto para lectores de pantalla (`aria-label` de la tabla). */
  titulo?: string
  /** Qué mostrar si no hay filas. */
  vacio?: ReactNode
  /** Clase del contenedor con desplazamiento (por defecto, 32 rem de alto máximo). */
  className?: string
}

function direccionPorDefecto(columna: Columna): Direccion {
  return columna.numerica ? 'desc' : 'asc'
}

function IconoOrden({ activo, direccion }: { activo: boolean; direccion: Direccion }) {
  if (!activo) return <ArrowUpDown className="size-3.5 text-texto-suave/60" aria-hidden />
  return direccion === 'asc' ? <ArrowUp className="size-3.5" aria-hidden /> : <ArrowDown className="size-3.5" aria-hidden />
}

export function TablaAgregados({
  filas,
  nivel,
  metricas = ['n_viajes'],
  ordenInicial,
  conTotal = false,
  titulo = 'Agregados',
  vacio,
  className,
}: Props) {
  const columnas = useMemo(() => columnasDe(nivel, metricas), [nivel, metricas])
  const [orden, setOrden] = useState<Orden | null>(ordenInicial ?? null)

  const ordenadas = useMemo(() => {
    if (!orden) return filas
    return [...filas].sort(compararPor(orden.clave, orden.direccion))
  }, [filas, orden])

  const totales = useMemo(() => totalesDe(filas), [filas])
  const indiceViajes = columnas.findIndex((c) => c.clave === 'n_viajes')
  // Con muchas columnas (varias métricas) el chip largo no cabe: se usa el corto, con el texto completo en el título.
  const chipCorto = columnas.length > 5

  const cambiarOrden = (columna: Columna) => {
    setOrden((actual) => {
      if (actual?.clave === columna.clave) {
        return { clave: columna.clave, direccion: actual.direccion === 'asc' ? 'desc' : 'asc' }
      }
      return { clave: columna.clave, direccion: direccionPorDefecto(columna) }
    })
  }

  if (filas.length === 0 && vacio) {
    return <>{vacio}</>
  }

  return (
    <div className={cn('relative max-h-[32rem] overflow-auto rounded-lg border bg-superficie', className)}>
      <table className="w-full caption-bottom text-sm" aria-label={titulo}>
        <TableHeader className="sticky top-0 z-10 bg-superficie-alterna">
          <TableRow className="hover:bg-transparent">
            {columnas.map((columna) => {
              const activa = orden?.clave === columna.clave
              const ariaSort = activa ? (orden.direccion === 'asc' ? 'ascending' : 'descending') : 'none'
              return (
                <TableHead key={columna.clave} scope="col" aria-sort={ariaSort} className={cn(columna.numerica && 'text-right')}>
                  <button
                    type="button"
                    onClick={() => cambiarOrden(columna)}
                    className={cn(
                      'inline-flex items-center gap-1 rounded-sm text-xs font-semibold text-texto-suave hover:text-foreground',
                      activa && 'text-foreground',
                      columna.numerica && 'flex-row-reverse',
                    )}
                  >
                    {columna.titulo}
                    <IconoOrden activo={activa} direccion={orden?.direccion ?? 'asc'} />
                  </button>
                </TableHead>
              )
            })}
          </TableRow>
        </TableHeader>
        <TableBody>
          {ordenadas.map((fila, indice) => {
            const enmascarada = esEnmascarada(fila)
            return (
              <TableRow key={claveFila(fila, indice)} data-enmascarada={enmascarada || undefined} className={cn(enmascarada && 'bg-enmascarado-suave/40')}>
                {columnas.map((columna) => (
                  <TableCell key={columna.clave} className={cn('cifra', columna.numerica && 'text-right', columna.clave === 'zona_origen' && 'whitespace-normal')}>
                    {columna.clave === 'n_viajes' && enmascarada ? (
                      <span className="inline-flex items-center justify-end gap-2">
                        <ChipEnmascarado corto={chipCorto} />
                        <span className="font-semibold text-enmascarado">{textoCelda(fila, columna.clave)}</span>
                      </span>
                    ) : columna.clave === 'zona_origen' ? (
                      <span>
                        {textoCelda(fila, columna.clave)}
                        {fila.zona_origen != null && <span className="ml-1.5 text-xs text-texto-suave">#{fila.zona_origen}</span>}
                      </span>
                    ) : (
                      textoCelda(fila, columna.clave)
                    )}
                  </TableCell>
                ))}
              </TableRow>
            )
          })}
        </TableBody>
        {conTotal && filas.length > 0 && (
          <TableFooter className="sticky bottom-0 bg-superficie-alterna">
            <TableRow className="hover:bg-transparent">
              <TableCell colSpan={indiceViajes} className="text-xs whitespace-normal text-texto-suave">
                Total de los grupos visibles ({pluralizar(totales.visibles, 'grupo')})
                {totales.enmascarados > 0 && (
                  <span className="text-enmascarado"> · {pluralizar(totales.enmascarados, 'enmascarado')} no incluidos</span>
                )}
              </TableCell>
              <TableCell className="cifra text-right font-semibold">{formatearEntero(totales.total)}</TableCell>
              {columnas.length > indiceViajes + 1 && <TableCell colSpan={columnas.length - indiceViajes - 1} />}
            </TableRow>
          </TableFooter>
        )}
      </table>
    </div>
  )
}

function claveFila(fila: Fila, indice: number): string {
  return [fila.hora ?? fila.dia ?? '', fila.zona_origen ?? '', fila.barrio_origen ?? '', fila.barrio_destino ?? '', indice].join('|')
}
