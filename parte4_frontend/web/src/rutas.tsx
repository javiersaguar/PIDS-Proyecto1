/**
 * Rutas del portal (§6). `/acceso` va suelta; el resto cuelga de la guardia de sesión y del shell.
 * Las páginas se importan directamente (sin `lazy`). El asistente (TAXI AI) no tiene ruta: vive en el shell.
 */
import { createBrowserRouter, createMemoryRouter, Navigate, type RouteObject } from 'react-router'

import { AppShell } from '@/componentes/shell/AppShell'
import { GuardiaSesion } from '@/componentes/shell/GuardiaSesion'
import PaginaAcceso from '@/paginas/acceso/PaginaAcceso'
import PaginaDocumentacion from '@/paginas/documentacion/PaginaDocumentacion'
import PaginaExplorador from '@/paginas/explorador/PaginaExplorador'
import PaginaNoEncontrado from '@/paginas/no-encontrado/PaginaNoEncontrado'
import PaginaOperaciones from '@/paginas/operaciones/PaginaOperaciones'
import PaginaPanel from '@/paginas/panel/PaginaPanel'
import PaginaPrivacidad from '@/paginas/privacidad/PaginaPrivacidad'
import PaginaTiempoReal from '@/paginas/tiempo-real/PaginaTiempoReal'

export const rutas: RouteObject[] = [
  { path: '/acceso', element: <PaginaAcceso /> },
  {
    element: <GuardiaSesion />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <PaginaPanel /> },
          { path: 'explorador', element: <PaginaExplorador /> },
          // El asistente dejó de ser una sección: la ruta antigua vuelve a la portada con el panel de TAXI AI abierto
          { path: 'asistente', element: <Navigate to="/" replace state={{ asistente: true }} /> },
          { path: 'tiempo-real', element: <PaginaTiempoReal /> },
          { path: 'privacidad', element: <PaginaPrivacidad /> },
          { path: 'operaciones', element: <PaginaOperaciones /> },
          { path: 'grafo', element: <PaginaDocumentacion /> },
          // La sección se llamaba «Documentación»: los enlaces antiguos siguen funcionando
          { path: 'documentacion', element: <Navigate to="/grafo" replace /> },
          { path: '*', element: <PaginaNoEncontrado /> },
        ],
      },
    ],
  },
]

/** El enrutador del navegador (producción y desarrollo). */
export function crearEnrutador() {
  return createBrowserRouter(rutas)
}

/** Un enrutador en memoria con las mismas rutas, para los tests (`initialEntries` marca dónde empieza). */
export function crearEnrutadorEnMemoria(initialEntries: string[] = ['/']) {
  return createMemoryRouter(rutas, { initialEntries })
}
