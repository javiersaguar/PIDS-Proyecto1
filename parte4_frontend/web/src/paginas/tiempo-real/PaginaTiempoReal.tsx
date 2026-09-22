/**
 * Tiempo real (§6): tres indicadores, viajes por hora (barras, últimas 6/12/24 h con datos)
 * y la última hora por zona. `GET /api/tiempo-real?horas=` se refresca cada 10 s y, mientras el simulador
 * envía viajes o Spark está publicando, cada 5 s; el indicador «En vivo» dice qué está pasando. Al llegar un dato
 * nuevo las barras se deslizan a su valor, la cifra de la última hora recorre el camino y, si aparece una hora
 * nueva, se anuncia. Los datos son agregados protegidos: los grupos enmascarados se cuentan, nunca se suman.
 */
import { Activity, CalendarDays, Clock3, type LucideIcon } from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'
import { Link } from 'react-router'

import { resumirActividad, useActividad } from '@/api/actividad'
import { HORAS_TIEMPO_REAL, INTERVALO_TIEMPO_REAL_ACTIVO_MS, INTERVALO_TIEMPO_REAL_MS, useTiempoReal, type HorasTiempoReal } from '@/api/tiempoReal'
import type { TiempoReal } from '@/api/tipos'
import { TablaAgregados } from '@/componentes/datos'
import { totalesDe } from '@/componentes/datos/agregados'
import { EnVivo } from '@/componentes/datos/EnVivo'
import { describirAntiguedad, formatearEntero, formatearFecha, formatearFechaCorta, formatearFechaHora, formatearHora } from '@/componentes/datos/formato'
import { useSegundosDesde } from '@/componentes/datos/useAhora'
import { useCambioDe, useInstanteDe } from '@/componentes/datos/useCambioDe'
import { useNumeroAnimado } from '@/componentes/datos/useNumeroAnimado'
import { GraficoBarras, type Barra } from '@/componentes/graficos'
import { Semaforo } from '@/componentes/graficos/Semaforo'
import { nivelFrescura, TEXTO_FRESCURA, type NivelFrescura } from '@/componentes/graficos/frescura'
import { EstadoError, EstadoNoDisponible, EstadoVacio } from '@/componentes/shell'
import { Button } from '@/componentes/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/componentes/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/componentes/ui/tabs'
import { cn } from '@/lib/utils'

import { MiniSerie } from '../panel/MiniSerie'

const VERDE = '#34d399'
const AZUL = '#38bdf8'
const AMBAR = '#fbbf24'
const CORAL = '#fb7185'

const TONO: Record<NivelFrescura, { icono: string; cifra: string; serie: string }> = {
  ok: { icono: 'bg-emerald-50 text-emerald-600', cifra: 'text-slate-900', serie: VERDE },
  aviso: { icono: 'bg-amber-50 text-amber-600', cifra: 'text-amber-700', serie: AMBAR },
  peligro: { icono: 'bg-rose-50 text-rose-500', cifra: 'text-rose-600', serie: CORAL },
}
/** Cuánto se anuncia una hora nueva tras aparecer. */
const MOSTRAR_HORA_NUEVA_S = 30

/** «Nueva hora: 23:00» durante un rato cuando el streaming abre otra hora. */
function ChipHoraNueva({ ultimaHora }: { ultimaHora: string | null }) {
  const cambio = useCambioDe(ultimaHora)
  const segundos = useSegundosDesde(useInstanteDe(cambio?.n))
  if (!cambio || !cambio.anterior || !cambio.actual || segundos == null || segundos > MOSTRAR_HORA_NUEVA_S) return null
  return (
    <span key={cambio.n} role="status" className="destello-datos cifra rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
      Nueva hora: {formatearHora(cambio.actual)}
    </span>
  )
}

function Esqueleto() {
  return (
    <div className="space-y-4" role="status" aria-label="Cargando el tiempo real">
      <div className="grid gap-4 sm:grid-cols-3">
        {['frescura', 'dia', 'hora'].map((clave) => (
          <div key={clave} className="h-[88px] animate-pulse rounded-2xl bg-white" />
        ))}
      </div>
      <div className="h-80 animate-pulse rounded-2xl bg-white" />
      <div className="h-64 animate-pulse rounded-2xl bg-white" />
    </div>
  )
}

function barrasPorHora(porHora: TiempoReal['por_hora']): Barra[] {
  return porHora.map((h) => ({
    etiqueta: h.hora,
    valor: h.n_viajes,
    detalle: h.grupos_enmascarados > 0 ? `${h.grupos_enmascarados} enmascarados, no incluidos` : undefined,
  }))
}

function Indicador({
  titulo,
  valor,
  icono: Icono,
  iconoClase,
  cifraClase = 'text-slate-900',
  serie,
  colorSerie,
  detalle,
}: {
  titulo: string
  valor: string
  icono: LucideIcon
  iconoClase: string
  cifraClase?: string
  serie: readonly number[]
  colorSerie: string
  detalle?: ReactNode
}) {
  return (
    <article className="flex items-center gap-3 rounded-2xl border border-slate-200/80 bg-white px-4 py-4 shadow-[0_1px_2px_rgba(15,23,42,0.04)] sm:px-5">
      <span className={cn('flex size-10 shrink-0 items-center justify-center rounded-xl', iconoClase)} aria-hidden>
        <Icono className="size-[18px]" strokeWidth={2} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-[13px] font-medium text-slate-500">{titulo}</p>
        <p className={cn('cifra mt-1 text-[1.65rem] leading-none font-semibold tracking-tight', cifraClase)}>{valor}</p>
        {detalle && <div className="mt-1.5">{detalle}</div>}
      </div>
      <MiniSerie valores={serie} color={colorSerie} />
    </article>
  )
}

