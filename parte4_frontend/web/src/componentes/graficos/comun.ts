/**
 * Colores y ayudas comunes de los gráficos (§7): la serie principal en el amarillo taxi (`--chart-1`),
 * las secundarias en azules y los grupos enmascarados en violeta (`--enmascarado`).
 */
export const COLOR_PRINCIPAL = 'var(--chart-1)'
export const COLOR_ENMASCARADO = 'var(--enmascarado)'
export const COLOR_ENMASCARADO_SUAVE = 'var(--enmascarado-suave)'
export const COLOR_TEXTO_SUAVE = 'var(--texto-suave)'
export const COLOR_BORDE = 'var(--borde)'
export const COLOR_CURSOR = 'var(--superficie-alterna)'

/** Paleta para varias series: acento, azules del tema y unos cuantos tonos más para llegar a los 8 barrios. */
export const COLORES_SERIES = [
  'var(--chart-1)',
  'var(--chart-2)',
  'var(--chart-3)',
  'var(--chart-4)',
  '#0e7490',
  '#7c2d12',
  '#4b5563',
  '#a16207',
] as const

export function colorSerie(indice: number): string {
  return COLORES_SERIES[indice % COLORES_SERIES.length]
}

/** Identificador del patrón SVG con el que se rellenan las barras de grupos enmascarados. */
export const ID_TRAMA_ENMASCARADO = 'trama-enmascarado'

/** Estilo de los ejes: texto pequeño y suave, sin líneas de eje. */
export const ESTILO_TICK = { fontSize: 11, fill: 'var(--texto-suave)' } as const

/** Ancho del eje de categorías según la etiqueta más larga (acotado). */
export function anchoEjeCategorias(etiquetas: readonly string[], minimo = 60, maximo = 170): number {
  const masLarga = etiquetas.reduce((max, e) => Math.max(max, e.length), 0)
  return Math.max(minimo, Math.min(maximo, 12 + masLarga * 6.5))
}
