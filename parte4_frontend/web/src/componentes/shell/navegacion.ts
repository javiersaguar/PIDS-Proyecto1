/**
 * Las secciones del portal (§6): ruta, título, descripción e icono. Es la única lista; la usan la barra
 * lateral y la cabecera (título de la sección activa). El asistente (TAXI AI) no es una sección: es el botón fijo
 * de la esquina inferior derecha y su panel, disponibles en todas las páginas (`PanelAsistente.tsx`).
 */
import {
  Activity,
  LayoutDashboard,
  LineChart,
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
  {
    ruta: '/observabilidad',
    titulo: 'Observabilidad',
    descripcion: 'Cuadros de Grafana: Spark, Kafka, MongoDB, S3, privacidad, chatbots y tiempo real.',
    icono: LineChart,
  },
]

/** La sección a la que pertenece una ruta (`/explorador/…` → Explorador); `undefined` si no es ninguna. */
export function seccionDe(pathname: string): Seccion | undefined {
  if (pathname === '/') return SECCIONES[0]
  return SECCIONES.find((s) => s.ruta !== '/' && (pathname === s.ruta || pathname.startsWith(`${s.ruta}/`)))
}

/** La sección que sigue a la de `ruta` en el menú, dando la vuelta al llegar a la última (✋ en los gestos); desde una
 * ruta que no es de ninguna sección, la primera. */
export function seccionSiguiente(ruta: string): string {
  const actual = seccionDe(ruta)
  const indice = actual ? SECCIONES.indexOf(actual) : -1
  return SECCIONES[(indice + 1) % SECCIONES.length].ruta
}
