/**
 * Barra lateral fija: logotipo, navegación a las secciones y cierre de sesión.
 * El botón de la cabecera la oculta; al cerrarla queda solo el de volver a abrirla, a la izquierda.
 */
import { LogOut, PanelLeftClose, PanelLeftOpen } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { NavLink, useNavigate } from 'react-router'
import { toast } from 'sonner'

import { useCerrarSesion } from '@/api/sesion'
import { Button } from '@/componentes/ui/button'
import { BotonGestos } from '@/gestos/BotonGestos'
import { cn } from '@/lib/utils'

import { LogoTaxi } from './LogoTaxi'
import { SECCIONES } from './navegacion'

export const ANCHO_BARRA = 'w-60'
export function BarraLateral({ abierta, alAlternar }: { abierta: boolean; alAlternar: () => void }) {
  const botonAbrir = useRef<HTMLButtonElement>(null)
  const pendienteFoco = useRef(false)

  useEffect(() => {
    if (!abierta && pendienteFoco.current) {
      pendienteFoco.current = false
      botonAbrir.current?.focus()
    }
  }, [abierta])

  const alternar = () => {
    if (abierta) pendienteFoco.current = true
    alAlternar()
  }
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
    <>
    <aside
      id="menu-lateral"
      aria-hidden={!abierta}
      inert={!abierta}
      className={cn(
        'fixed inset-y-0 left-0 z-30 flex flex-col border-r border-borde bg-white text-slate-600 transition-transform duration-200 motion-reduce:transition-none',
        ANCHO_BARRA,
        abierta ? 'translate-x-0' : '-translate-x-full',
      )}
    >
      <div className="flex items-center gap-2 px-4 pt-5 pb-4">
        <LogoTaxi className="size-9 shrink-0 rounded-xl" />
        <div className="min-w-0 flex-1 leading-tight">
          <p className="truncate text-[15px] font-semibold tracking-tight text-slate-900">PIDS · Taxis NYC</p>
          <p className="truncate text-xs text-slate-500">Plataforma de datos</p>
        </div>
        <button
          type="button"
          onClick={alternar}
          aria-expanded={abierta}
          aria-controls="menu-lateral"
          title="Cerrar el menú"
          className="flex size-8 shrink-0 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#2563eb]"
        >
          <PanelLeftClose className="size-4" aria-hidden />
          <span className="sr-only">Cerrar el menú</span>
        </button>
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

      <div className="px-3 pb-2">
        <p className="px-3 pb-1 text-[11px] font-semibold tracking-wide text-slate-400 uppercase">Parte 1</p>
        <BotonGestos />
      </div>

      <div className="border-t border-borde p-3">
        <Button variant="ghost" className="w-full justify-start text-slate-600" onClick={salir} disabled={cerrar.isPending}>
          <LogOut aria-hidden />
          Cerrar sesión
        </Button>
      </div>
    </aside>
    {!abierta && (
      <button
        ref={botonAbrir}
        type="button"
        onClick={alternar}
        aria-expanded={false}
        aria-controls="menu-lateral"
        title="Abrir el menú"
        className="fixed top-3 left-3 z-40 flex size-9 items-center justify-center rounded-xl border border-borde bg-white text-slate-600 shadow-sm hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#2563eb]"
      >
        <PanelLeftOpen className="size-4" aria-hidden />
        <span className="sr-only">Abrir el menú</span>
      </button>
    )}
    </>
  )
}
