/**
 * Esqueleto de la aplicación autenticada: barra lateral fija, cabecera, contenido (`<Outlet />`) y pie.
 */
import { Outlet } from 'react-router'

import { BarraLateral } from './BarraLateral'
import { Cabecera } from './Cabecera'
import { Pie } from './Pie'

export function AppShell() {
  return (
    <div className="min-h-svh bg-fondo">
      <a
        href="#contenido"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-superficie focus:px-3 focus:py-2 focus:shadow-md"
      >
        Saltar al contenido
      </a>
      <BarraLateral />
      <div className="flex min-h-svh flex-col pl-60">
        <Cabecera />
        <main id="contenido" tabIndex={-1} className="flex-1 px-6 py-6 outline-none">
          <div className="mx-auto w-full max-w-7xl">
            <Outlet />
          </div>
        </main>
        <Pie />
      </div>
    </div>
  )
}
