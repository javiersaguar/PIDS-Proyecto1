/**
 * Qué tramos del lienzo se iluminan con cada proceso en marcha (`useActividad`), y qué pastilla lleva cada
 * pieza mientras trabaja. Lógica pura sobre las aristas de `nodos.ts`.
 *
 *   carga histórica     Airflow → S3 → Spark → MongoDB
 *   simulación          Simulador → Captura → Redpanda → Spark
 *   Spark publicando    Redpanda → Spark → MongoDB
 *   el portal consulta  MongoDB → API de acceso → Portal
 *   un chatbot         MongoDB → API de acceso → Chatbots → Ollama o Helmcode (DeepSeek)
 *   el portal vigila   Prometheus → Portal (estado de los servicios, Observabilidad) y Grafana → Portal (alertas)
 *   un gesto           Captura → Redpanda (si entró en la plataforma) y la pastilla del gesto en Chatbots (en el
 *                      Portal si es ✋, que cambia de sección)
 */
import type { Actividad } from '@/api/actividad'
import { describirCarga } from '@/api/actividad'
import { describirAntiguedad, formatearEntero } from '@/componentes/datos/formato'
import { GESTOS } from '@/gestos/tabla'

import type { Tono } from './nodos'

export interface Flujo {
  desde: string
  hasta: string
  /** Color del flujo (por defecto, el de la arista). */
  tono?: Tono
}

export interface Realce {
  texto: string
  tono: Tono
}

export interface Flujos {
  /** Aristas activas por su clave `${desde}-${hasta}`. */
  aristas: Map<string, Flujo>
  /** Piezas que trabajan, con el texto de su pastilla. */
  nodos: Map<string, Realce>
}

export const claveArista = (desde: string, hasta: string) => `${desde}-${hasta}`

export const SIN_FLUJOS: Flujos = { aristas: new Map(), nodos: new Map() }

function activar(flujos: Flujos, tramos: readonly (readonly [string, string])[]): void {
  for (const [desde, hasta] of tramos) {
    flujos.aristas.set(claveArista(desde, hasta), { desde, hasta })
  }
}

function realzar(flujos: Flujos, id: string, texto: string, tono: Tono, forzar = false): void {
  if (!forzar && flujos.nodos.has(id)) return
  flujos.nodos.set(id, { texto, tono })
}

export function flujosDe(actividad: Actividad): Flujos {
  const flujos: Flujos = { aristas: new Map(), nodos: new Map() }

  if (actividad.carga) {
    activar(flujos, [['airflow', 's3'], ['s3', 'spark'], ['spark', 'mongo']])
    const que = describirCarga(actividad.carga.mes, actividad.carga.muestra)
    realzar(flujos, 'airflow', actividad.carga.estado === 'running' ? `Cargando ${que}` : `En cola: ${que}`, 'ambar')
    realzar(flujos, 's3', 'Recibe el fichero', 'coral')
    realzar(flujos, 'spark', 'Lote en curso', 'violeta')
    realzar(flujos, 'mongo', 'Publicando totales', 'azul')
  }

  if (actividad.simulacion) {
    activar(flujos, [['simulador', 'captura'], ['captura', 'redpanda'], ['redpanda', 'spark']])
    const { enviados, total } = actividad.simulacion
    const progreso = total > 0 ? `${formatearEntero(enviados)} de ${formatearEntero(total)} viajes` : `${formatearEntero(enviados)} viajes`
    realzar(flujos, 'simulador', progreso, 'verde')
    realzar(flujos, 'captura', 'Recibiendo viajes', 'verde')
    realzar(flujos, 'redpanda', 'Encolando', 'verde')
  }

  if (actividad.publicando) {
    activar(flujos, [['redpanda', 'spark'], ['spark', 'mongo']])
    realzar(flujos, 'spark', `Publicó ${describirAntiguedad(actividad.frescuraSegundos)}`, 'violeta')
    realzar(flujos, 'mongo', 'Totales al día', 'azul')
  }

  if (actividad.consultando) {
    activar(flujos, [['mongo', 'acceso'], ['acceso', 'portal']])
    realzar(flujos, 'acceso', 'Consulta del portal', 'azul')
    realzar(flujos, 'portal', 'Pidiendo totales', 'azul')
  }

  if (actividad.chatOllama || actividad.chatHelmcode) {
    activar(flujos, [['mongo', 'acceso'], ['acceso', 'chatbots']])
    realzar(flujos, 'mongo', 'Leyendo totales', 'azul')
    realzar(flujos, 'acceso', 'Consulta del asistente', 'azul', true)
    realzar(flujos, 'chatbots', 'Preguntando', 'cian')
    if (actividad.chatOllama) {
      activar(flujos, [['chatbots', 'ollama']])
      realzar(flujos, 'ollama', 'Redactando', 'violeta')
    }
    if (actividad.chatHelmcode) {
      activar(flujos, [['chatbots', 'helmcode']])
      realzar(flujos, 'helmcode', 'Redactando', 'cian')
    }
  }

  if (actividad.leyendoMetricas) {
    activar(flujos, [['prometheus', 'portal']])
    realzar(flujos, 'prometheus', 'Métricas al portal', 'cian')
  }

  if (actividad.leyendoAlertas) {
    activar(flujos, [['grafana', 'portal']])
    realzar(flujos, 'grafana', 'Estado de las alertas', 'cian')
  }

  if (actividad.gesto) {
    const { emoji, titulo, accion } = GESTOS[actividad.gesto.gesto]
    if (actividad.gesto.enPlataforma) {
      activar(flujos, [['captura', 'redpanda']])
      realzar(flujos, 'captura', `Gesto ${emoji}`, 'verde')
      realzar(flujos, 'redpanda', 'Cola de gestos', 'verde')
    }
    realzar(flujos, accion === 'seccion' ? 'portal' : 'chatbots', `${emoji} ${titulo}`, 'cian')
  }

  return flujos
}
