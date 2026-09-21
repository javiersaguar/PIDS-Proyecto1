/**
 * Lógica pura sobre las filas de agregados (`Fila` del §5): etiquetas de niveles y métricas, columnas de la
 * tabla por nivel, orden y formato de las celdas, y totales que **nunca** suman los grupos enmascarados.
 */
import type { Fila, Fuente, Metrica, Nivel } from '@/api/tipos'

import {
  formatearDecimal,
  formatearDistancia,
  formatearFecha,
  formatearFechaHora,
  formatearImporte,
  formatearPorcentaje,
  formatearViajes,
  SIN_DATO,
} from './formato'

export const METRICAS: readonly Metrica[] = ['n_viajes', 'distancia_media', 'importe_medio', 'propina_media', 'pct_pago_tarjeta']

export const ETIQUETAS_METRICA: Record<Metrica, string> = {
  n_viajes: 'Viajes',
  distancia_media: 'Distancia media',
  importe_medio: 'Importe medio',
  propina_media: 'Propina media',
  pct_pago_tarjeta: 'Pago con tarjeta',
}

export const DESCRIPCIONES_METRICA: Record<Metrica, string> = {
  n_viajes: 'Número de viajes del grupo (siempre se incluye).',
  distancia_media: 'Distancia media del viaje, en millas.',
  importe_medio: 'Importe medio pagado, en dólares.',
  propina_media: 'Propina media, en dólares.',
  pct_pago_tarjeta: 'Porcentaje de viajes pagados con tarjeta.',
}

export const ETIQUETAS_NIVEL: Record<Nivel, string> = {
  hora_zona: 'Por hora y zona de origen',
  dia_barrio: 'Por día y barrio de origen',
  od_dia_barrio: 'Flujos entre barrios por día',
}

export const ETIQUETAS_FUENTE: Record<Fuente, string> = {
  historico: 'Histórico',
  tiempo_real: 'Tiempo real',
}

/** Resultado de una decisión de la API de acceso (`Respuesta.resultado` o `Decision.resultado`). */
export type Resultado = 'permitida' | 'enmascarada' | 'rechazada'

export const TEXTO_RESULTADO: Record<Resultado, string> = {
  permitida: 'permitida',
  enmascarada: 'enmascarada',
  rechazada: 'rechazada',
}

export const NIVELES: readonly Nivel[] = ['hora_zona', 'dia_barrio', 'od_dia_barrio']
export const FUENTES: readonly Fuente[] = ['historico', 'tiempo_real']

export function esNivel(valor: unknown): valor is Nivel {
  return typeof valor === 'string' && (NIVELES as readonly string[]).includes(valor)
}
export function esFuente(valor: unknown): valor is Fuente {
  return typeof valor === 'string' && (FUENTES as readonly string[]).includes(valor)
}
export function esMetrica(valor: unknown): valor is Metrica {
  return typeof valor === 'string' && (METRICAS as readonly string[]).includes(valor)
}

/** Un grupo enmascarado llega con `suprimido: true` y `n_viajes: "<10"`, sin cifras. */
export function esEnmascarada(fila: Fila): boolean {
  return fila.suprimido === true || typeof fila.n_viajes === 'string'
}

/** El número de viajes de un grupo visible; `null` si está enmascarado. */
export function viajesVisibles(fila: Fila): number | null {
  if (esEnmascarada(fila) || typeof fila.n_viajes !== 'number') return null
  return fila.n_viajes
}

/** El valor de una métrica en un grupo visible; `null` si está enmascarado o no viene. */
export function valorMetrica(fila: Fila, metrica: Metrica): number | null {
  if (esEnmascarada(fila)) return null
  if (metrica === 'n_viajes') return viajesVisibles(fila)
  const valor = fila[metrica]
  return typeof valor === 'number' && Number.isFinite(valor) ? valor : null
}

export interface Totales {
  /** Suma de `n_viajes` de los grupos visibles. Los enmascarados no se suman (ataque por diferencia). */
  total: number
  visibles: number
  enmascarados: number
}

export function totalesDe(filas: readonly Fila[]): Totales {
  let total = 0
  let visibles = 0
  let enmascarados = 0
  for (const fila of filas) {
    const viajes = viajesVisibles(fila)
    if (viajes === null) enmascarados += 1
    else {
      visibles += 1
      total += viajes
    }
  }
  return { total, visibles, enmascarados }
}

