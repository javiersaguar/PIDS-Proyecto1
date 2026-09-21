/**
 * Tiempo real (§6): frescura con semáforo y «hace X s», último día con datos, viajes por hora (barras, últimas
 * 6/12/24 h con datos) y la última hora por zona. `GET /api/tiempo-real?horas=` se refresca cada 30 s.
 * Los datos son agregados protegidos: los grupos enmascarados se cuentan, nunca se suman.
 */
import { Activity, CalendarDays, Clock3, Info, RefreshCw } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router'

import { HORAS_TIEMPO_REAL, useTiempoReal, type HorasTiempoReal } from '@/api/tiempoReal'
import type { TiempoReal } from '@/api/tipos'
import { Antiguedad, Frescura, TablaAgregados, TarjetaKpi } from '@/componentes/datos'
import { totalesDe } from '@/componentes/datos/agregados'
import { formatearEntero, formatearFecha, formatearFechaCorta, formatearFechaHora, formatearHora, pluralizar } from '@/componentes/datos/formato'
import { GraficoBarras, type Barra } from '@/componentes/graficos'
import { EncabezadoPagina, EstadoCargando, EstadoError, EstadoNoDisponible, EstadoVacio } from '@/componentes/shell'
import { Button } from '@/componentes/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/componentes/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/componentes/ui/tabs'
import { cn } from '@/lib/utils'

const DESCRIPCION =
  'Viajes de las últimas horas del flujo de captura (simulador → Kafka → Spark) y frescura de los agregados de tiempo real. Misma protección que el histórico: solo grupos con al menos 10 viajes.'

function Esqueleto() {
  return (
    <div className="space-y-6" role="status" aria-label="Cargando el tiempo real">
      <div className="grid gap-4 sm:grid-cols-3">
        {['frescura', 'dia', 'hora'].map((clave) => (
          <TarjetaKpi key={clave} titulo="Cargando" cargando />
        ))}
      </div>
      <EstadoCargando variante="tarjeta" lineas={6} />
      <EstadoCargando variante="tarjeta" lineas={5} />
    </div>
  )
}

function barrasPorHora(porHora: TiempoReal['por_hora']): Barra[] {
  return porHora.map((h) => ({
    etiqueta: h.hora,
    valor: h.n_viajes,
    detalle: `${pluralizar(h.grupos, 'grupo')}${h.grupos_enmascarados > 0 ? ` · ${pluralizar(h.grupos_enmascarados, 'enmascarado')} (no incluidos)` : ''}`,
  }))
}

