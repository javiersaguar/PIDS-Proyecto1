/**
 * Qué está haciendo la plataforma ahora mismo, con lo que el BFF ya sabe (CONTRATOS.md §5): las ejecuciones de
 * Airflow, el simulador y la frescura del tiempo real. No abre ningún canal nuevo: reutiliza las consultas de
 * Operaciones y del panel, que TanStack Query comparte entre las páginas que las usan.
 *
 *   const actividad = useActividad()
 *   actividad.enMarcha       // hay una carga, una simulación o Spark ha publicado hace poco
 *   actividad.carga          // la ejecución de Airflow en curso (running o en cola), si la hay
 *   actividad.simulacion     // la simulación activa, si la hay
 *   actividad.publicando     // Spark ha escrito agregados de tiempo real hace menos de UMBRAL_PUBLICANDO_S
 *   actividad.consultando    // el portal está pidiendo datos a la API de acceso en este momento
 *
 * `derivarActividad` y `describirActividad` son lógica pura (se prueban sin React). Si Airflow o el simulador no
 * responden, esa parte cuenta como «sin actividad»: la página no se entera.
 */
import { useIsFetching } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { useSegundosDesde } from '@/componentes/datos/useAhora'
import { describirAntiguedad, formatearEntero } from '@/componentes/datos/formato'

import { useEjecucionesAirflow, useSimulacion } from './operaciones'
import { usePanel } from './panel'
import type { EjecucionAirflow, Simulacion } from './tipos'

/** Spark escribe los agregados de tiempo real cada 30 s; si el último lleva menos de esto, sigue publicando. */
export const UMBRAL_PUBLICANDO_S = 120
/** Cuánto se mantiene encendido «consultando» tras acabar la petición, para que se llegue a ver. */
export const SOSTENER_CONSULTANDO_MS = 1500
/** Consultas que van a la API de acceso a por agregados (las que animan el tramo MongoDB → acceso → portal). */
const CLAVES_CONSULTA = new Set(['panel', 'tiempo-real', 'consultas'])
const NOMBRE_MES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

export interface CargaEnMarcha {
  id: string
  estado: 'running' | 'queued'
  mes: string | null
  muestra: boolean
  inicio: string | null
  /** Segundos desde que arrancó, si Airflow ha dado la hora de inicio. */
  segundos: number | null
}

export interface UltimaCarga {
  estado: string
  mes: string | null
  muestra: boolean
  fin: string | null
  segundos: number | null
}

export interface Actividad {
  carga: CargaEnMarcha | null
  ultimaCarga: UltimaCarga | null
  /** La simulación, solo mientras está activa. */
  simulacion: Simulacion | null
  /** Antigüedad del último agregado de tiempo real, avanzando en cliente; `null` sin dato. */
  frescuraSegundos: number | null
  publicando: boolean
  consultando: boolean
  /** Carga, simulación o publicación: algo se mueve. */
  enMarcha: boolean
}

export const SIN_ACTIVIDAD: Actividad = {
  carga: null, ultimaCarga: null, simulacion: null, frescuraSegundos: null, publicando: false, consultando: false,
  enMarcha: false,
}

export interface Entradas {
  ejecuciones?: readonly EjecucionAirflow[] | null
  simulacion?: Simulacion | null
  frescuraSegundos?: number | null
  consultando?: boolean
  /** Instante actual en ms (para las antigüedades); por defecto `Date.now()`. */
  ahoraMs?: number
}

function segundosDesde(instante: string | null | undefined, ahoraMs: number): number | null {
  if (!instante) return null
  const ms = Date.parse(instante)
  return Number.isFinite(ms) ? Math.max(0, (ahoraMs - ms) / 1000) : null
}

function conf(ejecucion: EjecucionAirflow): { mes: string | null; muestra: boolean } {
  const mes = typeof ejecucion.conf?.mes === 'string' ? ejecucion.conf.mes : null
  return { mes, muestra: ejecucion.conf?.muestra === true }
}

export function estadoEnMarcha(estado: string): CargaEnMarcha['estado'] | null {
  if (estado === 'running') return 'running'
  if (estado === 'queued' || estado === 'scheduled') return 'queued'
  return null
}

