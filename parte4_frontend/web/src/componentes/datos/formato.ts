/**
 * Formato español de cifras y fechas (CONTRATOS.md §7): `1.234.567`, `2,07 $`, `35,4 %`, `dd/mm/yyyy`, `HH:mm`.
 *
 * Se implementa a mano (sin `Intl`) para que el resultado sea el mismo en el navegador, en Node y en jsdom, y
 * para agrupar siempre los millares (Intl en `es-ES` no separa los números de cuatro cifras). Las fechas de la
 * API vienen en ISO sin zona (`2020-01-15T08:00:00`) y se interpretan tal cual, sin desplazarlas.
 */
import { format, isValid, parseISO } from 'date-fns'

/** Lo que se pinta cuando no hay valor (nulo, indefinido, NaN). */
export const SIN_DATO = '—'

type Numero = number | null | undefined

function agruparMillares(entero: string): string {
  return entero.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

function esNumero(valor: unknown): valor is number {
  return typeof valor === 'number' && Number.isFinite(valor)
}

/** `1234567` → `1.234.567`. Las cadenas (por ejemplo `"<10"`) se devuelven tal cual. */
export function formatearEntero(valor: Numero | string): string {
  if (typeof valor === 'string') return valor
  if (!esNumero(valor)) return SIN_DATO
  const redondeado = Math.round(valor)
  const signo = redondeado < 0 ? '-' : ''
  return signo + agruparMillares(String(Math.abs(redondeado)))
}

/** `2.07` → `2,07`; `1234.5` → `1.234,50`. */
export function formatearDecimal(valor: Numero, decimales = 2): string {
  if (!esNumero(valor)) return SIN_DATO
  const [entera, decimal] = Math.abs(valor).toFixed(decimales).split('.')
  const signo = valor < 0 && Number(Math.abs(valor).toFixed(decimales)) !== 0 ? '-' : ''
  return signo + agruparMillares(entera) + (decimal ? `,${decimal}` : '')
}

/** `2.07` → `2,07 $` (los importes de los datos están en dólares). */
export function formatearImporte(valor: Numero, decimales = 2): string {
  if (!esNumero(valor)) return SIN_DATO
  return `${formatearDecimal(valor, decimales)} $`
}

/** `35.4` → `35,4 %` (el valor ya viene en tanto por ciento, 0-100). */
export function formatearPorcentaje(valor: Numero, decimales = 1): string {
  if (!esNumero(valor)) return SIN_DATO
  return `${formatearDecimal(valor, decimales)} %`
}

/** `1.5` millas → `1,50 mi`. */
export function formatearDistancia(valor: Numero, decimales = 2): string {
  if (!esNumero(valor)) return SIN_DATO
  return `${formatearDecimal(valor, decimales)} mi`
}

/** El número de viajes de una fila: los grupos enmascarados llegan como `"<10"` y se muestran así. */
export function formatearViajes(valor: number | string | null | undefined): string {
  return formatearEntero(valor)
}

/** Interpreta una fecha ISO sin zona como hora local; `null` si no es válida. */
export function parsearFecha(valor: string | Date | null | undefined): Date | null {
  if (valor == null || valor === '') return null
  const fecha = valor instanceof Date ? valor : parseISO(valor)
  return isValid(fecha) ? fecha : null
}

function formatearCon(patron: string, valor: string | Date | null | undefined): string {
  const fecha = parsearFecha(valor)
  return fecha ? format(fecha, patron) : SIN_DATO
}

/** `2020-01-15T08:00:00` → `15/01/2020`. */
export function formatearFecha(valor: string | Date | null | undefined): string {
  return formatearCon('dd/MM/yyyy', valor)
}

/** `2020-01-15T08:00:00` → `15/01` (ejes de los gráficos). */
export function formatearFechaCorta(valor: string | Date | null | undefined): string {
  return formatearCon('dd/MM', valor)
}

/** `2020-01-15T08:00:00` → `08:00`. */
export function formatearHora(valor: string | Date | null | undefined): string {
  return formatearCon('HH:mm', valor)
}

/** `2020-01-15T08:00:00` → `15/01/2020 08:00`. */
export function formatearFechaHora(valor: string | Date | null | undefined): string {
  return formatearCon('dd/MM/yyyy HH:mm', valor)
}

/** Fecha en ISO sin zona, como la espera la API: `2020-01-15T08:00:00`. */
export function aIsoLocal(fecha: Date): string {
  return format(fecha, "yyyy-MM-dd'T'HH:mm:ss")
}

/** Solo la parte de fecha en ISO (`2020-01-15`), para los `<input type="date">`. */
export function aIsoFecha(fecha: Date): string {
  return format(fecha, 'yyyy-MM-dd')
}

/**
 * Antigüedad legible a partir de segundos: `hace 12 s`, `hace 3 min 20 s`, `hace 2 h 5 min`, `hace 3 d`.
 * Con `null` (sin dato) devuelve `sin dato`.
 */
export function describirAntiguedad(segundos: number | null | undefined): string {
  if (!esNumero(segundos)) return 'sin dato'
  const s = Math.max(0, Math.floor(segundos))
  if (s < 60) return `hace ${s} s`
  const min = Math.floor(s / 60)
  if (min < 60) {
    const resto = s % 60
    return resto ? `hace ${min} min ${resto} s` : `hace ${min} min`
  }
  const horas = Math.floor(min / 60)
  if (horas < 24) {
    const resto = min % 60
    return resto ? `hace ${horas} h ${resto} min` : `hace ${horas} h`
  }
  const dias = Math.floor(horas / 24)
  return `hace ${dias} d`
}

/** Plural sencillo: `pluralizar(1, 'fila')` → `1 fila`; `pluralizar(3, 'fila')` → `3 filas`. */
export function pluralizar(cantidad: number, singular: string, plural = `${singular}s`): string {
  return `${formatearEntero(cantidad)} ${cantidad === 1 ? singular : plural}`
}