export default function PaginaTiempoReal() {
  const [horas, setHoras] = useState<HorasTiempoReal>(6)
  const tiempoReal = useTiempoReal(horas)
  const datos = tiempoReal.data

  const ultimaHora = useMemo(() => datos?.por_zona_ultima_hora?.[0]?.hora ?? datos?.por_hora?.at(-1)?.hora ?? null, [datos])
  const totalesUltimaHora = useMemo(() => totalesDe(datos?.por_zona_ultima_hora ?? []), [datos])
  const barras = useMemo(() => barrasPorHora(datos?.por_hora ?? []), [datos])
  const variosDias = useMemo(() => new Set(barras.map((b) => b.etiqueta.slice(0, 10))).size > 1, [barras])
  const sinDatos = !!datos && datos.por_hora.length === 0 && !datos.ultimo_dia
  const accesoCaido = !!datos && datos.acceso_disponible === false

  const acciones = (
    <div className="flex items-center gap-2 text-xs text-texto-suave">
      {datos && (
        <span className="flex items-center gap-1.5">
          <span className={cn('size-2 rounded-full bg-ok', tiempoReal.isFetching && 'animate-pulse bg-acento')} aria-hidden />
          <Antiguedad instante={tiempoReal.dataUpdatedAt} sufijo="· se refresca cada 30 s" />
        </span>
      )}
      <Button variant="outline" size="sm" onClick={() => void tiempoReal.refetch()} disabled={tiempoReal.isFetching}>
        <RefreshCw className={cn(tiempoReal.isFetching && 'animate-spin')} aria-hidden />
        Actualizar
      </Button>
    </div>
  )

  return (
    <>
      <EncabezadoPagina titulo="Tiempo real" descripcion={DESCRIPCION} acciones={acciones} />

      <p role="note" className="mb-6 flex items-start gap-2 rounded-lg border border-primario/15 bg-primario/5 px-3 py-2 text-xs text-foreground">
        <Info className="mt-0.5 size-3.5 shrink-0 text-primario" aria-hidden />
        <span>
          <span className="font-medium">Los datos simulados son de 2020.</span> El simulador reenvía viajes de 2020 al ritmo configurado, así que la hora de los datos
          no es la hora actual; la frescura mide cuándo escribió Spark por última vez en los agregados de tiempo real.
        </span>
      </p>

      {!datos ? (
        tiempoReal.isError ? (
          <EstadoError
            error={tiempoReal.error}
            titulo="No se ha podido cargar el tiempo real"
            alReintentar={() => void tiempoReal.refetch()}
            reintentando={tiempoReal.isFetching}
          />
        ) : (
          <Esqueleto />
        )
      ) : (
        <div className="space-y-6">
          {tiempoReal.isError && (
            <EstadoError
              error={tiempoReal.error}
              titulo="El último refresco ha fallado; se muestran los datos anteriores"
              alReintentar={() => void tiempoReal.refetch()}
              reintentando={tiempoReal.isFetching}
            />
          )}
          <section aria-label="Indicadores" className="grid gap-4 sm:grid-cols-3">
            <TarjetaKpi
              titulo="Frescura"
              icono={Activity}
              valor={<Frescura variante="grande" segundos={datos.frescura?.segundos ?? null} instante={datos.frescura?.instante ?? null} actualizadoEn={tiempoReal.dataUpdatedAt} />}
              descripcion="Verde: menos de 2 min · ámbar: menos de 10 min · rojo: más, o sin dato."
            />
            <TarjetaKpi
              titulo="Último día con datos"
              icono={CalendarDays}
              valor={datos.ultimo_dia ? formatearFecha(datos.ultimo_dia) : 'Sin datos'}
              descripcion={datos.ultimo_dia ? 'Último día presente en los agregados de tiempo real.' : 'Todavía no hay agregados de tiempo real.'}
            />
            <TarjetaKpi
              titulo="Última hora con datos"
              icono={Clock3}
              valor={ultimaHora ? formatearEntero(totalesUltimaHora.total) : 'Sin datos'}
              descripcion={
                ultimaHora
                  ? `Viajes visibles de las ${formatearHora(ultimaHora)} del ${formatearFecha(ultimaHora)} · ${pluralizar(totalesUltimaHora.visibles, 'zona')}${
                      totalesUltimaHora.enmascarados > 0 ? ` · ${pluralizar(totalesUltimaHora.enmascarados, 'grupo enmascarado', 'grupos enmascarados')}` : ''
                    }`
                  : 'Sin filas en la última hora.'
              }
            />
          </section>

          {sinDatos && accesoCaido ? (
            <EstadoNoDisponible
              servicio="API de acceso"
              descripcion="Sin agregados de tiempo real mientras la API de acceso no responda."
              alReintentar={() => void tiempoReal.refetch()}
              className="bg-superficie"
            />
          ) : sinDatos ? (
            <EstadoVacio
              titulo="Sin datos de tiempo real"
              descripcion="Los agregados de tiempo real están vacíos. Arranca el simulador para ver viajes llegando."
              accion={
                <Button asChild variant="outline" size="sm">
                  <Link to="/operaciones">Ir a Operaciones</Link>
                </Button>
              }
              className="bg-superficie"
            />
          ) : (
            <>
              <Card className="sombra-tarjeta">
                <CardHeader>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-1">
                      <CardTitle className="text-xl text-primario">Viajes por hora (últimas {horas} h con datos)</CardTitle>
                      <CardDescription>Suma de los grupos visibles de cada hora; los enmascarados se cuentan en el detalle, no se suman.</CardDescription>
                    </div>
                    <Tabs value={String(horas)} onValueChange={(v) => setHoras(Number(v) as HorasTiempoReal)}>
                      <TabsList aria-label="Horas a mostrar">
                        {HORAS_TIEMPO_REAL.map((h) => (
                          <TabsTrigger key={h} value={String(h)}>
                            {h} h
                          </TabsTrigger>
                        ))}
                      </TabsList>
                    </Tabs>
                  </div>
                </CardHeader>
                <CardContent>
                  {barras.length === 0 ? (
                    <EstadoVacio titulo="Sin horas con datos" descripcion="No hay ninguna hora con grupos en la fuente de tiempo real." />
                  ) : (
                    <GraficoBarras
                      datos={barras}
                      orientacion="vertical"
                      nombreSerie="Viajes"
                      formatearEtiqueta={(h) => (variosDias ? `${formatearFechaCorta(h)} ${formatearHora(h)}` : formatearHora(h))}
                      formatearEtiquetaCompleta={formatearFechaHora}
                      titulo={`Viajes por hora, últimas ${horas} horas con datos`}
                    />
                  )}
                </CardContent>
              </Card>

              <Card className="sombra-tarjeta">
                <CardHeader>
                  <CardTitle className="text-xl text-primario">Última hora por zona</CardTitle>
                  <CardDescription>
                    {ultimaHora ? `Grupos de las ${formatearHora(ultimaHora)} del ${formatearFecha(ultimaHora)}, por zona de origen.` : 'Grupos de la última hora, por zona de origen.'} Los
                    enmascarados llevan su chip y no muestran cifras.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <TablaAgregados
                    filas={datos.por_zona_ultima_hora ?? []}
                    nivel="hora_zona"
                    conTotal
                    ordenInicial={{ clave: 'n_viajes', direccion: 'desc' }}
                    titulo="Última hora por zona"
                    vacio={<EstadoVacio titulo="Sin filas en la última hora" descripcion="La última hora no tiene grupos publicados." />}
                  />
                </CardContent>
              </Card>
            </>
          )}
        </div>
      )}
    </>
  )
}
