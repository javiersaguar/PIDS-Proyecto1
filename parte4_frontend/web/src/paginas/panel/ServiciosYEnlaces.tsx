/**
 * Tabla inferior del panel: servicios o accesos directos, eligiendo con el control segmentado.
 * Cada fila lleva la marca PNG del servicio, la misma que en la documentación.
 */
import { ExternalLink, LayoutList } from 'lucide-react'
import { useState } from 'react'

import type { Panel, Servicio } from '@/api/tipos'
import { EstadoVacio } from '@/componentes/shell'
import { cn } from '@/lib/utils'

import { MarcaServicio } from './marcas'
import { SelectorSegmentado } from './SelectorSegmentado'

type Vista = 'servicios' | 'accesos'

const TEXTO_ESTADO: Record<Servicio['estado'], string> = {
  ok: 'En marcha',
  caido: 'Caído',
  desconocido: 'Desconocido',
}
const COLOR_ESTADO: Record<Servicio['estado'], string> = {
  ok: 'text-emerald-600',
  caido: 'text-orange-500',
  desconocido: 'text-sky-600',
}

interface Enlace {
  clave: keyof Panel['enlaces']
  titulo: string
  descripcion: string
  /** Sin login: solo responde mientras `make ver` está en marcha (proxy de solo lectura). */
  conVer?: boolean
}

const ENLACES: Enlace[] = [
  { clave: 'grafana', titulo: 'Grafana', descripcion: 'Los mismos cuadros, en su propia ventana' },
  { clave: 'airflow', titulo: 'Airflow', descripcion: 'Cargas históricas' },
  { clave: 'api_acceso', titulo: 'API de acceso', descripcion: 'Documentación interactiva' },
  { clave: 'api_captura', titulo: 'API de captura', descripcion: 'Documentación interactiva' },
  { clave: 'chatbot', titulo: 'Chatbot', descripcion: 'Chainlit con Ollama' },
  { clave: 'chatbot_rag', titulo: 'Chatbot RAG', descripcion: 'Chainlit con documentación' },
  { clave: 'spark', titulo: 'Spark', descripcion: 'Máster, workers y trabajos', conVer: true },
  { clave: 'prometheus', titulo: 'Prometheus', descripcion: 'Métricas y objetivos en bruto', conVer: true },
  { clave: 'seaweed', titulo: 'SeaweedFS (S3)', descripcion: 'Almacenamiento: volúmenes y tamaños, sin ficheros', conVer: true },
  { clave: 'qdrant', titulo: 'Qdrant', descripcion: 'Índice del chatbot RAG', conVer: true },
]

function destinoDe(url: string): string {
  try {
    return new URL(url).host
  } catch {
    return url
  }
}

function Cabecera({ columnas }: { columnas: readonly string[] }) {
  return (
    <thead>
      <tr>
        {columnas.map((columna, indice) => (
          <th
            key={columna || `accion-${indice}`}
            className={cn(
              'bg-slate-100 px-4 py-3 text-left text-xs font-medium text-slate-500',
              indice === 0 && 'rounded-l-xl',
              indice === columnas.length - 1 && 'rounded-r-xl text-right',
            )}
          >
            {columna || <span className="sr-only">Abrir</span>}
          </th>
        ))}
      </tr>
    </thead>
  )
}

function Abrir({ href, nombre }: { href: string; nombre: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      aria-label={`Abrir ${nombre}`}
      className="inline-flex size-8 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-700"
    >
      <ExternalLink className="size-4" aria-hidden />
    </a>
  )
}

