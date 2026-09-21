/**
 * Rutas del portal (§6). `/acceso` va suelta; el resto cuelga de la guardia de sesión y del shell.
 * Las páginas se importan directamente (sin `lazy`): F3 y F4 sobrescriben los ficheros, no las rutas.
 */
import { createBrowserRouter, createMemoryRouter, type RouteObject } from 'react-router'

import { AppShell } from '@/componentes/shell/AppShell'
import { GuardiaSesion } from '@/componentes/shell/GuardiaSesion'
import PaginaAcceso from '@/paginas/acceso/PaginaAcceso'
import PaginaAsistente from '@/paginas/asistente/PaginaAsistente'
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
          { path: 'asistente', element: <PaginaAsistente /> },
          { path: 'tiempo-real', element: <PaginaTiempoReal /> },
          { path: 'privacidad', element: <PaginaPrivacidad /> },
          { path: 'operaciones', element: <PaginaOperaciones /> },
          { path: 'documentacion', element: <PaginaDocumentacion /> },
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
