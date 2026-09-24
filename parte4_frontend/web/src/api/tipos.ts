/**
 * Tipos de las respuestas del BFF (`/api/*`). Son exactamente los del §5 de CONTRATOS.md: F1 y F2 devuelven
 * estas formas y F3 y F4 las consumen. Si una página necesita un tipo que no está aquí, lo define en su propio
 * fichero de `src/api/`.
 */

// --- plataforma (F1) ---
export type Nivel = 'hora_zona' | 'dia_barrio' | 'od_dia_barrio';
export type Fuente = 'historico' | 'tiempo_real';
export type Metrica = 'n_viajes' | 'distancia_media' | 'importe_medio' | 'propina_media' | 'pct_pago_tarjeta';

export interface Catalogo {                      // GET /api/catalogo  (proxy de GET /catalogo de la API de acceso)
  k_minimo: number; max_dias_por_consulta: number; metricas: Metrica[];
  niveles: Record<Nivel, { descripcion: string; dimensiones: string[] }>;
  fuentes: Fuente[]; barrios: string[];
}
export interface Zona { _id: number; nombre: string; barrio: string; tipo_servicio?: string }   // GET /api/zonas?texto=

export interface Consulta {                      // POST /api/consultas (cuerpo) — la misma Consulta de la API de acceso
  nivel: Nivel; fuente?: Fuente; desde: string; hasta: string;             // ISO sin zona: 2020-01-15T08:00:00
  metricas?: Metrica[]; zona_origen?: number | null; barrio_origen?: string | null; barrio_destino?: string | null;
}
export interface Fila {                          // una fila de agregados; n_viajes es "oculto" si el grupo está enmascarado
  hora?: string; dia?: string; zona_origen?: number; zona_origen_nombre?: string;
  barrio_origen?: string; barrio_destino?: string; n_viajes: number | string; suprimido: boolean;
  distancia_media?: number | null; importe_medio?: number | null; propina_media?: number | null; pct_pago_tarjeta?: number | null;
}
export interface Respuesta {                     // 200 de POST /api/consultas (la Respuesta de la API, tal cual)
  resultado: 'permitida' | 'enmascarada'; consulta: Consulta; filas: Fila[];
  grupos_enmascarados: number; truncada: boolean; nota: string;
}
export interface Decision {                      // 403 de POST /api/consultas (la Decision de la API, tal cual)
  resultado: 'rechazada'; motivos: string[]; alternativa: Consulta | null;
}

export interface Servicio { nombre: string; job: string; estado: 'ok' | 'caido' | 'desconocido'; enlace?: string }
export interface Panel {                         // GET /api/panel
  ultimo_dia: { historico: UltimoDia | null; tiempo_real: UltimoDia | null };
  frescura_tiempo_real: { instante: string | null; segundos: number | null };   // desde publico_ultima_actualizacion_timestamp_segundos
  consultas_24h: { permitida: number; enmascarada: number; rechazada: number } | null;   // increase(acceso_consultas_total[24h]) por resultado
  servicios: Servicio[];                                                        // `up` por job en Prometheus + GET /salud de las APIs
  enlaces: Record<'grafana' | 'airflow' | 'spark' | 'chatbot' | 'chatbot_rag' | 'api_acceso' | 'api_captura', string> &
    Partial<Record<'prometheus' | 'qdrant' | 'seaweed', string>>;   // sin login: solo con `make ver`
  prometheus_disponible: boolean;
  acceso_disponible: boolean;                    // false si la API de acceso no ha respondido (distinto de «sin datos»)
}
// solo grupos visibles; los enmascarados se cuentan, nunca se suman
export interface UltimoDia { dia: string; por_barrio: Record<string, number>; total: number; grupos_enmascarados: number }

