/**
 * Las seis secciones del portal (§6): ruta, título, descripción e icono. Es la única lista; la usan la barra
 * lateral y la cabecera (título de la sección activa). El asistente (TAXI AI) no es una sección: es el botón fijo
 * de la esquina inferior derecha y su panel, disponibles en todas las páginas (`PanelAsistente.tsx`).
 */
import {
  Activity,
  LayoutDashboard,
  Network,
  ShieldCheck,
  SlidersHorizontal,
  Table2,
  type LucideIcon,
} from 'lucide-react'

export interface Seccion {
  ruta: string
  titulo: string
  descripcion: string
  icono: LucideIcon
}

export const SECCIONES: readonly Seccion[] = [
  {
    ruta: '/',
    titulo: 'Panel',
    descripcion: 'Último día publicado, frescura del tiempo real, decisiones de las últimas 24 h y estado de los servicios.',
    icono: LayoutDashboard,
  },
  {
    ruta: '/explorador',
    titulo: 'Explorador',
    descripcion: 'Consultas agregadas por hora y zona, por día y barrio o flujos entre barrios, siempre con k = 10.',
    icono: Table2,
  },
  {
    ruta: '/tiempo-real',
    titulo: 'Tiempo real',
    descripcion: 'Viajes de las últimas horas y frescura del flujo de captura.',
    icono: Activity,
  },
  {
    ruta: '/privacidad',
    titulo: 'Privacidad',
    descripcion: 'Reglas del escenario E3, auditoría de decisiones y cargas históricas.',
    icono: ShieldCheck,
  },
  {
    ruta: '/operaciones',
    titulo: 'Operaciones',
    descripcion: 'Cargas históricas en Airflow y simulador de viajes en tiempo real.',
    icono: SlidersHorizontal,
  },
  {
    ruta: '/grafo',
    titulo: 'Grafo',
    descripcion: 'Por dónde pasan los datos: qué hace cada pieza, qué está en marcha ahora y la captura en directo.',
    icono: Network,
  },
]

/** La sección a la que pertenece una ruta (`/explorador/…` → Explorador); `undefined` si no es ninguna. */
export function seccionDe(pathname: string): Seccion | undefined {
  if (pathname === '/') return SECCIONES[0]
  return SECCIONES.find((s) => s.ruta !== '/' && (pathname === s.ruta || pathname.startsWith(`${s.ruta}/`)))
}