export function formatearMetrica(metrica: Metrica, valor: number | string | null | undefined): string {
  if (valor == null) return SIN_DATO
  switch (metrica) {
    case 'n_viajes':
      return formatearViajes(valor)
    case 'distancia_media':
      return typeof valor === 'number' ? formatearDistancia(valor) : String(valor)
    case 'importe_medio':
    case 'propina_media':
      return typeof valor === 'number' ? formatearImporte(valor) : String(valor)
    case 'pct_pago_tarjeta':
      return typeof valor === 'number' ? formatearPorcentaje(valor) : String(valor)
    default:
      return typeof valor === 'number' ? formatearDecimal(valor) : String(valor)
  }
}

/** Columnas de la tabla de agregados. */
export type ClaveColumna = 'hora' | 'dia' | 'zona_origen' | 'barrio_origen' | 'barrio_destino' | Metrica

export interface Columna {
  clave: ClaveColumna
  titulo: string
  /** Las cifras van alineadas a la derecha. */
  numerica: boolean
}

const DIMENSIONES: Record<Nivel, Columna[]> = {
  hora_zona: [
    { clave: 'hora', titulo: 'Hora', numerica: false },
    { clave: 'zona_origen', titulo: 'Zona de origen', numerica: false },
    { clave: 'barrio_origen', titulo: 'Barrio', numerica: false },
  ],
  dia_barrio: [
    { clave: 'dia', titulo: 'Día', numerica: false },
    { clave: 'barrio_origen', titulo: 'Barrio de origen', numerica: false },
  ],
  od_dia_barrio: [
    { clave: 'dia', titulo: 'Día', numerica: false },
    { clave: 'barrio_origen', titulo: 'Origen', numerica: false },
    { clave: 'barrio_destino', titulo: 'Destino', numerica: false },
  ],
}

/** Dimensiones del nivel seguidas de `n_viajes` y del resto de métricas pedidas, en el orden del catálogo. */
export function columnasDe(nivel: Nivel, metricas: readonly Metrica[] = ['n_viajes']): Columna[] {
  const pedidas = new Set<Metrica>(['n_viajes', ...metricas])
  const columnasMetricas = METRICAS.filter((m) => pedidas.has(m)).map<Columna>((m) => ({
    clave: m,
    titulo: ETIQUETAS_METRICA[m],
    numerica: true,
  }))
  return [...DIMENSIONES[nivel], ...columnasMetricas]
}

/** Texto de una celda, ya formateado en español. */
export function textoCelda(fila: Fila, clave: ClaveColumna): string {
  switch (clave) {
    case 'hora':
      return formatearFechaHora(fila.hora)
    case 'dia':
      return formatearFecha(fila.dia)
    case 'zona_origen':
      return fila.zona_origen_nombre ?? (fila.zona_origen != null ? `Zona ${fila.zona_origen}` : SIN_DATO)
    case 'barrio_origen':
      return fila.barrio_origen ?? SIN_DATO
    case 'barrio_destino':
      return fila.barrio_destino ?? SIN_DATO
    default:
      return esEnmascarada(fila) && clave !== 'n_viajes' ? SIN_DATO : formatearMetrica(clave, fila[clave])
  }
}

/** Valor con el que se ordena una columna: cadenas para las dimensiones, números para las métricas. */
export function valorOrden(fila: Fila, clave: ClaveColumna): string | number | null {
  switch (clave) {
    case 'hora':
      return fila.hora ?? null
    case 'dia':
      return fila.dia ?? null
    case 'zona_origen':
      return fila.zona_origen_nombre ?? fila.zona_origen ?? null
    case 'barrio_origen':
      return fila.barrio_origen ?? null
    case 'barrio_destino':
      return fila.barrio_destino ?? null
    case 'n_viajes':
      // Un grupo enmascarado tiene menos de k viajes: se ordena por debajo de cualquier grupo visible.
      return viajesVisibles(fila) ?? -1
    default:
      return valorMetrica(fila, clave)
  }
}

export type Direccion = 'asc' | 'desc'

/** Comparador estable para `Array.prototype.sort`; los valores nulos van siempre al final. */
export function compararPor(clave: ClaveColumna, direccion: Direccion): (a: Fila, b: Fila) => number {
  const signo = direccion === 'asc' ? 1 : -1
  return (a, b) => {
    const va = valorOrden(a, clave)
    const vb = valorOrden(b, clave)
    if (va === null && vb === null) return 0
    if (va === null) return 1
    if (vb === null) return -1
    if (typeof va === 'number' && typeof vb === 'number') return signo * (va - vb)
    return signo * String(va).localeCompare(String(vb), 'es', { numeric: true, sensitivity: 'base' })
  }
}
