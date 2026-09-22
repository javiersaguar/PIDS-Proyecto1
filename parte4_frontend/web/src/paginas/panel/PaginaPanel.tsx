/**
 * Panel de inicio: indicadores, viajes por barrio y la tabla de servicios o accesos.
 * Sin título de página: `GET /api/panel` se actualiza solo cada 60 s y, mientras la plataforma trabaja (una carga,
 * el simulador, Spark publicando), cada 20 s; el indicador «En vivo» dice qué pasa y cuándo llega el siguiente dato.
 * Las cifras y las barras se mueven hacia el valor nuevo en vez de saltar. En esta ruta el shell no pinta cabecera ni pie.
 */
import { resumirActividad, useActividad } from '@/api/actividad'
import { INTERVALO_PANEL_ACTIVO_MS, INTERVALO_PANEL_MS, usePanel } from '@/api/panel'
import { EnVivo } from '@/componentes/datos/EnVivo'
import { EstadoError } from '@/componentes/shell'

import { TablaPlataforma } from './ServiciosYEnlaces'
import { TarjetasPanel } from './TarjetasPanel'
import { ViajesPorBarrio } from './ViajesPorBarrio'

function Esqueleto() {
  return (
    <div className="space-y-4" role="status" aria-label="Cargando el panel">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {['viajes', 'barrios', 'decisiones', 'frescura'].map((clave) => (
          <div key={clave} className="h-[88px] animate-pulse rounded-2xl bg-white" />
        ))}
      </div>
      <div className="h-80 animate-pulse rounded-2xl bg-white" />
      <div className="h-64 animate-pulse rounded-2xl bg-white" />
    </div>
  )
}

export default function PaginaPanel() {
  const actividad = useActividad()
  const intervaloMs = actividad.enMarcha ? INTERVALO_PANEL_ACTIVO_MS : INTERVALO_PANEL_MS
  const panel = usePanel({ intervaloMs })

  return (
    <>
      <h1 className="sr-only">Panel</h1>
      {panel.isPending ? (
        <Esqueleto />
      ) : panel.isError ? (
        <EstadoError
          error={panel.error}
          titulo="No se ha podido cargar el panel"
          alReintentar={() => void panel.refetch()}
          reintentando={panel.isFetching}
        />
      ) : (
        <div className="space-y-4">
          <div className="flex justify-end">
            <EnVivo
              activo={actividad.enMarcha}
              texto={resumirActividad(actividad)}
              actualizadoEn={panel.dataUpdatedAt}
              intervaloMs={intervaloMs}
              refrescando={panel.isFetching}
            />
          </div>
          <TarjetasPanel panel={panel.data} actualizadoEn={panel.dataUpdatedAt} />
          <ViajesPorBarrio ultimoDia={panel.data.ultimo_dia} accesoDisponible={panel.data.acceso_disponible !== false} />
          <TablaPlataforma servicios={panel.data.servicios ?? []} enlaces={panel.data.enlaces} />
        </div>
      )}
    </>
  )
}