export interface TiempoReal {                    // GET /api/tiempo-real?horas=6
  acceso_disponible: boolean;
  frescura: Panel['frescura_tiempo_real'];
  ultimo_dia: string | null;                     // último día con datos en tr_viajes_dia_barrio
  por_hora: { hora: string; n_viajes: number; grupos: number; grupos_enmascarados: number }[];   // últimas N horas con datos, solo visibles
  por_zona_ultima_hora: Fila[];                  // las filas de la última hora (hora_zona, fuente tiempo_real)
}

export interface AuditoriaResumen {              // GET /api/auditoria/resumen?horas=24
  desde: string; hasta: string; total: number;
  resultados: Record<string, number>; clientes: Record<string, number>;
  motivos: { motivo: string; cantidad: number }[];          // tipo de motivo (antes de ': '), como scripts/informe_auditoria.py
  disponible: boolean;
}
export interface DecisionAuditada {              // GET /api/auditoria/decisiones?horas=24&resultado=&cliente=&limite=100
  instante: string; cliente: string; componente: string; resultado: string; motivos: string[];
  consulta: Record<string, unknown>; alternativa: Consulta | null; filas_devueltas?: number; grupos_enmascarados?: number;
}
export interface Carga {                         // GET /api/auditoria/cargas
  lote: string; entrada: string; origen: string; filas: number; validos: number; rechazados: number;
  motivos: Record<string, number>; grupos_publicados: Record<string, number>; grupos_suprimidos: Record<string, number>;
  grupos_complementarios?: Record<string, number>; version_reglas: number; instante: string;
}

export interface EjecucionAirflow {              // GET /api/operaciones/airflow/ejecuciones  (últimas 20 de pids_carga_historica)
  dag_run_id: string; estado: string; conf: Record<string, unknown>; inicio: string | null; fin: string | null;
}
// POST /api/operaciones/airflow/cargas {mes: '2020-01', muestra: boolean} -> EjecucionAirflow (202)
export interface Simulacion {                    // GET /api/operaciones/simulacion · POST (inicia) · DELETE (para)
  activa: boolean; lote: string | null; fichero: string | null; sinteticos: number | null;
  dia?: string | null;                           // 'AAAA-MM-DD': día al que se movieron los viajes (marca de agua)
  enviados: number; total: number;
  ritmo: number; inicio: string | null; fin: string | null; error: string | null;
}
// POST /api/operaciones/simulacion {fichero: 'yellow_tripdata_2020_muestra.csv', ritmo?: 50, maximo?: number,
//   sinteticos?: number, semilla?: number} -> Simulacion (202)
// `sinteticos`: en vez de enviar el fichero, se inventan esos viajes usándolo de plantilla (la muestra tiene 999).
// Los ficheros permitidos son solo los de data/muestra (GET /api/operaciones/simulacion/ficheros -> string[]).

// --- chat (F2) ---
export interface Motor { id: 'ollama' | 'rag'; nombre: string; modelo: string; disponible: boolean; descripcion: string }
// GET /api/chat/motores -> Motor[]
// POST /api/chat/sesiones {motor} -> {id: string, motor: Motor['id']}   · DELETE /api/chat/sesiones/{id} -> 204
// POST /api/chat/sesiones/{id}/mensajes {texto} -> text/event-stream con los eventos de abajo
// POST /api/chat/sesiones/{id}/alternativa -> el mismo flujo, ejecutando la alternativa pendiente de la sesión
export interface EventoPaso { nombre: string; argumentos: Record<string, unknown>; resultado: string; segundos: number }
export interface EventoRespuesta {
  respuesta: string;                             // Markdown (tal cual lo produce el agente: tablas, 🔒, pie de fuente)
  bloqueo: string | null; pasos_llm: number; segundos: number; tokens: number | null;
  alternativa: Consulta | null; alternativa_descripcion: string | null;      // agente.describir(alternativa)
  fuentes: { titulo: string; fuente: string; tipo: string }[];             // solo el motor rag
}
// eventos SSE: `paso` (EventoPaso), `respuesta` (EventoRespuesta), `error` ({detail})

// --- sesión del portal (F0, §4) ---
export interface EstadoSesion { autenticado: boolean }   // GET /api/sesion
