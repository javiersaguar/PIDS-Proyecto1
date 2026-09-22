/**
 * Unidades y colores de los paneles, con los mismos nombres que usa Grafana (`short`, `bytes`, `s`, `reqps`…).
 * Lógica pura: se prueba sin navegador.
 */
import type { PanelCuadro } from '@/api/observabilidad'

const NUMERO = new Intl.NumberFormat('es-ES')

function numero(valor: number, decimales: number): string {
  return new Intl.NumberFormat('es-ES', { maximumFractionDigits: decimales }).format(valor)
}

/** 1234 → «1234»; 12 345 → «12,3 mil»; 0,0342 → «0,034». */
export function corto(valor: number): string {
  const absoluto = Math.abs(valor)
  if (absoluto >= 1e9) return `${numero(valor / 1e9, 1)} mil M`
  if (absoluto >= 1e6) return `${numero(valor / 1e6, 1)} M`
  if (absoluto >= 1e4) return `${numero(valor / 1e3, 1)} mil`
  if (absoluto >= 100) return NUMERO.format(Math.round(valor))
  if (absoluto >= 1) return numero(valor, 1)
  if (absoluto === 0) return '0'
  return numero(valor, 3)
}

function bytes(valor: number, base = 1024): string {
  const unidades = base === 1024 ? ['B', 'KiB', 'MiB', 'GiB', 'TiB'] : ['B', 'kB', 'MB', 'GB', 'TB']
  let indice = 0
  let resto = Math.abs(valor)
  while (resto >= base && indice < unidades.length - 1) {
    resto /= base
    indice += 1
  }
  return `${numero(Math.sign(valor) * resto, resto >= 100 || indice === 0 ? 0 : 1)} ${unidades[indice]}`
}

function duracion(segundos: number): string {
  if (segundos < 60) return `${numero(segundos, segundos < 10 ? 1 : 0)} s`
  if (segundos < 3600) return `${Math.floor(segundos / 60)} min ${Math.round(segundos % 60)} s`
  if (segundos < 86_400) return `${Math.floor(segundos / 3600)} h ${Math.round((segundos % 3600) / 60)} min`
  return `${numero(segundos / 86_400, 1)} d`
}

/** Una duración con solo su unidad mayor, para los ejes: «33 min», «2,2 h». */
function duracionCorta(segundos: number): string {
  if (Math.abs(segundos) < 60) return `${numero(segundos, 0)} s`
  if (Math.abs(segundos) < 3600) return `${numero(segundos / 60, 0)} min`
  if (Math.abs(segundos) < 86_400) return `${numero(segundos / 3600, 1)} h`
  return `${numero(segundos / 86_400, 1)} d`
}

/** El valor con su unidad, como lo enseñaría Grafana pero en español. `eje`: la versión corta, para los ejes. */
export function formatear(valor: number | null | undefined, unidad: string, eje = false): string {
  if (valor == null || !Number.isFinite(valor)) return '—'
  if (eje && unidad === 's') return duracionCorta(valor)
  switch (unidad) {
    case 'bytes':
      return bytes(valor)
    case 'decmbytes':
      return bytes(valor * 1e6, 1000)
    case 'Bps':
      return `${bytes(valor)}/s`
    case 's':
      return duracion(valor)
    case 'reqps':
      return `${corto(valor)}/s`
    case 'dateTimeAsIso': {
      const fecha = new Date(valor)
      return Number.isNaN(fecha.getTime()) || valor <= 0 ? '—' : fecha.toLocaleDateString('es-ES', { timeZone: 'UTC' })
    }
    default:
      return corto(valor)
  }
}

/** Los colores con nombre de Grafana, en la paleta del portal. */
const COLORES: Record<string, string> = {
  green: '#17875a',
  'semi-dark-green': '#17875a',
  orange: '#d97706',
  red: '#dc2626',
  yellow: '#ca8a04',
  blue: '#2f62c4',
  purple: '#6d4eae',
}

export function color(nombre: string | null | undefined): string | undefined {
  if (!nombre) return undefined
  return COLORES[nombre] ?? nombre
}

/** Color de un valor según los umbrales del panel (el último paso cuyo `desde` no supera el valor). */
export function colorPorUmbral(panel: Pick<PanelCuadro, 'umbrales' | 'color'>, valor: number | null | undefined): string | undefined {
  if (valor != null && panel.umbrales.length > 1) {
    let elegido: string | undefined
    for (const paso of panel.umbrales) {
      if (paso.desde == null || valor >= paso.desde) elegido = paso.color
    }
    return color(elegido)
  }
  return color(panel.color)
}

/** Series de un panel en filas para Recharts: `[{t, «serie A»: 3, «serie B»: 1}, …]`. */
export function aFilas(series: readonly { nombre: string; puntos: readonly (readonly [number, number | null])[] }[]) {
  const filas = new Map<number, Record<string, number | null>>()
  for (const serie of series) {
    for (const [t, v] of serie.puntos) {
      const fila = filas.get(t) ?? { t }
      fila[serie.nombre] = v
      filas.set(t, fila)
    }
  }
  return [...filas.values()].sort((a, b) => (a.t as number) - (b.t as number))
}

const UNIDADES_PERIODO: Record<string, string> = { s: 's', m: 'min', h: 'h', d: 'd' }

/** `6h` → «últimas 6 h». */
export function describirPeriodo(periodo: string): string {
  const partes = /^(\d+)([smhd])$/.exec(periodo)
  return partes ? `últimas ${partes[1]} ${UNIDADES_PERIODO[partes[2]]}` : periodo
}

/** Alto en píxeles de `alto` filas de la rejilla de Grafana: 28 px por fila y 12 px de hueco entre filas. */
export const altoPanel = (alto: number) => alto * 40 - 12

/** Alto útil de la gráfica de un panel: sin el relleno de la tarjeta, la cabecera y, si la hay, la leyenda. */
export function altoGrafica(alto: number, conLeyenda: boolean): number {
  return Math.max(120, altoPanel(alto) - 32 - 30 - (conLeyenda ? 22 : 0))
}
