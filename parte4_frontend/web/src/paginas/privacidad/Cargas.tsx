/**
 * Pestaña «Cargas»: cada carga histórica en una fila legible. Los viajes y cada agrupación
 * se leen con su etiqueta (publicados, sin cifra, de más), y el detalle abre el fichero y los descartes.
 */
import { ChevronDown, ChevronRight } from 'lucide-react'
import { Fragment, useState } from 'react'

import { useCargas } from '@/api/auditoria'
import type { Carga, Nivel } from '@/api/tipos'
import { formatearFechaHora, formatearNumero } from '@/componentes/chat/formato'
import { EstadoCargando, EstadoError, EstadoVacio } from '@/componentes/shell'
import { Button } from '@/componentes/ui/button'
import { Card, CardContent } from '@/componentes/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/componentes/ui/table'
import { cn } from '@/lib/utils'

import { NOMBRE_NIVEL } from './etiquetas'

const NIVELES: Nivel[] = ['hora_zona', 'dia_barrio', 'od_dia_barrio']

const TITULO_NIVEL: Record<string, string> = {
  hora_zona: 'Por hora y zona',
  dia_barrio: 'Por día y barrio',
  od_dia_barrio: 'Entre barrios',
}

function tituloNivel(nivel: string): string {
  return TITULO_NIVEL[nivel] ?? NOMBRE_NIVEL[nivel as Nivel] ?? nivel.replaceAll('_', ' ')
}

function nivelesDe(cargas: Carga[]): string[] {
  const vistos = new Set<string>(NIVELES)
  for (const carga of cargas) {
    for (const nivel of Object.keys(carga.grupos_publicados ?? {})) vistos.add(nivel)
  }
  return [...vistos]
}

function Linea({ valor, etiqueta, clase, titulo }: { valor: string; etiqueta: string; clase?: string; titulo?: string }) {
  return (
    <li className="flex items-baseline gap-1.5" title={titulo}>
      <span className={cn('cifra font-medium', clase)}>{valor}</span>
      <span className="text-texto-suave">{etiqueta}</span>
    </li>
  )
}

function CifrasViajes({ carga }: { carga: Carga }) {
  return (
    <ul className="space-y-1 text-sm">
      <Linea valor={formatearNumero(carga.filas)} etiqueta="leídos" />
      <Linea valor={formatearNumero(carga.validos)} etiqueta="válidos" clase="text-ok" />
      <Linea
        valor={formatearNumero(carga.rechazados)}
        etiqueta="descartados"
        clase={carga.rechazados > 0 ? 'text-aviso' : 'text-texto-suave'}
      />
    </ul>
  )
}

function CifrasNivel({ carga, nivel }: { carga: Carga; nivel: string }) {
  const publicados = carga.grupos_publicados?.[nivel]
  const suprimidos = carga.grupos_suprimidos?.[nivel]
  const complementarios = carga.grupos_complementarios?.[nivel]
  if (publicados === undefined && suprimidos === undefined) {
    return <span className="text-sm text-texto-suave">Sin datos</span>
  }
  return (
    <ul className="space-y-1 text-sm">
      <Linea valor={formatearNumero(publicados)} etiqueta="publicados" titulo="Grupos que se guardaron, incluidos los que van sin cifra" />
      <Linea
        valor={formatearNumero(suprimidos)}
        etiqueta="sin cifra"
        clase="text-enmascarado"
        titulo="Grupos con menos de 10 viajes, o ocultos de más, que se publican vacíos"
      />
      <Linea
        valor={complementarios === undefined ? '—' : formatearNumero(complementarios)}
        etiqueta="de más"
        clase="text-texto-suave"
        titulo="Grupos visibles que también se ocultan para que no se pueda calcular el resto restando"
      />
    </ul>
  )
}

function nombreOrigen(origen: string): string {
  if (origen === 'historico') return 'Histórico'
  if (origen === 'tiempo_real') return 'Tiempo real'
  return origen
}

