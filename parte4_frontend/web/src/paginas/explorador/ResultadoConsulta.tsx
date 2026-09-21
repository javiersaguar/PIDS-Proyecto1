/**
 * Resultado de la consulta del explorador: resumen (filas, grupos enmascarados, truncada), gráfico según el
 * nivel, tabla ordenable y la nota de privacidad de la respuesta. Un 403 se muestra como «Consulta rechazada»;
 * cualquier otro error, con su `detail` y «Reintentar». La región es `aria-live` para anunciar el resultado.
 */
import type { UseQueryResult } from '@tanstack/react-query'
import { LoaderCircle, Lock, Table2, TriangleAlert } from 'lucide-react'
import { useMemo } from 'react'

import { decisionDe } from '@/api/consultas'
import type { Consulta, Respuesta } from '@/api/tipos'
import { ChipResultado, TablaAgregados } from '@/componentes/datos'
import { ETIQUETAS_FUENTE, totalesDe } from '@/componentes/datos/agregados'
import { formatearEntero, pluralizar } from '@/componentes/datos/formato'
import { EstadoCargando, EstadoError, EstadoVacio } from '@/componentes/shell'
import { Badge } from '@/componentes/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/componentes/ui/card'

import { describirConsulta, normalizarMetricas } from './consulta'
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
          descripcion="Configura una consulta en el formulario o elige uno de los ejemplos. La consulta queda en la URL para poder compartirla."
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

function Respuestas({ respuesta, actualizando }: { respuesta: Respuesta; actualizando: boolean }) {
  const { consulta, filas } = respuesta
  const totales = useMemo(() => totalesDe(filas), [filas])
  const metricas = useMemo(() => normalizarMetricas(consulta.metricas), [consulta.metricas])
  const nombresZona = useMemo(() => {
    const mapa = new Map<number, string>()
    for (const fila of filas) if (fila.zona_origen != null && fila.zona_origen_nombre) mapa.set(fila.zona_origen, fila.zona_origen_nombre)
    return mapa
  }, [filas])
  const descripcion = describirConsulta(consulta, nombresZona)

  return (
    <>
      <Card className="sombra-tarjeta">
        <CardHeader>
          <div className="flex flex-wrap items-center gap-2">
            <ChipResultado resultado={respuesta.resultado} />
            <Badge variant="outline">{ETIQUETAS_FUENTE[consulta.fuente ?? 'historico']}</Badge>
            {actualizando && (
              <span className="flex items-center gap-1 text-xs text-texto-suave">
                <LoaderCircle className="size-3 animate-spin" aria-hidden /> Actualizando…
              </span>
            )}
          </div>
          <CardTitle className="text-xl text-primario first-letter:uppercase">{descripcion}</CardTitle>
          <CardDescription>
            <span className="cifra">{pluralizar(filas.length, 'fila')}</span> · <span className="cifra">{pluralizar(totales.visibles, 'grupo visible', 'grupos visibles')}</span> ·{' '}
            <span className={totales.enmascarados > 0 ? 'cifra font-medium text-enmascarado' : 'cifra'}>
              {pluralizar(respuesta.grupos_enmascarados, 'grupo enmascarado', 'grupos enmascarados')}
            </span>
            {totales.visibles > 0 && (
              <>
                {' '}
                · total de los grupos visibles <span className="cifra font-medium text-foreground">{formatearEntero(totales.total)}</span> viajes
              </>
            )}
          </CardDescription>
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