function IndicadorFrescura({ segundos, actualizadoEn }: { segundos: number | null; actualizadoEn: number }) {
  const transcurridos = useSegundosDesde(actualizadoEn, INTERVALO_TIEMPO_REAL_MS)
  const actuales = segundos == null ? null : segundos + (transcurridos ?? 0)
  const nivel = nivelFrescura(actuales)
  const tono = TONO[nivel]

  return (
    <Indicador
      titulo="Frescura"
      valor={actuales == null ? 'Sin dato' : describirAntiguedad(actuales)}
      icono={Activity}
      iconoClase={tono.icono}
      cifraClase={tono.cifra}
      serie={[]}
      colorSerie={tono.serie}
      detalle={<Semaforo nivel={nivel} etiqueta={TEXTO_FRESCURA[nivel]} tamano="sm" className="text-xs" />}
    />
  )
}

export default function PaginaTiempoReal() {
  const [horas, setHoras] = useState<HorasTiempoReal>(6)
  const actividad = useActividad()
  // con viajes entrando o Spark publicando, el BFF guarda la respuesta 20 s: preguntar cada 5 s la trae en cuanto cambia
  const intervaloMs = actividad.simulacion || actividad.publicando ? INTERVALO_TIEMPO_REAL_ACTIVO_MS : INTERVALO_TIEMPO_REAL_MS
  const tiempoReal = useTiempoReal(horas, { intervaloMs })
  const datos = tiempoReal.data

  const ultimaHora = useMemo(() => datos?.por_zona_ultima_hora?.[0]?.hora ?? datos?.por_hora?.at(-1)?.hora ?? null, [datos])
  const totalesUltimaHora = useMemo(() => totalesDe(datos?.por_zona_ultima_hora ?? []), [datos])
  const totalUltimaHoraAnimado = useNumeroAnimado(ultimaHora ? totalesUltimaHora.total : null)
  const barras = useMemo(() => barrasPorHora(datos?.por_hora ?? []), [datos])
  const serieHoras = useMemo(() => (datos?.por_hora ?? []).map((h) => h.n_viajes), [datos])
  const variosDias = useMemo(() => new Set(barras.map((b) => b.etiqueta.slice(0, 10))).size > 1, [barras])
  const sinDatos = !!datos && datos.por_hora.length === 0 && !datos.ultimo_dia
  const accesoCaido = !!datos && datos.acceso_disponible === false
  // las barras se deslizan solo a partir del segundo dato: la primera pintura sale ya en su sitio
  const animar = useCambioDe(tiempoReal.dataUpdatedAt, String(horas)) !== null

  return (
    <>
      <h1 className="sr-only">Tiempo real</h1>
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
        <div className="space-y-4">
          {tiempoReal.isError && (
            <EstadoError
              error={tiempoReal.error}
              titulo="El último refresco ha fallado; se muestran los datos anteriores"
              alReintentar={() => void tiempoReal.refetch()}
              reintentando={tiempoReal.isFetching}
            />
          )}
          <div className="flex flex-wrap items-center justify-end gap-2">
            <ChipHoraNueva ultimaHora={ultimaHora} />
            <EnVivo
              activo={actividad.enMarcha}
              texto={resumirActividad(actividad)}
              actualizadoEn={tiempoReal.dataUpdatedAt}
              intervaloMs={intervaloMs}
              refrescando={tiempoReal.isFetching}
            />
          </div>
          <section aria-label="Indicadores" className="grid gap-4 sm:grid-cols-3">
            <IndicadorFrescura segundos={datos.frescura?.segundos ?? null} actualizadoEn={tiempoReal.dataUpdatedAt} />
            <Indicador
              titulo="Último día"
              valor={datos.ultimo_dia ? formatearFecha(datos.ultimo_dia) : 'Sin datos'}
              icono={CalendarDays}
              iconoClase="bg-sky-50 text-sky-600"
              serie={serieHoras}
              colorSerie={AZUL}
            />
            <Indicador
              titulo="Última hora"
              valor={ultimaHora ? formatearEntero(totalUltimaHoraAnimado) : 'Sin datos'}
              icono={Clock3}
              iconoClase="bg-indigo-50 text-indigo-600"
              serie={serieHoras}
              colorSerie="#818cf8"
              detalle={ultimaHora ? <p className="text-xs text-slate-500">{formatearHora(ultimaHora)}</p> : undefined}
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
              <Card className="sombra-tarjeta border-slate-200/80 bg-white">
                <CardHeader>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <CardTitle className="text-xl text-primario">Viajes por hora</CardTitle>
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
                      animado={animar}
                      nombreSerie="Viajes"
                      formatearEtiqueta={(h) => (variosDias ? `${formatearFechaCorta(h)} ${formatearHora(h)}` : formatearHora(h))}
                      formatearEtiquetaCompleta={formatearFechaHora}
                      titulo={`Viajes por hora, últimas ${horas} horas con datos`}
                    />
                  )}
                </CardContent>
              </Card>

              <Card className="sombra-tarjeta border-slate-200/80 bg-white">
                <CardHeader>
                  <CardTitle className="text-xl text-primario">
                    Última hora por zona
                    {ultimaHora ? <span className="ml-2 text-base font-medium text-slate-500">{formatearHora(ultimaHora)}</span> : null}
                  </CardTitle>
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
