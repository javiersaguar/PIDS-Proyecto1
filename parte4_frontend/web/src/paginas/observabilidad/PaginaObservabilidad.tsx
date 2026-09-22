/**
 * Los cuadros de Grafana, dentro del portal. Grafana se incrusta en modo kiosco (sin su menú) y sigue
 * siendo el sitio donde viven las alertas. Si no hay URL, se explica en vez de un marco vacío.
 */
import { ExternalLink } from 'lucide-react'
import { useState } from 'react'

import { usePanel } from '@/api/panel'
import { EstadoError, EstadoVacio } from '@/componentes/shell'
import { cn } from '@/lib/utils'

import { CUADROS, incrustable, urlCuadro } from './cuadros'

export default function PaginaObservabilidad() {
  const panel = usePanel()
  const [uid, setUid] = useState(CUADROS[0].uid)
  const activo = CUADROS.find((cuadro) => cuadro.uid === uid) ?? CUADROS[0]
  const base = panel.data?.enlaces?.grafana

  return (
    <>
      <h1 className="sr-only">Observabilidad</h1>
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-sm text-slate-500">Prometheus mide la plataforma. Estos cuadros no ven viajes sueltos.</p>
          </div>
          {base && (
            <a
              href={base}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1.5 text-xs font-semibold text-[#2f62c4] shadow-sm hover:bg-[#eaf2ff]"
            >
              Abrir Grafana
              <ExternalLink className="size-3.5" aria-hidden />
            </a>
          )}
        </div>

        <div role="tablist" aria-label="Cuadros de mando" className="flex gap-2 overflow-x-auto pb-1">
          {CUADROS.map((cuadro) => {
            const elegido = cuadro.uid === activo.uid
            return (
              <button
                key={cuadro.uid}
                type="button"
                role="tab"
                aria-selected={elegido}
                onClick={() => setUid(cuadro.uid)}
                className={cn(
                  'shrink-0 rounded-2xl border px-3.5 py-2 text-left transition',
                  elegido
                    ? 'border-[#2f62c4] bg-white shadow-sm'
                    : 'border-transparent bg-white/70 hover:bg-white',
                )}
              >
                <span className={cn('block text-sm font-semibold', elegido ? 'text-[#2f62c4]' : 'text-slate-700')}>{cuadro.titulo}</span>
                <span className="block text-[11px] text-slate-500">{cuadro.texto}</span>
              </button>
            )
          })}
        </div>

        {panel.isError ? (
          <EstadoError error={panel.error} titulo="No se ha podido saber dónde está Grafana" alReintentar={() => void panel.refetch()} reintentando={panel.isFetching} />
        ) : !panel.isPending && !base ? (
          <EstadoVacio
            titulo="Grafana no está configurado"
            descripcion="Falta ENLACES_GRAFANA en el portal. Los cuadros siguen en el servicio, si está levantado."
          />
        ) : !panel.isPending && base && !incrustable(base) ? (
          <EstadoVacio
            titulo="Los cuadros se ven desde el equipo de la plataforma"
            descripcion="Grafana solo escucha en ese equipo (127.0.0.1): ábrelo desde el portal local, http://localhost:8020, o con «Abrir Grafana»."
          />
        ) : panel.isPending || !base ? (
          <div className="h-[calc(100svh-13.5rem)] min-h-[32rem] animate-pulse rounded-2xl bg-white" role="status" aria-label="Cargando el cuadro" />
        ) : (
          <iframe
            title={`Cuadro ${activo.titulo}`}
            src={urlCuadro(base, activo.uid)}
            className="h-[calc(100svh-13.5rem)] min-h-[32rem] w-full rounded-2xl border border-[#e6edf5] bg-white"
          />
        )}
      </div>
    </>
  )
}
