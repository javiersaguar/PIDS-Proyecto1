import { describe, expect, it } from 'vitest'

import {
  chatsDesdeDecisiones, derivarActividad, describirActividad, describirCarga, estadoEnMarcha, resumirActividad, SIN_ACTIVIDAD,
  UMBRAL_CHAT_MS, UMBRAL_PUBLICANDO_S,
} from './actividad'
import type { EjecucionAirflow, Simulacion } from './tipos'

const AHORA = Date.parse('2026-09-22T10:00:00Z')

const ejecucion = (parcial: Partial<EjecucionAirflow>): EjecucionAirflow => ({
  dag_run_id: 'manual__1', estado: 'success', conf: { mes: '2020-03', muestra: false },
  inicio: '2026-09-22T09:40:00+00:00', fin: '2026-09-22T09:42:00+00:00', ...parcial,
})

const SIMULACION: Simulacion = {
  activa: true, lote: 'portal-muestra', fichero: 'yellow_tripdata_2020_muestra.csv', sinteticos: null,
  enviados: 450, total: 999, ritmo: 50, inicio: '2026-09-22T09:59:50+00:00', fin: null, error: null,
}

describe('derivarActividad', () => {
  it('sin nada en marcha, no hay actividad', () => {
    expect(derivarActividad({ ahoraMs: AHORA })).toEqual(SIN_ACTIVIDAD)
    expect(derivarActividad({ ejecuciones: [ejecucion({})], simulacion: { ...SIMULACION, activa: false }, frescuraSegundos: 900, ahoraMs: AHORA }).enMarcha).toBe(false)
  })

  it('una ejecución running de Airflow es una carga en marcha, con su mes y desde cuándo', () => {
    const actividad = derivarActividad({
      ejecuciones: [ejecucion({ dag_run_id: 'manual__2', estado: 'running', inicio: '2026-09-22T09:58:00+00:00', fin: null }), ejecucion({})],
      ahoraMs: AHORA,
    })
    expect(actividad.carga).toEqual({ id: 'manual__2', estado: 'running', mes: '2020-03', muestra: false, inicio: '2026-09-22T09:58:00+00:00', segundos: 120 })
    expect(actividad.ultimaCarga).toMatchObject({ estado: 'success', mes: '2020-03', segundos: 18 * 60 })
    expect(actividad.enMarcha).toBe(true)
  })

  it('queued y scheduled cuentan como en cola; running manda sobre ellas', () => {
    expect(estadoEnMarcha('queued')).toBe('queued')
    expect(estadoEnMarcha('scheduled')).toBe('queued')
    expect(estadoEnMarcha('failed')).toBeNull()
    const actividad = derivarActividad({
      ejecuciones: [ejecucion({ dag_run_id: 'q', estado: 'queued', inicio: null, fin: null }), ejecucion({ dag_run_id: 'r', estado: 'running', fin: null })],
      ahoraMs: AHORA,
    })
    expect(actividad.carga?.id).toBe('r')
  })

  it('la simulación solo cuenta mientras está activa', () => {
    expect(derivarActividad({ simulacion: SIMULACION, ahoraMs: AHORA }).simulacion).toEqual(SIMULACION)
    expect(derivarActividad({ simulacion: { ...SIMULACION, activa: false }, ahoraMs: AHORA }).simulacion).toBeNull()
  })

  it('Spark está publicando si el último agregado de tiempo real tiene menos de dos minutos', () => {
    expect(derivarActividad({ frescuraSegundos: 25, ahoraMs: AHORA })).toMatchObject({ publicando: true, enMarcha: true, frescuraSegundos: 25 })
    expect(derivarActividad({ frescuraSegundos: UMBRAL_PUBLICANDO_S + 1, ahoraMs: AHORA }).publicando).toBe(false)
    expect(derivarActividad({ frescuraSegundos: null, ahoraMs: AHORA }).publicando).toBe(false)
  })

  it('consultar no es estar en marcha: solo ilumina el tramo del portal', () => {
    const actividad = derivarActividad({ consultando: true, ahoraMs: AHORA })
    expect(actividad.consultando).toBe(true)
    expect(actividad.enMarcha).toBe(false)
  })

  it('un asistente en curso sí está en marcha y dice con qué modelo redacta', () => {
    const ollama = derivarActividad({ chatOllama: true, ahoraMs: AHORA })
    const helmcode = derivarActividad({ chatHelmcode: true, ahoraMs: AHORA })
    expect(ollama.enMarcha).toBe(true)
    expect(describirActividad(ollama)).toEqual(['El asistente consulta con Ollama'])
    expect(describirActividad(helmcode)).toEqual(['El asistente consulta con Mistral'])
  })

  it('la auditoría reciente de Chainlit enciende el modelo que preguntó', () => {
    const reciente = new Date(AHORA - 10_000).toISOString()
    const vieja = new Date(AHORA - UMBRAL_CHAT_MS - 1_000).toISOString()
    expect(chatsDesdeDecisiones([
      { instante: reciente, cliente: 'chatbot' },
      { instante: reciente, cliente: 'chatbot_rag' },
      { instante: vieja, cliente: 'chatbot' },
      { instante: reciente, cliente: 'frontend' },
    ], AHORA)).toEqual({ ollama: true, helmcode: true })
    expect(chatsDesdeDecisiones([{ instante: vieja, cliente: 'chatbot_rag' }], AHORA)).toEqual({ ollama: false, helmcode: false })
  })
})

describe('textos de la actividad', () => {
  it('describe la carga por su mes o por la muestra', () => {
    expect(describirCarga('2020-03', false)).toBe('marzo de 2020')
    expect(describirCarga('2020-01', true)).toBe('la muestra de prueba (enero de 2020)')
    expect(describirCarga(null, true)).toBe('la muestra de prueba')
    expect(describirCarga(null, false)).toBe('un mes')
  })

  it('una frase por proceso, y un resumen corto', () => {
    const actividad = derivarActividad({
      ejecuciones: [ejecucion({ estado: 'running', inicio: '2026-09-22T09:58:00+00:00', fin: null })],
      simulacion: SIMULACION, frescuraSegundos: 25, ahoraMs: AHORA,
    })
    expect(describirActividad(actividad)).toEqual([
      'Carga histórica de marzo de 2020 en ejecución desde hace 2 min',
      'Simulación en marcha: 450 de 999 viajes · 50 viajes/s',
      'Tiempo real: Spark publicó hace 25 s',
    ])
    expect(resumirActividad(actividad)).toBe('3 procesos en marcha')
    expect(resumirActividad(derivarActividad({ simulacion: SIMULACION, ahoraMs: AHORA }))).toBe('Simulación en marcha: 450 de 999 viajes · 50 viajes/s')
    expect(resumirActividad(SIN_ACTIVIDAD)).toBe('Sin procesos en marcha')
  })

  it('una carga en cola no dice desde cuándo', () => {
    const actividad = derivarActividad({ ejecuciones: [ejecucion({ estado: 'queued', conf: { mes: '2020-05', muestra: true }, fin: null })], ahoraMs: AHORA })
    expect(describirActividad(actividad)).toEqual(['Carga histórica de la muestra de prueba (mayo de 2020) en cola'])
  })
})
