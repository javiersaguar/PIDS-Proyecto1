/**
 * Tarjeta «Viajes por barrio del último día»: barras horizontales del histórico y, si lo hay, del tiempo real,
 * en pestañas. Solo llegan grupos visibles (`UltimoDia.por_barrio`): los enmascarados no están ni se suman.
 */
import { useState } from 'react'

import type { PanelExtendido, UltimoDiaExtendido } from '@/api/panel'
import { formatearEntero, formatearFecha, pluralizar } from '@/componentes/datos/formato'
import { GraficoBarras, type Barra } from '@/componentes/graficos'
import { EstadoNoDisponible, EstadoVacio } from '@/componentes/shell'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/componentes/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/componentes/ui/tabs'

type ClaveFuente = 'historico' | 'tiempo_real'

const TITULO_FUENTE: Record<ClaveFuente, string> = { historico: 'Histórico', tiempo_real: 'Tiempo real' }

function barrasDe(dia: UltimoDiaExtendido): Barra[] {
  return Object.entries(dia.por_barrio)
    .sort((a, b) => b[1] - a[1])
    .map(([barrio, viajes]) => ({ etiqueta: barrio, valor: viajes }))
}

function Grafico({ dia, fuente, accesoDisponible }: { dia: UltimoDiaExtendido | null; fuente: ClaveFuente; accesoDisponible: boolean }) {
  if (!dia && !accesoDisponible) {
    return <EstadoNoDisponible servicio="API de acceso" descripcion="Sin cifras del último día mientras la API de acceso no responda." />
  }
  if (!dia || Object.keys(dia.por_barrio).length === 0) {
    return (
      <EstadoVacio
        titulo={`Sin datos de ${TITULO_FUENTE[fuente].toLowerCase()}`}
        descripcion={fuente === 'tiempo_real' ? 'Arranca el simulador en Operaciones para ver viajes en tiempo real.' : 'No hay agregados publicados para esta fuente.'}
      />
    )
  }
  return (
    <>
      <GraficoBarras
        datos={barrasDe(dia)}
        orientacion="horizontal"
        nombreSerie="Viajes"
        titulo={`Viajes por barrio el ${formatearFecha(dia.dia)} (${TITULO_FUENTE[fuente].toLowerCase()})`}
      />
      <p className="mt-2 text-xs text-texto-suave">
        {formatearFecha(dia.dia)} · {pluralizar(Object.keys(dia.por_barrio).length, 'barrio')} con grupos visibles · total{' '}
        <span className="cifra font-medium text-foreground">{formatearEntero(dia.total)}</span> viajes.{' '}
        {dia.grupos_enmascarados ? (
          <span className="text-enmascarado">{pluralizar(dia.grupos_enmascarados, 'grupo enmascarado', 'grupos enmascarados')} no aparecen ni se suman.</span>
        ) : (
          'Los grupos con menos de 10 viajes no aparecen ni se suman.'
        )}
      </p>
    </>
  )
}

export function ViajesPorBarrio({ ultimoDia, accesoDisponible = true }: { ultimoDia: PanelExtendido['ultimo_dia']; accesoDisponible?: boolean }) {
  const hayTiempoReal = !!ultimoDia?.tiempo_real
  const [fuente, setFuente] = useState<ClaveFuente>('historico')
  const historico = ultimoDia?.historico ?? null
  const tiempoReal = ultimoDia?.tiempo_real ?? null

  return (
    <Card className="sombra-tarjeta">
      <CardHeader>
        <CardTitle className="text-xl text-primario">Viajes por barrio del último día</CardTitle>
        <CardDescription>Grupos visibles del último día con datos publicados, por barrio de origen.</CardDescription>
      </CardHeader>
      <CardContent>
        {hayTiempoReal ? (
          <Tabs value={fuente} onValueChange={(v) => setFuente(v as ClaveFuente)}>
            <TabsList aria-label="Fuente de los datos">
              <TabsTrigger value="historico">Histórico</TabsTrigger>
              <TabsTrigger value="tiempo_real">Tiempo real</TabsTrigger>
            </TabsList>
            <TabsContent value="historico">
              <Grafico dia={historico} fuente="historico" accesoDisponible={accesoDisponible} />
            </TabsContent>
            <TabsContent value="tiempo_real">
              <Grafico dia={tiempoReal} fuente="tiempo_real" accesoDisponible={accesoDisponible} />
            </TabsContent>
          </Tabs>
        ) : (
          <Grafico dia={historico} fuente="historico" accesoDisponible={accesoDisponible} />
        )}
      </CardContent>
    </Card>
  )
}