function TablaServicios({ servicios }: { servicios: Servicio[] }) {
  if (servicios.length === 0) {
    return <EstadoVacio titulo="Sin información de servicios" descripcion="El BFF no ha devuelto ningún servicio." className="border-0 bg-transparent py-8" />
  }
  return (
    <table aria-label="Servicios de la plataforma" className="w-full border-separate border-spacing-0 text-sm">
      <Cabecera columnas={['Servicio', 'Job', 'Estado', '']} />
      <tbody>
        {servicios.map((servicio, indice) => {
          const estado = servicio.estado in TEXTO_ESTADO ? servicio.estado : 'desconocido'
          const borde = indice < servicios.length - 1 ? 'border-b border-slate-100' : ''
          return (
            <tr key={`${servicio.job}|${servicio.nombre}|${indice}`}>
              <td className={cn('px-4 py-3.5', borde)}>
                <span className="flex items-center gap-3">
                  <MarcaServicio textos={[servicio.nombre, servicio.job]} />
                  <span className="font-medium text-slate-900">{servicio.nombre}</span>
                </span>
              </td>
              <td className={cn('px-4 py-3.5 text-slate-500', borde)}>{servicio.job || '—'}</td>
              <td className={cn('px-4 py-3.5 font-medium', COLOR_ESTADO[estado], borde)}>{TEXTO_ESTADO[estado]}</td>
              <td className={cn('px-4 py-3.5 text-right', borde)}>{servicio.enlace && <Abrir href={servicio.enlace} nombre={servicio.nombre} />}</td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

function TablaAccesos({ enlaces }: { enlaces: Panel['enlaces'] | undefined }) {
  const disponibles = ENLACES.filter((enlace) => enlaces?.[enlace.clave])
  if (disponibles.length === 0) {
    return <EstadoVacio titulo="Sin enlaces configurados" descripcion="Las variables ENLACES_* del BFF están vacías." className="border-0 bg-transparent py-8" />
  }
  const hayConVer = disponibles.some((enlace) => enlace.conVer)
  return (
    <>
      <table aria-label="Accesos directos" className="w-full border-separate border-spacing-0 text-sm">
        <Cabecera columnas={['Acceso', 'Descripción', 'Destino', '']} />
        <tbody>
          {disponibles.map((enlace, indice) => {
            const href = enlaces?.[enlace.clave] ?? ''
            const borde = indice < disponibles.length - 1 ? 'border-b border-slate-100' : ''
            return (
              <tr key={enlace.clave}>
                <td className={cn('px-4 py-3.5', borde)}>
                  <span className="flex items-center gap-3">
                    <MarcaServicio textos={[enlace.titulo, enlace.clave]} />
                    <span className="font-medium text-slate-900">{enlace.titulo}</span>
                  </span>
                </td>
                <td className={cn('px-4 py-3.5 text-slate-500', borde)}>
                  {enlace.descripcion}
                  {enlace.conVer && (
                    <span className="ml-2 rounded-md bg-amber-50 px-1.5 py-0.5 font-mono text-xs text-amber-700">make ver</span>
                  )}
                </td>
                <td className={cn('cifra px-4 py-3.5 text-slate-700', borde)}>{destinoDe(href)}</td>
                <td className={cn('px-4 py-3.5 text-right', borde)}>
                  <Abrir href={href} nombre={enlace.titulo} />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      {hayConVer && (
        <p className="px-4 pt-3 text-xs text-slate-500">
          Los marcados con <span className="font-mono">make ver</span> no tienen login: solo se abren mientras ese comando
          está en marcha, de solo lectura, y se cierran con <span className="font-mono">make ver-cerrar</span>. La consola de
          Redpanda y los ficheros de SeaweedFS no se abren nunca: llevan viajes individuales. Todas las direcciones:{' '}
          <span className="font-mono">make localhost</span>.
        </p>
      )}
    </>
  )
}

export function TablaPlataforma({ servicios, enlaces }: { servicios: Servicio[]; enlaces: Panel['enlaces'] | undefined }) {
  const [vista, setVista] = useState<Vista>('servicios')
  return (
    <section className="rounded-2xl border border-slate-200/80 bg-white px-5 py-4 shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className="flex size-9 items-center justify-center rounded-xl bg-sky-50 text-sky-600" aria-hidden>
            <LayoutList className="size-4" />
          </span>
          <h2 className="text-[15px] text-slate-900">{vista === 'servicios' ? 'Servicios' : 'Accesos directos'}</h2>
        </div>
        <SelectorSegmentado
          etiqueta="Contenido de la tabla"
          valor={vista}
          opciones={[
            { valor: 'servicios', texto: 'Servicios' },
            { valor: 'accesos', texto: 'Accesos directos' },
          ]}
          alCambiar={setVista}
        />
      </div>
      {vista === 'servicios' ? <TablaServicios servicios={servicios} /> : <TablaAccesos enlaces={enlaces} />}
    </section>
  )
}
