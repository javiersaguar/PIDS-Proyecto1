/**
 * Los cuadros de Grafana, dentro del portal y dibujados por él: los mismos ocho cuadros, con sus paneles en el mismo
 * sitio, pero con los componentes y las animaciones del resto de la app. El BFF lee los JSON de Grafana y ejecuta en
 * Prometheus solo esas consultas (`bff/servicios/observabilidad.py`), así que se ven igual desde el equipo, por el
 * túnel de la web pública y, con datos grabados, en la demostración. Grafana sigue siendo el sitio de las alertas y
 * de editar los cuadros: desde el equipo de la plataforma hay un enlace a cada uno.
 */
import { AlertTriangle, ExternalLink, Info } from 'lucide-react'
import { useState } from 'react'

import { useCuadro, useCuadros, type Cuadro } from '@/api/observabilidad'
import { usePanel } from '@/api/panel'
import { Antiguedad } from '@/componentes/datos/Antiguedad'
import { EstadoError } from '@/componentes/shell'
import { Skeleton } from '@/componentes/ui/skeleton'
import { cn } from '@/lib/utils'

import { CuadroNativo } from './CuadroNativo'
import { CUADROS, incrustable, urlCuadro } from './cuadros'
import { describirPeriodo } from './formatoUnidad'

function fechaGrabacion(iso: string): string {
  const fecha = new Date(iso)
  const dia = fecha.toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' })
  return `${dia} a las ${fecha.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}`
}

function Actualizacion({ cuadro }: { cuadro: Cuadro }) {
  if (cuadro.grabado) {
    return <span>Datos grabados el {fechaGrabacion(cuadro.grabado)}</span>
  }
  return <Antiguedad instante={cuadro.actualizado * 1000} sufijo="· se refresca cada 30 s" />
}

function CuadroCargando() {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4" role="status" aria-label="Cargando el cuadro">
      {Array.from({ length: 4 }, (_, i) => <Skeleton key={`s${i}`} className="h-36 rounded-2xl" />)}
      {Array.from({ length: 2 }, (_, i) => <Skeleton key={`g${i}`} className="col-span-2 h-72 rounded-2xl" />)}
    </div>
  )
}

export default function PaginaObservabilidad() {
  const panel = usePanel()
  const lista = useCuadros()
  const [uid, setUid] = useState(CUADROS[0].uid)
  const cuadro = useCuadro(uid)
  const base = panel.data?.enlaces?.grafana
  const local = base ? incrustable(base) : false
  const textos = new Map(CUADROS.map((c) => [c.uid, c.texto]))
  const pestanas = (lista.data ?? CUADROS).map((c) => ({ uid: c.uid, titulo: c.titulo, texto: textos.get(c.uid) ?? '' }))
  const datos = cuadro.data
  const cambiando = cuadro.isPlaceholderData

  return (
    <>
      <h1 className="sr-only">Observabilidad</h1>
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="grid gap-0.5">
            <p className="text-sm text-slate-500">
              Los cuadros de Grafana, con los datos de Prometheus: miden la plataforma, nunca viajes sueltos.
            </p>
            {datos && !cambiando && (
              <p className="text-xs text-slate-400">
                {describirPeriodo(datos.periodo).replace(/^./, (l) => l.toUpperCase())} · <Actualizacion cuadro={datos} />
              </p>
            )}
          </div>
          {base && local && (
            <a
              href={urlCuadro(base, uid)}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1.5 text-xs font-semibold text-[#2f62c4] shadow-sm hover:bg-[#eaf2ff]"
            >
              Abrir en Grafana
              <ExternalLink className="size-3.5" aria-hidden />
            </a>
          )}
        </div>

        {base && !local && !panel.isPending && (
          <p className="flex items-start gap-2 rounded-2xl bg-[#eef4ff] px-4 py-2.5 text-xs text-slate-600">
            <Info className="mt-px size-3.5 shrink-0 text-[#2f62c4]" aria-hidden />
            <span>
              Son los mismos cuadros que en Grafana. Grafana completo (alertas, edición, zoom del periodo) solo se abre
              desde el equipo de la plataforma: <span className="font-medium">http://localhost:3000</span>, o «Abrir en
              Grafana» en el portal local (http://localhost:8020).
            </span>
          </p>
        )}

        <div role="tablist" aria-label="Cuadros de mando" className="flex gap-2 overflow-x-auto pb-1">
          {pestanas.map((pestana) => {
            const elegido = pestana.uid === uid
            return (
              <button
                key={pestana.uid}
                type="button"
                role="tab"
                aria-selected={elegido}
                onClick={() => setUid(pestana.uid)}
                className={cn(
                  'shrink-0 rounded-2xl border px-3.5 py-2 text-left transition',
                  elegido ? 'border-[#2f62c4] bg-white shadow-sm' : 'border-transparent bg-white/70 hover:bg-white',
                )}
              >
                <span className={cn('block text-sm font-semibold', elegido ? 'text-[#2f62c4]' : 'text-slate-700')}>{pestana.titulo}</span>
                {pestana.texto && <span className="block text-[11px] text-slate-500">{pestana.texto}</span>}
              </button>
            )
          })}
        </div>

        {cuadro.isError && !datos ? (
          <EstadoError
            error={cuadro.error}
            titulo="No se ha podido cargar el cuadro"
            alReintentar={() => void cuadro.refetch()}
            reintentando={cuadro.isFetching}
          />
        ) : !datos ? (
          <CuadroCargando />
        ) : (
          <div role="tabpanel" aria-label={`Cuadro ${datos.titulo}`} className={cn('grid gap-3 transition-opacity duration-300', cambiando && 'opacity-60')}>
            {!datos.disponible && (
              <p className="flex items-center gap-2 rounded-2xl bg-amber-50 px-4 py-2.5 text-xs text-amber-800">
                <AlertTriangle className="size-3.5 shrink-0" aria-hidden />
                Prometheus no responde: los paneles se quedan vacíos hasta que vuelva.
              </p>
            )}
            <CuadroNativo key={datos.uid} cuadro={datos} />
          </div>
        )}
      </div>
    </>
  )
}