export function derivarActividad(entradas: Entradas): Actividad {
  const ahoraMs = entradas.ahoraMs ?? Date.now()
  const ejecuciones = entradas.ejecuciones ?? []

  // La más reciente en marcha (la lista llega de la más nueva a la más antigua); running manda sobre queued.
  let carga: CargaEnMarcha | null = null
  for (const ejecucion of ejecuciones) {
    const estado = estadoEnMarcha(ejecucion.estado)
    if (!estado) continue
    if (!carga || (carga.estado === 'queued' && estado === 'running')) {
      carga = { id: ejecucion.dag_run_id, estado, ...conf(ejecucion), inicio: ejecucion.inicio,
                segundos: segundosDesde(ejecucion.inicio, ahoraMs) }
    }
  }

  const terminada = ejecuciones.find((e) => !estadoEnMarcha(e.estado) && e.fin)
  const ultimaCarga: UltimaCarga | null = terminada
    ? { estado: terminada.estado, ...conf(terminada), fin: terminada.fin, segundos: segundosDesde(terminada.fin, ahoraMs) }
    : null

  const simulacion = entradas.simulacion?.activa ? entradas.simulacion : null
  const frescuraSegundos = entradas.frescuraSegundos ?? null
  const publicando = frescuraSegundos != null && frescuraSegundos <= UMBRAL_PUBLICANDO_S
  return {
    carga, ultimaCarga, simulacion, frescuraSegundos, publicando,
    consultando: entradas.consultando ?? false,
    enMarcha: carga !== null || simulacion !== null || publicando,
  }
}

// --- textos --------------------------------------------------------------------------------------------------

/** `2020-03` → `marzo de 2020`; con `muestra`, «la muestra de prueba». */
export function describirCarga(mes: string | null, muestra: boolean): string {
  const nombre = mes && /^2020-(0[1-9]|1[0-2])$/.test(mes) ? `${NOMBRE_MES[Number(mes.slice(5, 7)) - 1]} de 2020` : mes
  if (muestra) return nombre ? `la muestra de prueba (${nombre})` : 'la muestra de prueba'
  return nombre ?? 'un mes'
}

/** Frases cortas, una por proceso en marcha, para los indicadores «En vivo» y la barra del lienzo. */
export function describirActividad(actividad: Actividad): string[] {
  const frases: string[] = []
  if (actividad.carga) {
    const que = describirCarga(actividad.carga.mes, actividad.carga.muestra)
    const estado = actividad.carga.estado === 'running' ? 'en ejecución' : 'en cola'
    const desde = actividad.carga.segundos != null && actividad.carga.estado === 'running'
      ? ` desde ${describirAntiguedad(actividad.carga.segundos)}` : ''
    frases.push(`Carga histórica de ${que} ${estado}${desde}`)
  }
  if (actividad.simulacion) {
    const { enviados, total, ritmo } = actividad.simulacion
    const de = total > 0 ? `${formatearEntero(enviados)} de ${formatearEntero(total)} viajes` : `${formatearEntero(enviados)} viajes enviados`
    frases.push(`Simulación en marcha: ${de} · ${formatearEntero(ritmo)} viajes/s`)
  }
  if (actividad.publicando) {
    frases.push(`Tiempo real: Spark publicó ${describirAntiguedad(actividad.frescuraSegundos)}`)
  }
  return frases
}

/** Una sola frase para los indicadores pequeños. */
export function resumirActividad(actividad: Actividad): string {
  const frases = describirActividad(actividad)
  if (frases.length === 0) return 'Sin procesos en marcha'
  return frases.length === 1 ? frases[0] : `${frases.length} procesos en marcha`
}

// --- el hook ---------------------------------------------------------------------------------------------------

/** `true` mientras `valor` lo es y durante `ms` después, para que un estado fugaz se llegue a ver. */
export function useSostenido(valor: boolean, ms: number): boolean {
  const [sostenido, setSostenido] = useState(valor)
  useEffect(() => {
    // al encenderse se apunta enseguida (para tenerlo cuando se apague); al apagarse se espera `ms`
    const id = setTimeout(() => setSostenido(valor), valor ? 0 : ms)
    return () => clearTimeout(id)
  }, [valor, ms])
  return valor || sostenido
}

export function useActividad(): Actividad {
  const ejecuciones = useEjecucionesAirflow()
  const simulacion = useSimulacion()
  const panel = usePanel()
  const consultando = useSostenido(
    useIsFetching({ predicate: (consulta) => CLAVES_CONSULTA.has(String(consulta.queryKey[0])) }) > 0,
    SOSTENER_CONSULTANDO_MS,
  )
  // la frescura avanza en cliente entre refrescos del panel (cada 5 s basta para los textos «hace X s»)
  const transcurridos = useSegundosDesde(panel.dataUpdatedAt || null, 5_000)
  const frescura = panel.data?.frescura_tiempo_real?.segundos
  return derivarActividad({
    ejecuciones: ejecuciones.data,
    simulacion: simulacion.data,
    frescuraSegundos: frescura == null ? null : frescura + (transcurridos ?? 0),
    consultando,
  })
}
