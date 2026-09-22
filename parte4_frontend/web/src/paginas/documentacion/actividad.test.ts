import { describe, expect, it } from 'vitest'

import { SIN_ACTIVIDAD, type Actividad } from '@/api/actividad'

import { claveArista, flujosDe } from './actividad'
import { ARISTAS } from './nodos'

const SIMULACION = {
  activa: true, lote: 'portal-muestra', fichero: 'yellow_tripdata_2020_muestra.csv', enviados: 450, total: 999,
  ritmo: 50, inicio: null, fin: null, error: null,
}

const con = (parcial: Partial<Actividad>): Actividad => ({ ...SIN_ACTIVIDAD, ...parcial, enMarcha: true })

describe('flujosDe', () => {
  it('sin actividad no ilumina nada', () => {
    const flujos = flujosDe(SIN_ACTIVIDAD)
    expect(flujos.aristas.size).toBe(0)
    expect(flujos.nodos.size).toBe(0)
  })

  it('una carga histórica recorre Airflow → S3 → Spark → MongoDB y dice qué mes carga', () => {
    const flujos = flujosDe(con({ carga: { id: 'r', estado: 'running', mes: '2020-03', muestra: false, inicio: null, segundos: 10 } }))
    expect([...flujos.aristas.keys()].sort()).toEqual(['airflow-s3', 's3-spark', 'spark-mongo'])
    expect(flujos.nodos.get('airflow')).toEqual({ texto: 'Cargando marzo de 2020', tono: 'ambar' })
    expect(flujos.nodos.get('spark')?.texto).toBe('Lote en curso')
    expect(flujos.nodos.get('mongo')?.texto).toBe('Publicando totales')
  })

  it('en cola, Airflow lo dice en su pastilla', () => {
    const flujos = flujosDe(con({ carga: { id: 'q', estado: 'queued', mes: null, muestra: true, inicio: null, segundos: null } }))
    expect(flujos.nodos.get('airflow')?.texto).toBe('En cola: la muestra de prueba')
  })

  it('la simulación recorre Simulador → Captura → Redpanda → Spark con el progreso', () => {
    const flujos = flujosDe(con({ simulacion: SIMULACION }))
    expect([...flujos.aristas.keys()].sort()).toEqual(['captura-redpanda', 'redpanda-spark', 'simulador-captura'])
    expect(flujos.nodos.get('simulador')).toEqual({ texto: '450 de 999 viajes', tono: 'verde' })
  })

  it('Spark publicando ilumina Redpanda → Spark → MongoDB con la antigüedad', () => {
    const flujos = flujosDe(con({ publicando: true, frescuraSegundos: 25 }))
    expect([...flujos.aristas.keys()].sort()).toEqual(['redpanda-spark', 'spark-mongo'])
    expect(flujos.nodos.get('spark')?.texto).toBe('Publicó hace 25 s')
  })

  it('el portal consultando ilumina MongoDB → acceso → portal, sin contar como en marcha', () => {
    const flujos = flujosDe({ ...SIN_ACTIVIDAD, consultando: true })
    expect([...flujos.aristas.keys()].sort()).toEqual(['acceso-portal', 'mongo-acceso'])
    expect(flujos.nodos.get('acceso')?.texto).toBe('Consulta del portal')
  })

  it('con carga y simulación a la vez, Spark conserva la pastilla del lote y se suman los tramos', () => {
    const flujos = flujosDe(con({
      carga: { id: 'r', estado: 'running', mes: '2020-03', muestra: false, inicio: null, segundos: 10 },
      simulacion: SIMULACION, publicando: true, frescuraSegundos: 40,
    }))
    expect(flujos.aristas.size).toBe(6)
    expect(flujos.nodos.get('spark')?.texto).toBe('Lote en curso')
  })

  it('Ollama ilumina MongoDB → acceso → Chatbots → Ollama', () => {
    const flujos = flujosDe(con({ chatOllama: true }))
    expect([...flujos.aristas.keys()].sort()).toEqual(['acceso-chatbots', 'chatbots-ollama', 'mongo-acceso'])
    expect(flujos.nodos.get('mongo')?.texto).toBe('Leyendo totales')
    expect(flujos.nodos.get('chatbots')?.texto).toBe('Preguntando')
    expect(flujos.nodos.get('ollama')?.texto).toBe('Redactando')
    expect(flujos.nodos.has('helmcode')).toBe(false)
  })

  it('DeepSeek ilumina el tramo hasta Helmcode y, si el portal también consulta, la pastilla del acceso es la del asistente', () => {
    const flujos = flujosDe(con({ chatHelmcode: true, consultando: true }))
    expect(flujos.aristas.has('chatbots-helmcode')).toBe(true)
    expect(flujos.aristas.has('acceso-portal')).toBe(true)
    expect(flujos.nodos.get('acceso')?.texto).toBe('Consulta del asistente')
    expect(flujos.nodos.get('helmcode')?.texto).toBe('Redactando')
    expect(flujos.nodos.has('ollama')).toBe(false)
  })

  it('todas las aristas que ilumina existen en el lienzo', () => {
    const existentes = new Set(ARISTAS.map((a) => claveArista(a.desde, a.hasta)))
    const flujos = flujosDe(con({
      carga: { id: 'r', estado: 'running', mes: '2020-03', muestra: false, inicio: null, segundos: 10 },
      simulacion: SIMULACION, publicando: true, frescuraSegundos: 40, consultando: true,
      chatOllama: true, chatHelmcode: true,
    }))
    for (const clave of flujos.aristas.keys()) expect(existentes.has(clave), clave).toBe(true)
  })
})
