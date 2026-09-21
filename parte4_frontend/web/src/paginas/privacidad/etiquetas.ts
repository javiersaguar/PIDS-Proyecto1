/**
 * Textos en español para los identificadores del catálogo y de la auditoría (niveles, métricas, fuentes,
 * resultados) y la lista de campos individuales prohibidos de `config/privacidad.json`.
 */
import type { Fuente, Metrica, Nivel } from '@/api/tipos'

export const NOMBRE_NIVEL: Record<Nivel, string> = {
  hora_zona: 'Por hora y zona de origen',
  dia_barrio: 'Por día y barrio de origen',
  od_dia_barrio: 'Flujos entre barrios por día',
}

export const NOMBRE_METRICA: Record<Metrica, string> = {
  n_viajes: 'Número de viajes',
  distancia_media: 'Distancia media',
  importe_medio: 'Importe medio',
  propina_media: 'Propina media',
  pct_pago_tarjeta: 'Porcentaje de pago con tarjeta',
}

export const NOMBRE_FUENTE: Record<Fuente, string> = {
  historico: 'Histórico (2020, cargas de Airflow)',
  tiempo_real: 'Tiempo real (streaming de Spark, colecciones tr_*)',
}

export const NOMBRE_DIMENSION: Record<string, string> = {
  hora: 'hora',
  dia: 'día',
  zona_origen: 'zona de origen',
  barrio_origen: 'barrio de origen',
  barrio_destino: 'barrio de destino',
}

/** Los tres resultados posibles de una decisión de la API de acceso, con su color de estado. */
export const RESULTADOS = ['permitida', 'enmascarada', 'rechazada'] as const
export type Resultado = (typeof RESULTADOS)[number]

export const TEXTO_RESULTADO: Record<string, string> = {
  permitida: 'Permitida',
  enmascarada: 'Enmascarada',
  rechazada: 'Rechazada',
}

export const CLASE_RESULTADO: Record<string, string> = {
  permitida: 'bg-ok/10 text-ok border-ok/30',
  enmascarada: 'bg-enmascarado-suave text-enmascarado border-enmascarado/30',
  rechazada: 'bg-peligro/10 text-peligro border-peligro/30',
}

/** `campos_individuales` de `config/privacidad.json`: cualquier consulta que los pida se rechaza. */
export const CAMPOS_INDIVIDUALES = [
  'id',
  'recogida',
  'llegada',
  'lote',
  'vendor_id',
  'pasajeros',
  'tarifa',
  'propina',
  'importe_total',
  'zona_destino',
  'minuto',
  'segundo',
  'matricula',
  'conductor',
]

/** Granularidad temporal de un nivel a partir de sus dimensiones: con `hora` es la hora completa; si no, el día. */
export function granularidadDe(dimensiones: string[]): string {
  return dimensiones.includes('hora') ? 'hora completa' : 'día completo'
}
