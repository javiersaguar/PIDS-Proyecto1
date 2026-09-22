/**
 * Barra lateral fija: logotipo, navegación a las secciones y cierre de sesión.
 */
import { LogOut } from 'lucide-react'
import { NavLink, useNavigate } from 'react-router'
import { toast } from 'sonner'

import { useCerrarSesion } from '@/api/sesion'
import { Button } from '@/componentes/ui/button'
import { cn } from '@/lib/utils'

import { LogoTaxi } from './LogoTaxi'
import { SECCIONES } from './navegacion'

export const ANCHO_BARRA = 'w-60'

export function BarraLateral() {
  const navegar = useNavigate()
  const cerrar = useCerrarSesion()

  const salir = () => {
    cerrar.mutate(undefined, {
      onSuccess: () => toast.success('Sesión cerrada'),
      onError: () => toast.error('No se ha podido cerrar la sesión en el servidor; se ha borrado en este navegador'),
      onSettled: () => void navegar('/acceso', { replace: true }),
    })
  }

  return (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-30 flex flex-col border-r border-borde bg-white text-slate-600',
        ANCHO_BARRA,
      )}
    >
      <div className="flex items-center gap-3 px-5 pt-5 pb-4">
        <LogoTaxi className="size-9 rounded-xl" />
        <div className="leading-tight">
          <p className="text-[15px] font-semibold tracking-tight text-slate-900">PIDS · Taxis NYC</p>
          <p className="text-xs text-slate-500">Plataforma de datos</p>
        </div>
      </div>

      <nav aria-label="Secciones del portal" className="mt-2 flex-1 px-3">
        <ul className="space-y-0.5">
          {SECCIONES.map(({ ruta, titulo, icono: Icono }) => (
            <li key={ruta}>
              <NavLink
                to={ruta}
                end={ruta === '/'}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 rounded-xl px-3 py-2 text-[13.5px] font-medium transition-colors',
                    'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#2563eb]',
                    isActive ? 'bg-[#e8f1ff] text-[#1d4ed8]' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900',
                  )
                }
              >
                <Icono className="size-4 shrink-0" aria-hidden />
                <span className="truncate">{titulo}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <div className="border-t border-borde p-3">
        <Button variant="ghost" className="w-full justify-start text-slate-600" onClick={salir} disabled={cerrar.isPending}>
          <LogOut aria-hidden />
          Cerrar sesión
        </Button>
      </div>
    </aside>
  )
}
