/**
 * Pestaña «Cargas»: los resúmenes que `pids.CargaHistorica` escribe en `auditoria.cargas` al terminar cada carga:
 * viajes leídos, válidos y rechazados, y por nivel los grupos publicados, suprimidos y complementarios.
 */
import { ChevronDown, ChevronRight } from 'lucide-react'
import { Fragment, useState } from 'react'

import { useCargas } from '@/api/auditoria'
import type { Carga, Nivel } from '@/api/tipos'
import { formatearFechaHora, formatearNumero } from '@/componentes/chat/formato'
import { EstadoCargando, EstadoError, EstadoVacio } from '@/componentes/shell'
import { Button } from '@/componentes/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/componentes/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/componentes/ui/table'
import { cn } from '@/lib/utils'

import { NOMBRE_NIVEL } from './etiquetas'

const NIVELES: Nivel[] = ['hora_zona', 'dia_barrio', 'od_dia_barrio']

function nivelesDe(cargas: Carga[]): string[] {
  const vistos = new Set<string>(NIVELES)
  for (const carga of cargas) {
    for (const nivel of Object.keys(carga.grupos_publicados ?? {})) vistos.add(nivel)
  }
  return [...vistos]
}

function CeldaNivel({ carga, nivel }: { carga: Carga; nivel: string }) {
  const publicados = carga.grupos_publicados?.[nivel]
  const suprimidos = carga.grupos_suprimidos?.[nivel]
  const complementarios = carga.grupos_complementarios?.[nivel]
  if (publicados === undefined && suprimidos === undefined) return <span className="text-texto-suave">—</span>
  return (
    <span className="cifra inline-flex items-baseline gap-1.5">
      <span title="Grupos publicados (incluidos los suprimidos, que van sin cifras)">{formatearNumero(publicados)}</span>
      <span className="text-texto-suave">/</span>
      <span className="text-enmascarado" title="Grupos suprimidos (menos de 10 viajes o complementarios)">
        {formatearNumero(suprimidos)}
      </span>
      <span className="text-texto-suave">/</span>
      <span className="text-texto-suave" title="Suprimidos solo por la supresión complementaria">
        {complementarios === undefined ? '—' : formatearNumero(complementarios)}
      </span>
    </span>
  )
}

function DetalleCarga({ carga }: { carga: Carga }) {
  const motivos = Object.entries(carga.motivos ?? {}).sort((a, b) => b[1] - a[1])
  return (
    <div className="grid gap-3 py-1 text-xs lg:grid-cols-2">
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
        <dt className="text-texto-suave">Entrada</dt>
        <dd className="font-mono break-all">{carga.entrada}</dd>
        <dt className="text-texto-suave">Origen</dt>
        <dd>{carga.origen}</dd>
        <dt className="text-texto-suave">Versión de las reglas</dt>
        <dd className="cifra">{carga.version_reglas}</dd>
      </dl>
      <div>
        <p className="mb-1 font-medium text-texto-suave">Motivos de rechazo de viajes</p>
        {motivos.length ? (
          <ul className="space-y-0.5">
            {motivos.map(([motivo, cantidad]) => (
              <li key={motivo} className="flex justify-between gap-3">
                <span>{motivo}</span>
                <span className="cifra font-medium">{formatearNumero(cantidad)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-texto-suave">Ningún viaje rechazado.</p>
        )}
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
  const columnas = 6 + niveles.length

  return (
    <Table>
      <TableHeader>
        <TableRow className="bg-superficie-alterna/60 hover:bg-superficie-alterna/60">
          <TableHead scope="col" className="w-8">
            <span className="sr-only">Detalle</span>
          </TableHead>
          <TableHead scope="col">Instante</TableHead>
          <TableHead scope="col">Lote</TableHead>
          <TableHead scope="col" className="text-right">
            Leídos
          </TableHead>
          <TableHead scope="col" className="text-right">
            Válidos
          </TableHead>
          <TableHead scope="col" className="text-right">
            Rechazados
          </TableHead>
          {niveles.map((nivel) => (
            <TableHead key={nivel} scope="col" title={NOMBRE_NIVEL[nivel as Nivel] ?? nivel}>
              <span className="font-mono text-[11px]">{nivel}</span>
              <span className="block text-[10px] font-normal text-texto-suave">publicados / suprimidos / complementarios</span>
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {cargas.map((carga, indice) => {
          const abierta = abiertas.has(indice)
          return (
            <Fragment key={`${carga.lote}-${carga.instante}`}>
              <TableRow className={cn(abierta && 'bg-muted/40')}>
                <TableCell className="py-1">
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    onClick={() => alternar(indice)}
                    aria-expanded={abierta}
                    aria-label={abierta ? 'Ocultar el detalle' : 'Ver el detalle'}
                  >
                    {abierta ? <ChevronDown aria-hidden /> : <ChevronRight aria-hidden />}
                  </Button>
                </TableCell>
                <TableCell className="cifra text-texto-suave">{formatearFechaHora(carga.instante)}</TableCell>
                <TableCell className="font-medium">{carga.lote}</TableCell>
                <TableCell className="cifra text-right">{formatearNumero(carga.filas)}</TableCell>
                <TableCell className="cifra text-right text-ok">{formatearNumero(carga.validos)}</TableCell>
                <TableCell className={cn('cifra text-right', carga.rechazados > 0 ? 'text-aviso' : 'text-texto-suave')}>
                  {formatearNumero(carga.rechazados)}
                </TableCell>
                {niveles.map((nivel) => (
                  <TableCell key={nivel}>
                    <CeldaNivel carga={carga} nivel={nivel} />
                  </TableCell>
                ))}
              </TableRow>
              {abierta && (
                <TableRow className="bg-muted/30 hover:bg-muted/30">
                  <TableCell colSpan={columnas} className="whitespace-normal">
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
      <CardHeader>
        <CardTitle>Cargas históricas</CardTitle>
        <CardDescription>
          Resumen que Spark escribe en <code className="font-mono text-[11px]">auditoria.cargas</code> al terminar cada carga: los viajes
          leídos del fichero de la TLC, los que pasaron la validación y, por nivel, cuántos grupos se publicaron y cuántos quedaron
          suprimidos (por tener menos de 10 viajes o por la supresión complementaria).
        </CardDescription>
      </CardHeader>
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
