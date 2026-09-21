/**
 * Resultado de la consulta del explorador: resumen (filas, grupos enmascarados, truncada), gráfico según el
 * nivel, tabla ordenable y la nota de privacidad de la respuesta. Un 403 se muestra como «Consulta rechazada»;
 * cualquier otro error, con su `detail` y «Reintentar». La región es `aria-live` para anunciar el resultado.
 */
import type { UseQueryResult } from '@tanstack/react-query'
import { LoaderCircle, Lock, Table2, TriangleAlert } from 'lucide-react'
import { useMemo } from 'react'

import { decisionDe } from '@/api/consultas'
import type { Consulta, Nivel, Respuesta } from '@/api/tipos'
import { ChipResultado, TablaAgregados } from '@/componentes/datos'
import { ETIQUETAS_FUENTE, ETIQUETAS_METRICA, totalesDe } from '@/componentes/datos/agregados'
import { formatearEntero, pluralizar } from '@/componentes/datos/formato'
import { EstadoCargando, EstadoError, EstadoVacio } from '@/componentes/shell'
import { Badge } from '@/componentes/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/componentes/ui/card'

import { describirVentana, normalizarMetricas } from './consulta'
import { ConsultaRechazada } from './ConsultaRechazada'
import { GraficoResultado } from './GraficoResultado'

interface Props {
  consulta: Consulta | null
  resultado: UseQueryResult<Respuesta, Error>
  onAlternativa: (consulta: Consulta) => void
}

export function ResultadoConsulta({ consulta, resultado, onAlternativa }: Props) {
  const decision = resultado.isError ? decisionDe(resultado.error) : null

  return (
    <section aria-live="polite" aria-busy={resultado.isFetching || undefined} aria-label="Resultado de la consulta" className="space-y-4">
      {!consulta ? (
        <EstadoVacio
          icono={<Table2 className="size-7" aria-hidden />}
          titulo="Sin consulta"
          descripcion="Ajusta los filtros y pulsa Consultar, o abre un ejemplo o una vista guardada. La consulta queda en la URL para poder compartirla."
          className="bg-superficie"
        />
      ) : resultado.isPending ? (
        <EstadoCargando variante="tarjeta" lineas={6} etiqueta="Consultando la API de acceso…" />
      ) : resultado.isError ? (
        decision ? (
          <ConsultaRechazada decision={decision} consulta={consulta} onAlternativa={onAlternativa} enviando={resultado.isFetching} />
        ) : (
          <EstadoError
            error={resultado.error}
            titulo="No se ha podido ejecutar la consulta"
            alReintentar={() => void resultado.refetch()}
            reintentando={resultado.isFetching}
          />
        )
      ) : (
        <Respuestas respuesta={resultado.data} actualizando={resultado.isFetching} />
      )}
    </section>
  )
}

const TITULO_NIVEL: Record<Nivel, string> = {
  hora_zona: 'Viajes por hora',
  dia_barrio: 'Viajes por día',
  od_dia_barrio: 'Flujos por día',
}

/** Origen, destino, ventana y métricas, en piezas cortas separadas. */
function detalleResultado(consulta: Consulta, nombresZona: ReadonlyMap<number, string>): string {
  const partes: string[] = []
  if (consulta.zona_origen != null) {
    const nombre = nombresZona.get(consulta.zona_origen)
    partes.push(nombre ? `${nombre} (zona ${consulta.zona_origen})` : `Zona ${consulta.zona_origen}`)
  }
  if (consulta.barrio_origen && consulta.barrio_destino) partes.push(`${consulta.barrio_origen} → ${consulta.barrio_destino}`)
  else if (consulta.barrio_origen) partes.push(consulta.barrio_origen)
  else if (consulta.barrio_destino) partes.push(`Hacia ${consulta.barrio_destino}`)
  partes.push(describirVentana(consulta))
  const extras = normalizarMetricas(consulta.metricas).filter((m) => m !== 'n_viajes')
  if (extras.length) partes.push(extras.map((m) => ETIQUETAS_METRICA[m]).join(', '))
  return partes.join(' · ')
}

