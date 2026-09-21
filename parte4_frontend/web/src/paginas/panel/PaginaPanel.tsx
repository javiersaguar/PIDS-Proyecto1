/**
 * Panel de inicio (§6): KPIs del último día publicado, frescura del tiempo real, decisiones de las últimas
 * 24 h, viajes por barrio (barras), estado de los servicios y accesos directos. Todo sale de `GET /api/panel`,
 * que se refresca solo cada 60 s (`usePanel`, misma clave que la cabecera).
 */
import { RefreshCw } from 'lucide-react'

import { usePanel } from '@/api/panel'
import { Antiguedad, TarjetaKpi } from '@/componentes/datos'
import { EncabezadoPagina, EstadoCargando, EstadoError } from '@/componentes/shell'
import { Button } from '@/componentes/ui/button'
import { cn } from '@/lib/utils'

import { TarjetaEnlaces, TarjetaServicios } from './ServiciosYEnlaces'
import { TarjetasPanel } from './TarjetasPanel'
import { ViajesPorBarrio } from './ViajesPorBarrio'

const DESCRIPCION =
  'Último día publicado, frescura del tiempo real, decisiones de las últimas 24 h y estado de los servicios. Todas las cifras son agregados protegidos: los grupos con menos de 10 viajes no se muestran ni se suman.'

function Esqueleto() {
  return (
    <div className="space-y-6" role="status" aria-label="Cargando el panel">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {['viajes', 'barrios', 'decisiones', 'frescura'].map((clave) => (
          <TarjetaKpi key={clave} titulo="Cargando" cargando />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-3">
        <EstadoCargando variante="tarjeta" lineas={6} className="xl:col-span-2" />
        <div className="space-y-6">
          <EstadoCargando variante="tarjeta" lineas={4} />
          <EstadoCargando variante="tarjeta" lineas={4} />
        </div>
      </div>
    </div>
  )
}

export default function PaginaPanel() {
  const panel = usePanel()

  const acciones = (
    <div className="flex items-center gap-2 text-xs text-texto-suave">
      {panel.data && <Antiguedad instante={panel.dataUpdatedAt} sufijo="· cada 60 s" />}
      <Button variant="outline" size="sm" onClick={() => void panel.refetch()} disabled={panel.isFetching}>
        <RefreshCw className={cn(panel.isFetching && 'animate-spin')} aria-hidden />
        Actualizar
      </Button>
    </div>
  )

  return (
    <>
      <EncabezadoPagina titulo="Panel" descripcion={DESCRIPCION} acciones={acciones} />

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
        <div className="space-y-6">
          <TarjetasPanel panel={panel.data} actualizadoEn={panel.dataUpdatedAt} />
          <div className="grid gap-6 xl:grid-cols-3">
            <div className="xl:col-span-2">
              <ViajesPorBarrio ultimoDia={panel.data.ultimo_dia} accesoDisponible={panel.data.acceso_disponible !== false} />
            </div>
            <div className="space-y-6">
              <TarjetaServicios servicios={panel.data.servicios ?? []} />
              <TarjetaEnlaces enlaces={panel.data.enlaces} />
            </div>
          </div>
        </div>
      )}
    </>
  )
}