function DetalleCarga({ carga }: { carga: Carga }) {
  const motivos = Object.entries(carga.motivos ?? {}).sort((a, b) => b[1] - a[1])
  const maximo = Math.max(1, ...motivos.map(([, cantidad]) => cantidad))
  return (
    <div className="border-t border-borde bg-[#f8fafc] px-4 py-4 sm:px-5">
      <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.35fr)]">
        <div>
          <p className="text-sm font-semibold text-primario">De dónde salió</p>
          <dl className="mt-2 space-y-2.5 text-sm">
            <div>
              <dt className="text-texto-suave">Fichero</dt>
              <dd className="mt-0.5 font-mono text-[13px] leading-snug break-all text-slate-700">{carga.entrada}</dd>
            </div>
            <div className="flex flex-wrap gap-x-8 gap-y-2">
              <div>
                <dt className="text-texto-suave">Origen</dt>
                <dd className="mt-0.5 font-medium text-slate-800">{nombreOrigen(carga.origen)}</dd>
              </div>
              <div>
                <dt className="text-texto-suave">Reglas</dt>
                <dd className="mt-0.5 font-medium text-slate-800">Versión {carga.version_reglas}</dd>
              </div>
            </div>
          </dl>
        </div>
        <div>
          <p className="text-sm font-semibold text-primario">Por qué se descartaron</p>
          {motivos.length === 0 ? (
            <p className="mt-2 text-sm text-texto-suave">Ningún viaje se descartó.</p>
          ) : (
            <ul className="mt-2 space-y-2.5" aria-label="Motivos de descarte">
              {motivos.map(([motivo, cantidad]) => {
                const parte = carga.rechazados > 0 ? Math.round((cantidad / carga.rechazados) * 100) : 0
                return (
                  <li key={motivo}>
                    <div className="flex items-baseline justify-between gap-3 text-sm">
                      <span className="text-slate-800">{motivo}</span>
                      <span className="cifra shrink-0 text-texto-suave">
                        <span className="font-medium text-slate-800">{formatearNumero(cantidad)}</span>
                        {parte > 0 ? ` · ${parte} %` : ''}
                      </span>
                    </div>
                    <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white ring-1 ring-borde">
                      <div className="h-full rounded-full bg-aviso" style={{ width: `${Math.max(6, (cantidad / maximo) * 100)}%` }} />
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}

function TablaCargas({ cargas }: { cargas: Carga[] }) {
  const niveles = nivelesDe(cargas)
  const [abiertas, setAbiertas] = useState<Set<number>>(() => new Set())
  const alternar = (indice: number) =>
    setAbiertas((previas) => {
      const siguientes = new Set(previas)
      if (siguientes.has(indice)) siguientes.delete(indice)
      else siguientes.add(indice)
      return siguientes
    })
  const columnas = 4 + niveles.length

  return (
    <Table className="text-sm">
      <TableHeader>
        <TableRow className="bg-superficie-alterna/60 hover:bg-superficie-alterna/60">
          <TableHead scope="col" className="w-8">
            <span className="sr-only">Detalle</span>
          </TableHead>
          <TableHead scope="col">Cuándo</TableHead>
          <TableHead scope="col">Lote</TableHead>
          <TableHead scope="col">Viajes del fichero</TableHead>
          {niveles.map((nivel) => (
            <TableHead key={nivel} scope="col" className="align-bottom">
              {tituloNivel(nivel)}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {cargas.map((carga, indice) => {
          const abierta = abiertas.has(indice)
          return (
            <Fragment key={`${carga.lote}-${carga.instante}`}>
              <TableRow
                className={cn('cursor-pointer', abierta && 'bg-slate-100 hover:bg-slate-100')}
                onClick={() => alternar(indice)}
              >
                <TableCell className="py-1 align-top">
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    onClick={(evento) => {
                      evento.stopPropagation()
                      alternar(indice)
                    }}
                    aria-expanded={abierta}
                    aria-label={abierta ? 'Ocultar el detalle' : 'Ver el detalle'}
                  >
                    {abierta ? <ChevronDown aria-hidden /> : <ChevronRight aria-hidden />}
                  </Button>
                </TableCell>
                <TableCell className="cifra align-top text-texto-suave">{formatearFechaHora(carga.instante)}</TableCell>
                <TableCell className="align-top font-medium">{carga.lote}</TableCell>
                <TableCell className="align-top whitespace-normal">
                  <CifrasViajes carga={carga} />
                </TableCell>
                {niveles.map((nivel) => (
                  <TableCell key={nivel} className="align-top whitespace-normal">
                    <CifrasNivel carga={carga} nivel={nivel} />
                  </TableCell>
                ))}
              </TableRow>
              {abierta && (
                <TableRow className="bg-slate-50 hover:bg-slate-50">
                  <TableCell colSpan={columnas} className="p-0 whitespace-normal">
                    <DetalleCarga carga={carga} />
                  </TableCell>
                </TableRow>
              )}
            </Fragment>
          )
        })}
      </TableBody>
    </Table>
  )
}

export function Cargas() {
  const cargas = useCargas()
  return (
    <Card className="sombra-tarjeta">
      <CardContent>
        {cargas.isPending ? (
          <EstadoCargando lineas={6} etiqueta="Cargando las cargas históricas…" />
        ) : cargas.isError ? (
          <EstadoError
            titulo="No se han podido leer las cargas"
            error={cargas.error}
            alReintentar={() => void cargas.refetch()}
            reintentando={cargas.isFetching}
          />
        ) : cargas.data.length === 0 ? (
          <EstadoVacio
            titulo="Todavía no hay cargas"
            descripcion="Lanza una carga histórica desde Operaciones (o con make historico-muestra) y aparecerá aquí al terminar."
          />
        ) : (
          <TablaCargas cargas={cargas.data} />
        )}
      </CardContent>
    </Card>
  )
}
