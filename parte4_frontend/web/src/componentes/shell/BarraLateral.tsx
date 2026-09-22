/**
 * Barra lateral fija: logotipo, navegación a las seis secciones, botón para contraerla o expandirla y cierre
 * de sesión. Contraída (4 rem) muestra solo los iconos, con el título de cada sección como descripción
 * emergente y como texto solo para lectores de pantalla; la preferencia se recuerda (`menuLateral.ts`).
 */
import { LogOut, PanelLeftClose, PanelLeftOpen, type LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { NavLink, useMatch, useNavigate } from 'react-router'
import { toast } from 'sonner'

import { useCerrarSesion } from '@/api/sesion'
import { Button } from '@/componentes/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/componentes/ui/tooltip'
import { cn } from '@/lib/utils'

import { LogoTaxi } from './LogoTaxi'
import { ANCHO_BARRA, ID_MENU_SECCIONES } from './menuLateral'
import { SECCIONES } from './navegacion'

export { ANCHO_BARRA } from './menuLateral'

interface Props {
  contraida: boolean
  alAlternar: () => void
}

/** Con la barra contraída, la descripción emergente a la derecha sustituye al texto visible. */
function ConDescripcion({ texto, activa, children }: { texto: string; activa: boolean; children: ReactNode }) {
  if (!activa) return <>{children}</>
  return (
    <Tooltip>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent side="right" sideOffset={6}>
        {texto}
      </TooltipContent>
    </Tooltip>
  )
}

function EnlaceSeccion({ ruta, titulo, icono: Icono, contraida }: { ruta: string; titulo: string; icono: LucideIcon; contraida: boolean }) {
  // La sección activa se calcula aquí (y no con el `className` en forma de función de NavLink) porque el
  // disparador del tooltip (`asChild`) concatena los `className` como cadenas.
  const activa = useMatch({ path: ruta, end: ruta === '/' }) !== null
  return (
    <ConDescripcion texto={titulo} activa={contraida}>
      <NavLink
        to={ruta}
        end={ruta === '/'}
        className={cn(
          'flex items-center gap-3 rounded-xl py-2 text-[13.5px] font-medium transition-colors',
          contraida ? 'justify-center px-0' : 'px-3',
          'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#2563eb]',
          activa ? 'bg-[#e8f1ff] text-[#1d4ed8]' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900',
        )}
      >
        <Icono className={cn('shrink-0', contraida ? 'size-[18px]' : 'size-4')} aria-hidden />
        <span className={contraida ? 'sr-only' : 'truncate'}>{titulo}</span>
      </NavLink>
    </ConDescripcion>
  )
}

export function BarraLateral({ contraida, alAlternar }: Props) {
  const navegar = useNavigate()
  const cerrar = useCerrarSesion()

  const salir = () => {
    cerrar.mutate(undefined, {
      onSuccess: () => toast.success('Sesión cerrada'),
      onError: () => toast.error('No se ha podido cerrar la sesión en el servidor; se ha borrado en este navegador'),
      onSettled: () => void navegar('/acceso', { replace: true }),
    })
  }

  const textoAlternar = contraida ? 'Expandir el menú' : 'Contraer el menú'

  return (
    <aside
      data-estado={contraida ? 'contraido' : 'expandido'}
      className={cn(
        'fixed inset-y-0 left-0 z-30 flex flex-col overflow-hidden border-r border-borde bg-white text-slate-600',
        'transition-[width] duration-200 ease-out motion-reduce:transition-none',
        contraida ? ANCHO_BARRA.contraido : ANCHO_BARRA.expandido,
      )}
    >
      <div className={cn('flex items-center gap-3 pt-5 pb-4', contraida ? 'justify-center px-3' : 'px-5')}>
        <LogoTaxi className="size-9 rounded-xl" />
        <div className={cn('leading-tight', contraida && 'sr-only')}>
          <p className="text-[15px] font-semibold tracking-tight text-slate-900">PIDS · Taxis NYC</p>
          <p className="text-xs text-slate-500">Plataforma de datos</p>
        </div>
      </div>

      <nav id={ID_MENU_SECCIONES} aria-label="Secciones del portal" className="mt-2 flex-1 px-3">
        <ul className="space-y-0.5">
          {SECCIONES.map((seccion) => (
            <li key={seccion.ruta}>
              <EnlaceSeccion {...seccion} contraida={contraida} />
            </li>
          ))}
        </ul>
      </nav>

      <div className="space-y-0.5 border-t border-borde p-3">
        <ConDescripcion texto={textoAlternar} activa={contraida}>
          <Button
            variant="ghost"
            className={cn('w-full text-slate-600', contraida ? 'justify-center px-0' : 'justify-start')}
            onClick={alAlternar}
            aria-expanded={!contraida}
            aria-controls={ID_MENU_SECCIONES}
          >
            {contraida ? <PanelLeftOpen aria-hidden /> : <PanelLeftClose aria-hidden />}
            <span className={contraida ? 'sr-only' : undefined}>{textoAlternar}</span>
          </Button>
        </ConDescripcion>
        <ConDescripcion texto="Cerrar sesión" activa={contraida}>
          <Button
            variant="ghost"
            className={cn('w-full text-slate-600', contraida ? 'justify-center px-0' : 'justify-start')}
            onClick={salir}
            disabled={cerrar.isPending}
          >
            <LogOut aria-hidden />
            <span className={contraida ? 'sr-only' : undefined}>Cerrar sesión</span>
          </Button>
        </ConDescripcion>
      </div>
    </aside>
  )
}
