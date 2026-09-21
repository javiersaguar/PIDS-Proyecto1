/**
 * De las filas de una respuesta a los datos de los gráficos, según el nivel:
 *   - `hora_zona`: líneas por hora (una serie por zona si hay pocas; si no, el total de los grupos visibles);
 *   - `dia_barrio`: barras por barrio (un día) o líneas por día con una serie por barrio (varios días);
 *   - `od_dia_barrio`: matriz origen → destino.
 * Los grupos enmascarados nunca se suman: se cuentan y se marcan.
 */
import type { Fila, Metrica } from '@/api/tipos'
import { esEnmascarada, valorMetrica, viajesVisibles } from '@/componentes/datos/agregados'
import type { Barra, CeldaFlujo, PuntoLinea, Serie } from '@/componentes/graficos'

/** Con más zonas o barrios que esto, el gráfico de líneas pasa a mostrar el total de los grupos visibles. */
export const MAX_SERIES = 6

export const CLAVE_ENMASCARADOS = 'enmascarados'

interface Acumulador {
  suma: number
  peso: number
  visibles: number
  enmascarados: number
}

function nuevoAcumulador(): Acumulador {
  return { suma: 0, peso: 0, visibles: 0, enmascarados: 0 }
}

/** Acumula una fila: `n_viajes` se suma; las medias se ponderan por `n_viajes`. Los enmascarados solo se cuentan. */
function acumular(acumulador: Acumulador, fila: Fila, metrica: Metrica): void {
  if (esEnmascarada(fila)) {
    acumulador.enmascarados += 1
    return
  }
  const viajes = viajesVisibles(fila) ?? 0
  const valor = valorMetrica(fila, metrica)
  if (valor === null) return
  acumulador.visibles += 1
  if (metrica === 'n_viajes') {
    acumulador.suma += valor
    acumulador.peso += 1
  } else {
    acumulador.suma += valor * viajes
    acumulador.peso += viajes
  }
}

function valorDe(acumulador: Acumulador, metrica: Metrica): number | null {
  if (acumulador.visibles === 0) return null
  if (metrica === 'n_viajes') return acumulador.suma
  return acumulador.peso > 0 ? Math.round((acumulador.suma / acumulador.peso) * 100) / 100 : null
}

function ordenarIso(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0
}

export function diasDistintos(filas: readonly Fila[]): string[] {
  return [...new Set(filas.map((f) => f.dia).filter((d): d is string => !!d))].sort(ordenarIso)
}

export interface DatosLineas {
  puntos: PuntoLinea[]
  series: Serie[]
  /** `series`: una línea por zona o barrio; `total`: una sola línea con el agregado de los grupos visibles. */
  modo: 'series' | 'total'
  /** Zonas o barrios distintos en las filas (aunque se muestre el total). */
  categorias: number
}

function nombreZona(fila: Fila): string {
  return fila.zona_origen_nombre ?? (fila.zona_origen != null ? `Zona ${fila.zona_origen}` : 'Sin zona')
}

/**
 * Líneas sobre un eje temporal (`claveTiempo`: `hora` o `dia`), con una serie por categoría (zona o barrio) si
 * hay como mucho `MAX_SERIES`; si no, el total de los grupos visibles. Cada punto lleva `enmascarados`.
 */
function lineas(filas: readonly Fila[], metrica: Metrica, claveTiempo: 'hora' | 'dia', categoriaDe: (f: Fila) => string, prefijo: string): DatosLineas {
  const tiempos = [...new Set(filas.map((f) => f[claveTiempo]).filter((t): t is string => !!t))].sort(ordenarIso)
  const categorias = [...new Set(filas.map(categoriaDe))].sort((a, b) => a.localeCompare(b, 'es'))
  const modo: DatosLineas['modo'] = categorias.length <= MAX_SERIES ? 'series' : 'total'
  const claveDe = (categoria: string) => `${prefijo}${categorias.indexOf(categoria)}`

  const porTiempo = new Map<string, Map<string, Acumulador>>()
  for (const fila of filas) {
    const t = fila[claveTiempo]
    if (!t) continue
    const grupo = porTiempo.get(t) ?? new Map<string, Acumulador>()
    const clave = modo === 'series' ? claveDe(categoriaDe(fila)) : 'total'
    const acumulador = grupo.get(clave) ?? nuevoAcumulador()
    acumular(acumulador, fila, metrica)
    grupo.set(clave, acumulador)
    porTiempo.set(t, grupo)
  }

  const puntos: PuntoLinea[] = tiempos.map((t) => {
    const grupo = porTiempo.get(t) ?? new Map<string, Acumulador>()
    const punto: PuntoLinea = { [claveTiempo]: t }
    let enmascarados = 0
    for (const [clave, acumulador] of grupo) {
      punto[clave] = valorDe(acumulador, metrica)
      enmascarados += acumulador.enmascarados
    }
    punto[CLAVE_ENMASCARADOS] = enmascarados
    return punto
  })

  const series: Serie[] =
    modo === 'series'
      ? categorias.map((c) => ({ clave: claveDe(c), nombre: c }))
      : [{ clave: 'total', nombre: metrica === 'n_viajes' ? 'Total de grupos visibles' : 'Media ponderada de grupos visibles' }]

  return { puntos, series, modo, categorias: categorias.length }
}

export function lineasPorHora(filas: readonly Fila[], metrica: Metrica): DatosLineas {
  return lineas(filas, metrica, 'hora', nombreZona, 'z')
}

export function lineasPorDia(filas: readonly Fila[], metrica: Metrica): DatosLineas {
  return lineas(filas, metrica, 'dia', (f) => f.barrio_origen ?? 'Sin barrio', 'b')
}

/** Barras por barrio de origen (para un solo día): los enmascarados salen marcados, sin cifra. */
export function barrasPorBarrio(filas: readonly Fila[], metrica: Metrica): Barra[] {
  const porBarrio = new Map<string, Acumulador>()
  for (const fila of filas) {
    const barrio = fila.barrio_origen ?? 'Sin barrio'
    const acumulador = porBarrio.get(barrio) ?? nuevoAcumulador()
    acumular(acumulador, fila, metrica)
    porBarrio.set(barrio, acumulador)
  }
  return [...porBarrio.entries()]
    .map<Barra>(([barrio, acumulador]) => {
      const valor = valorDe(acumulador, metrica)
      return {
        etiqueta: barrio,
        valor,
        enmascarado: valor === null && acumulador.enmascarados > 0,
        detalle: acumulador.enmascarados > 0 && valor !== null ? `${acumulador.enmascarados} grupo(s) enmascarado(s) no incluidos` : undefined,
      }
    })
    .sort((a, b) => (b.valor ?? -1) - (a.valor ?? -1))
}

/** Celdas de la matriz origen → destino, agregando los días que haya. */
export function celdasFlujos(filas: readonly Fila[], metrica: Metrica): CeldaFlujo[] {
  const celdas = new Map<string, { origen: string; destino: string; acumulador: Acumulador }>()
  for (const fila of filas) {
    const origen = fila.barrio_origen ?? 'Sin origen'
    const destino = fila.barrio_destino ?? 'Sin destino'
    const clave = `${origen}→${destino}`
    const celda = celdas.get(clave) ?? { origen, destino, acumulador: nuevoAcumulador() }
    acumular(celda.acumulador, fila, metrica)
    celdas.set(clave, celda)
  }
  return [...celdas.values()].map(({ origen, destino, acumulador }) => ({
    origen,
    destino,
    valor: valorDe(acumulador, metrica),
    enmascarados: acumulador.enmascarados,
    visibles: acumulador.visibles,
  }))
}
