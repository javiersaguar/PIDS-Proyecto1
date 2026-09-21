/**
 * Barra lateral fija: logotipo textual, navegación a las siete secciones (elemento activo en el amarillo taxi)
 * y una nota discreta del escenario.
 */
import { CarTaxiFront } from 'lucide-react'
import { NavLink } from 'react-router'

import { cn } from '@/lib/utils'

import { SECCIONES } from './navegacion'

export const ANCHO_BARRA = 'w-60'

export function BarraLateral() {
  return (
    <aside
      className={cn(
        'fondo-marino fixed inset-y-0 left-0 z-30 flex flex-col border-r border-sidebar-border text-sidebar-foreground',
        ANCHO_BARRA,
      )}
    >
      <div className="flex items-center gap-3 px-5 pt-5 pb-4">
        <span className="flex size-9 items-center justify-center rounded-lg bg-acento text-primario shadow-sm" aria-hidden>
          <CarTaxiFront className="size-5" strokeWidth={2.25} />
        </span>
        <div className="leading-tight">
          <p className="text-[15px] font-semibold tracking-tight text-white">PIDS · Taxis NYC</p>
          <p className="text-xs text-sidebar-foreground/70">Plataforma de datos · E3</p>
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
                    'flex items-center gap-3 rounded-lg px-3 py-2 text-[13.5px] font-medium transition-colors',
                    'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sidebar-ring',
                    isActive
                      ? 'bg-acento text-primario shadow-sm'
                      : 'text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
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

      <div className="border-t border-sidebar-border px-5 py-4 text-xs leading-relaxed text-sidebar-foreground/70">
        <p className="font-medium text-sidebar-foreground/90">Privacidad total</p>
        <p>Solo agregados con al menos 10 viajes. Ninguna vista muestra viajes individuales.</p>
      </div>
    </aside>
  )
}
