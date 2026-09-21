/**
 * Cabecera: título de la sección activa, chips con el estado de los servicios (`GET /api/panel` → `servicios`)
 * y el botón «Cerrar sesión».
 */
import { LogOut } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router'
import { toast } from 'sonner'

import { useCerrarSesion } from '@/api/sesion'
import type { Servicio } from '@/api/tipos'
import { Button } from '@/componentes/ui/button'
import { Separator } from '@/componentes/ui/separator'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/componentes/ui/tooltip'
import { cn } from '@/lib/utils'

import { seccionDe } from './navegacion'
import { useEstadoServicios } from './servicios'

const COLOR_ESTADO: Record<Servicio['estado'], string> = {
  ok: 'bg-ok',
  caido: 'bg-peligro',
  desconocido: 'bg-texto-suave/60',
}
const TEXTO_ESTADO: Record<Servicio['estado'], string> = {
  ok: 'en marcha',
  caido: 'caído',
  desconocido: 'estado desconocido',
}

function ChipServicio({ servicio }: { servicio: Servicio }) {
  const contenido = (
    <>
      <span className={cn('size-2 rounded-full', COLOR_ESTADO[servicio.estado])} aria-hidden />
      <span>{servicio.nombre}</span>
    </>
  )
  const clases =
    'inline-flex h-6 items-center gap-1.5 rounded-full border bg-superficie px-2 text-xs font-medium text-foreground'
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        {servicio.enlace ? (
          <a href={servicio.enlace} target="_blank" rel="noreferrer" className={cn(clases, 'hover:bg-muted')}>
            {contenido}
          </a>
        ) : (
          <span className={clases}>{contenido}</span>
        )}
      </TooltipTrigger>
      <TooltipContent>
        {servicio.nombre}: {TEXTO_ESTADO[servicio.estado]}
        {servicio.job && <span className="text-muted-foreground"> · job {servicio.job}</span>}
      </TooltipContent>
    </Tooltip>
  )
}

function ChipsServicios() {
  const { data: servicios } = useEstadoServicios()
  if (!servicios?.length) return null
  return (
    <ul aria-label="Estado de los servicios" className="hidden items-center gap-1.5 lg:flex">
      {servicios.map((s) => (
        <li key={s.job || s.nombre}>
          <ChipServicio servicio={s} />
        </li>
      ))}
    </ul>
  )
}

export function Cabecera() {
  const { pathname } = useLocation()
  const navegar = useNavigate()
  const cerrar = useCerrarSesion()
  const seccion = seccionDe(pathname)
  const Icono = seccion?.icono

  const salir = () => {
    cerrar.mutate(undefined, {
      onSuccess: () => toast.success('Sesión cerrada'),
      onError: () => toast.error('No se ha podido cerrar la sesión en el servidor; se ha borrado en este navegador'),
      onSettled: () => void navegar('/acceso', { replace: true }),
    })
  }

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-4 border-b bg-superficie/90 px-6 backdrop-blur">
      <div className="flex min-w-0 items-center gap-2">
        {Icono && <Icono className="size-4 text-texto-suave" aria-hidden />}
        <p className="truncate text-[15px] font-semibold text-primario">{seccion?.titulo ?? 'Página no encontrada'}</p>
      </div>
      <div className="ml-auto flex items-center gap-3">
        <ChipsServicios />
        <Separator orientation="vertical" className="hidden h-5! lg:block" />
        <Button variant="ghost" size="sm" onClick={salir} disabled={cerrar.isPending}>
          <LogOut aria-hidden />
          Cerrar sesión
        </Button>
      </div>
    </header>
  )
}
