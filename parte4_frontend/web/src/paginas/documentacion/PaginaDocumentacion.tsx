/**
 * Documentación: el lienzo de arquitectura. Cada pieza se explica al pulsarla y los tramos por los que pasa un
 * proceso en marcha (una carga en Airflow, el simulador, Spark publicando) se iluminan y se mueven.
 * Los enlaces salen de `GET /api/panel` o de los puertos por defecto; la actividad, de `useActividad`.
 */
import { useActividad } from '@/api/actividad'
import { useEnlaces } from '@/api/operaciones'

import { flujosDe } from './actividad'
import { BarraActividad } from './BarraActividad'
import { Lienzo } from './Lienzo'

export default function PaginaDocumentacion() {
  const { enlaces } = useEnlaces()
  const actividad = useActividad()
  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <h1 className="sr-only">Arquitectura de la plataforma</h1>
      <BarraActividad actividad={actividad} />
      <div className="min-h-0 flex-1">
        <Lienzo enlaces={enlaces} flujos={flujosDe(actividad)} />
      </div>
    </div>
  )
}