function Respuestas({ respuesta, actualizando }: { respuesta: Respuesta; actualizando: boolean }) {
  const { consulta, filas } = respuesta
  const totales = useMemo(() => totalesDe(filas), [filas])
  const metricas = useMemo(() => normalizarMetricas(consulta.metricas), [consulta.metricas])
  const nombresZona = useMemo(() => {
    const mapa = new Map<number, string>()
    for (const fila of filas) if (fila.zona_origen != null && fila.zona_origen_nombre) mapa.set(fila.zona_origen, fila.zona_origen_nombre)
    return mapa
  }, [filas])
  const descripcion = detalleResultado(consulta, nombresZona)
  const titulo = TITULO_NIVEL[consulta.nivel]

  return (
    <>
      <Card className="sombra-tarjeta">
        <CardHeader className="gap-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 space-y-1">
              <h2 className="text-[15px] font-semibold text-slate-900">{titulo}</h2>
              <p className="text-sm text-slate-500">{descripcion}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <ChipResultado resultado={respuesta.resultado} />
              <Badge variant="outline">{ETIQUETAS_FUENTE[consulta.fuente ?? 'historico']}</Badge>
              {actualizando && (
                <span className="flex items-center gap-1 text-xs text-texto-suave">
                  <LoaderCircle className="size-3 animate-spin" aria-hidden /> Actualizando…
                </span>
              )}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Dato etiqueta={pluralizar(filas.length, 'fila')} />
            <Dato etiqueta={pluralizar(totales.visibles, 'grupo visible', 'grupos visibles')} />
            <Dato etiqueta={pluralizar(respuesta.grupos_enmascarados, 'grupo enmascarado', 'grupos enmascarados')} aviso={respuesta.grupos_enmascarados > 0} />
            {totales.visibles > 0 && <Dato etiqueta={`${formatearEntero(totales.total)} viajes visibles`} />}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {respuesta.truncada && (
            <p role="status" className="flex items-start gap-2 rounded-md border border-aviso/30 bg-aviso/5 px-3 py-2 text-xs text-aviso">
              <TriangleAlert className="mt-0.5 size-3.5 shrink-0" aria-hidden />
              Respuesta truncada: la API devuelve como mucho 500 filas por consulta. Acota la ventana o añade un filtro de zona o barrio para verlo todo.
            </p>
          )}
          {filas.length === 0 ? (
            <EstadoVacio titulo="Sin grupos en esa ventana" descripcion="La API no tiene agregados para esos filtros. Prueba con otra fecha, zona o barrio." />
          ) : (
            <GraficoResultado respuesta={respuesta} />
          )}
        </CardContent>
      </Card>

      {filas.length > 0 && (
        <Card className="sombra-tarjeta">
          <CardHeader>
            <CardTitle className="text-xl text-primario">Filas</CardTitle>
            <CardDescription>Pulsa una cabecera para ordenar. Los grupos enmascarados no muestran cifras ni se suman al total.</CardDescription>
          </CardHeader>
          <CardContent>
            <TablaAgregados filas={filas} nivel={consulta.nivel} metricas={metricas} conTotal titulo={`Filas: ${descripcion}`} />
          </CardContent>
        </Card>
      )}

      {respuesta.nota && (
        <p className="flex items-start gap-2 rounded-lg border border-enmascarado/20 bg-enmascarado-suave/40 px-3 py-2 text-xs text-foreground">
          <Lock className="mt-0.5 size-3.5 shrink-0 text-enmascarado" aria-hidden />
          <span>
            <span className="font-medium text-enmascarado">Nota de privacidad de la API:</span> {respuesta.nota}
          </span>
        </p>
      )}
    </>
  )
}

function Dato({ etiqueta, aviso = false }: { etiqueta: string; aviso?: boolean }) {
  return (
    <div className={aviso ? 'rounded-lg bg-enmascarado-suave px-2.5 py-1 text-xs font-medium text-enmascarado' : 'rounded-lg bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-600'}>
      {etiqueta}
    </div>
  )
}
