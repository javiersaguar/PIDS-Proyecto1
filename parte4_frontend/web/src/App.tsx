/**
 * Raíz de la aplicación: proveedores (TanStack Query, tooltips, avisos) y el enrutador.
 */
import { QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import { RouterProvider } from 'react-router'

import { Toaster } from '@/componentes/ui/sonner'
import { TooltipProvider } from '@/componentes/ui/tooltip'
import { crearClienteConsultas } from '@/lib/consultas'
import { crearEnrutador } from '@/rutas'

export default function App() {
  const [cliente] = useState(crearClienteConsultas)
  const [enrutador] = useState(crearEnrutador)
  return (
    <QueryClientProvider client={cliente}>
      <TooltipProvider>
        <RouterProvider router={enrutador} />
        <Toaster theme="light" position="bottom-right" richColors closeButton />
      </TooltipProvider>
    </QueryClientProvider>
  )
}
