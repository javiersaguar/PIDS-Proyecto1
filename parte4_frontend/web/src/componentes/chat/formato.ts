/**
 * Helpers mínimos de formato en español para las páginas de F4 (asistente, privacidad, operaciones):
 * cifras `1.234.567`, decimales con coma, fechas `dd/mm/yyyy` y horas `HH:mm` (§7 de CONTRATOS.md).
 */
import { format, isValid, parseISO } from 'date-fns'

const ENTEROS = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 0 })

/** `1234567` → `1.234.567`. Acepta también cadenas ya formateadas (por ejemplo `"<10"`), que devuelve tal cual. */
export function formatearNumero(valor: number | string | null | undefined): string {
  if (valor === null || valor === undefined) return '—'
  if (typeof valor === 'string') return valor
  if (!Number.isFinite(valor)) return '—'
  return ENTEROS.format(valor)
}

/** Decimales con coma: `formatearDecimal(2.0712, 2)` → `2,07`. */
export function formatearDecimal(valor: number | null | undefined, decimales = 2): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) return '—'
  return new Intl.NumberFormat('es-ES', { minimumFractionDigits: decimales, maximumFractionDigits: decimales }).format(valor)
}

/** Duración en segundos: `0.004` → `< 0,01 s`, `2.61` → `2,6 s`, `75` → `1 min 15 s`. */
export function formatearSegundos(segundos: number | null | undefined): string {
  if (segundos === null || segundos === undefined || !Number.isFinite(segundos)) return '—'
  if (segundos < 0.01) return '< 0,01 s'
  if (segundos < 10) return `${formatearDecimal(segundos, segundos < 1 ? 2 : 1)} s`
  if (segundos < 60) return `${Math.round(segundos)} s`
  const minutos = Math.floor(segundos / 60)
  const resto = Math.round(segundos % 60)
  return resto ? `${minutos} min ${resto} s` : `${minutos} min`
}

/** Porcentaje con una cifra decimal: `35.42` → `35,4 %`. */
export function formatearPorcentaje(valor: number | null | undefined): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) return '—'
  return `${formatearDecimal(valor, 1)} %`
}

function aFecha(valor: string | Date | null | undefined): Date | null {
  if (!valor) return null
  const fecha = typeof valor === 'string' ? parseISO(valor) : valor
  return isValid(fecha) ? fecha : null
}

/** ISO → `dd/mm/yyyy HH:mm` en la hora local del navegador; `—` si no es una fecha. */
export function formatearFechaHora(valor: string | Date | null | undefined): string {
  const fecha = aFecha(valor)
  return fecha ? format(fecha, 'dd/MM/yyyy HH:mm') : '—'
}

/** ISO → `dd/mm/yyyy`. */
export function formatearFecha(valor: string | Date | null | undefined): string {
  const fecha = aFecha(valor)
  return fecha ? format(fecha, 'dd/MM/yyyy') : '—'
}

/** ISO → `HH:mm:ss`, para instantes cercanos (auditoría de las últimas horas). */
export function formatearHora(valor: string | Date | null | undefined): string {
  const fecha = aFecha(valor)
  return fecha ? format(fecha, 'HH:mm:ss') : '—'
}

/** Recorta un texto largo dejando una elipsis. */
export function abreviar(texto: string, maximo = 80): string {
  if (texto.length <= maximo) return texto
  return `${texto.slice(0, Math.max(0, maximo - 1)).trimEnd()}…`
}

/** JSON en una línea, sin las llaves exteriores: `nivel: "hora_zona", desde: "2020-01-15T08:00:00"`. */
export function argumentosEnLinea(argumentos: Record<string, unknown> | null | undefined): string {
  if (!argumentos) return ''
  return Object.entries(argumentos)
    .filter(([, v]) => v !== undefined && v !== null)
    .map(([clave, valor]) => `${clave}: ${typeof valor === 'string' ? valor : JSON.stringify(valor)}`)
    .join(' · ')
}

/** JSON con sangría para los desplegables de detalle (consulta, alternativa, resultado de una herramienta). */
export function jsonLegible(valor: unknown): string {
  if (valor === null || valor === undefined) return '—'
  if (typeof valor === 'string') {
    try {
      return JSON.stringify(JSON.parse(valor), null, 2)
    } catch {
      return valor
    }
  }
  return JSON.stringify(valor, null, 2)
}
