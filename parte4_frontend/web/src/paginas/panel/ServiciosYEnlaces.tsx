/**
 * Tarjetas laterales del panel: estado de los servicios (ok / caído / desconocido) y accesos directos a
 * Grafana, Airflow, Spark, las APIs y los dos chatbots (se abren en una pestaña nueva).
 */
import { Bot, BookOpenText, ExternalLink, Gauge, type LucideIcon, Server, Waypoints, Workflow } from 'lucide-react'

import type { Panel, Servicio } from '@/api/tipos'
import { EstadoVacio } from '@/componentes/shell'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/componentes/ui/card'
import { cn } from '@/lib/utils'

const COLOR_ESTADO: Record<Servicio['estado'], string> = {
  ok: 'bg-ok',
  caido: 'bg-peligro',
  desconocido: 'bg-texto-suave/50',
}
const TEXTO_ESTADO: Record<Servicio['estado'], string> = {
  ok: 'en marcha',
  caido: 'caído',
  desconocido: 'desconocido',
}
const COLOR_TEXTO_ESTADO: Record<Servicio['estado'], string> = {
  ok: 'text-ok',
  caido: 'text-peligro',
  desconocido: 'text-texto-suave',
}

interface Enlace {
  clave: keyof Panel['enlaces']
  titulo: string
  descripcion: string
  icono: LucideIcon
}

const ENLACES: Enlace[] = [
  { clave: 'grafana', titulo: 'Grafana', descripcion: 'Cuadros de mando y alertas', icono: Gauge },
  { clave: 'airflow', titulo: 'Airflow', descripcion: 'Cargas históricas', icono: Workflow },
  { clave: 'spark', titulo: 'Spark', descripcion: 'Trabajos por lotes y streaming', icono: Waypoints },
  { clave: 'api_acceso', titulo: 'API de acceso', descripcion: 'Documentación interactiva', icono: BookOpenText },
  { clave: 'api_captura', titulo: 'API de captura', descripcion: 'Documentación interactiva', icono: Server },
  { clave: 'chatbot', titulo: 'Chatbot', descripcion: 'Chainlit con Ollama', icono: Bot },
  { clave: 'chatbot_rag', titulo: 'Chatbot RAG', descripcion: 'Chainlit con documentación', icono: Bot },
]

export function TarjetaServicios({ servicios }: { servicios: Servicio[] }) {
  return (
    <Card className="sombra-tarjeta">
      <CardHeader>
        <CardTitle className="text-xl text-primario">Servicios</CardTitle>
        <CardDescription>Estado según Prometheus y las rutas de salud de las APIs.</CardDescription>
      </CardHeader>
      <CardContent>
        {servicios.length === 0 ? (
          <EstadoVacio titulo="Sin información de servicios" descripcion="El BFF no ha devuelto ningún servicio." className="py-6" />
        ) : (
          <ul className="divide-y" aria-label="Servicios de la plataforma">
            {servicios.map((s, indice) => (
              <li key={`${s.job}|${s.nombre}|${indice}`} className="flex items-center justify-between gap-3 py-2 first:pt-0 last:pb-0">
                <span className="flex min-w-0 items-center gap-2.5">
                  <span className={cn('size-2.5 shrink-0 rounded-full', COLOR_ESTADO[s.estado] ?? COLOR_ESTADO.desconocido)} aria-hidden />
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{s.nombre}</span>
                    {s.job && <span className="block truncate text-xs text-texto-suave">job {s.job}</span>}
                  </span>
                </span>
                <span className="flex shrink-0 items-center gap-2">
                  <span className={cn('text-xs font-medium', COLOR_TEXTO_ESTADO[s.estado] ?? COLOR_TEXTO_ESTADO.desconocido)}>
                    {TEXTO_ESTADO[s.estado] ?? TEXTO_ESTADO.desconocido}
                  </span>
                  {s.enlace && (
                    <a
                      href={s.enlace}
                      target="_blank"
                      rel="noreferrer"
                      className="rounded-sm text-texto-suave hover:text-foreground"
                      aria-label={`Abrir ${s.nombre} en una pestaña nueva`}
                    >
                      <ExternalLink className="size-3.5" aria-hidden />
                    </a>
                  )}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

export function TarjetaEnlaces({ enlaces }: { enlaces: Panel['enlaces'] | undefined }) {
  const disponibles = ENLACES.filter((e) => enlaces?.[e.clave])
  return (
    <Card className="sombra-tarjeta">
      <CardHeader>
        <CardTitle className="text-xl text-primario">Accesos directos</CardTitle>
        <CardDescription>Herramientas de la plataforma; se abren en una pestaña nueva.</CardDescription>
      </CardHeader>
      <CardContent>
        {disponibles.length === 0 ? (
          <EstadoVacio titulo="Sin enlaces configurados" descripcion="Las variables ENLACES_* del BFF están vacías." className="py-6" />
        ) : (
          <ul className="grid gap-2 sm:grid-cols-2 xl:grid-cols-1" aria-label="Accesos directos">
            {disponibles.map(({ clave, titulo, descripcion, icono: Icono }) => (
              <li key={clave}>
                <a
                  href={enlaces?.[clave]}
                  target="_blank"
                  rel="noreferrer"
                  className="group flex items-center gap-3 rounded-lg border px-3 py-2 transition-colors hover:border-primario/30 hover:bg-muted"
                >
                  <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primario/5 text-primario" aria-hidden>
                    <Icono className="size-4" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium">{titulo}</span>
                    <span className="block truncate text-xs text-texto-suave">{descripcion}</span>
                  </span>
                  <ExternalLink className="size-3.5 shrink-0 text-texto-suave group-hover:text-foreground" aria-hidden />
                </a>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
