/**
 * Esqueleto de la aplicación autenticada: barra lateral fija, contenido (`<Outlet />`) y TAXI AI, el asistente,
 * como botón fijo abajo a la derecha con su panel deslizante (disponible en todas las páginas, sin ruta propia).
 * El grafo ocupa todo el hueco, sin cabecera. El panel, el explorador, privacidad, tiempo real y
 * operaciones tampoco llevan cabecera: el título de la sección ya está en la barra lateral.
 */
import { useCallback, useRef, useState } from 'react'
import { Outlet, useLocation } from 'react-router'

import { cn } from '@/lib/utils'

import { BarraLateral } from './BarraLateral'
import { BotonTaxiAI } from './BotonTaxiAI'
import { Cabecera } from './Cabecera'
import { PanelAsistente } from './PanelAsistente'

export function AppShell() {
  const { pathname, state, key } = useLocation()
  const [asistenteAbierto, setAsistenteAbierto] = useState(false)
  const [navegacionAtendida, setNavegacionAtendida] = useState<string | null>(null)
  const botonRef = useRef<HTMLButtonElement>(null)

  // La antigua ruta /asistente redirige a la portada pidiendo abrir el panel (rutas.tsx): se atiende una vez por
  // navegación (estado derivado de la ubicación, ajustado en el render).
  const pideAbrir = (state as { asistente?: boolean } | null)?.asistente === true
  if (pideAbrir && key !== navegacionAtendida) {
    setNavegacionAtendida(key)
    setAsistenteAbierto(true)
  }

  const cerrarAsistente = useCallback(() => setAsistenteAbierto(false), [])
  const alternarAsistente = useCallback(() => setAsistenteAbierto((abierto) => !abierto), [])

  const lienzo = pathname === '/grafo' || pathname.startsWith('/grafo/')
  const esPanel = pathname === '/'
  const esPrivacidad = pathname === '/privacidad' || pathname.startsWith('/privacidad/')
  const esExplorador = pathname === '/explorador' || pathname.startsWith('/explorador/')
  const esTiempoReal = pathname === '/tiempo-real' || pathname.startsWith('/tiempo-real/')
  const esOperaciones = pathname === '/operaciones' || pathname.startsWith('/operaciones/')
  const esObservabilidad = pathname === '/observabilidad' || pathname.startsWith('/observabilidad/')
  const amplio = esPanel || esExplorador || esTiempoReal || esOperaciones || esObservabilidad

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
        {!lienzo && !amplio && !esPrivacidad && <Cabecera />}
        <main
          id="contenido"
          tabIndex={-1}
          className={cn(lienzo ? 'h-svh overflow-hidden outline-none' : 'flex-1 outline-none', amplio && 'bg-[#f3f6fb] px-4 py-4 sm:px-6 sm:py-5', !lienzo && !amplio && 'px-6 py-6')}
        >
          {lienzo ? (
            <Outlet />
          ) : (
            <div className={cn('mx-auto w-full', esExplorador || esObservabilidad ? 'max-w-none' : 'max-w-7xl')}>
              <Outlet />
            </div>
          )}
        </main>
      </div>
      <BotonTaxiAI ref={botonRef} abierto={asistenteAbierto} alPulsar={alternarAsistente} />
      <PanelAsistente abierto={asistenteAbierto} alCerrar={cerrarAsistente} botonRef={botonRef} />
    </div>
  )
}
