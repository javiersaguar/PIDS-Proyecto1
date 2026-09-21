/**
 * Lógica pura del explorador: el formulario y su conversión a `Consulta` (lo que se envía a la API y se guarda en
 * la URL), la validación en cliente (ventana no vacía y rango máximo), la descripción de una consulta en lenguaje
 * natural (como `agente.describir` del chatbot) y los ejemplos rápidos.
 *
 * Las fechas son ISO sin zona (`2020-01-15T08:00:00`) y se operan como instantes UTC para que la aritmética sea la
 * misma que hace la API con `datetime` (sin sorpresas por cambios de hora).
 */
import type { Consulta, Fuente, Metrica, Nivel } from '@/api/tipos'
import { esFuente, esMetrica, esNivel, ETIQUETAS_METRICA, METRICAS } from '@/componentes/datos/agregados'

export interface Formulario {
  nivel: Nivel
  fuente: Fuente
  /** `YYYY-MM-DD`. */
  fechaDesde: string
  fechaHasta: string
  /** Hora en punto (0-23); solo cuenta en `hora_zona`. */
  horaDesde: number
  horaHasta: number
  zonaOrigen: number | null
  barrioOrigen: string | null
  barrioDestino: string | null
  /** Siempre incluye `n_viajes`. */
  metricas: Metrica[]
}

export const FORMULARIO_INICIAL: Formulario = {
  nivel: 'dia_barrio',
  fuente: 'historico',
  fechaDesde: '2020-01-01',
  fechaHasta: '2020-01-02',
  horaDesde: 0,
  horaHasta: 0,
  zonaOrigen: null,
  barrioOrigen: null,
  barrioDestino: null,
  metricas: ['n_viajes'],
}

/** Máximo de días por consulta si el catálogo aún no ha llegado (`config/privacidad.json`). */
export const MAX_DIAS_POR_DEFECTO = 31

/** Barrios de la plataforma si el catálogo aún no ha llegado. */
export const BARRIOS_POR_DEFECTO = ['Bronx', 'Brooklyn', 'EWR', 'Manhattan', 'N/A', 'Queens', 'Staten Island', 'Unknown']

export const DESCRIPCIONES_NIVEL_POR_DEFECTO: Record<Nivel, string> = {
  hora_zona: 'Viajes por hora y zona de origen. Sin destino: origen y destino a nivel de hora identificarían a personas.',
  dia_barrio: 'Viajes por día y barrio (borough) de origen.',
  od_dia_barrio: 'Flujos entre barrios por día: el único nivel con destino, y solo a nivel de barrio y día.',
}

export function esPorHoras(nivel: Nivel): boolean {
  return nivel === 'hora_zona'
}

export function admiteZona(nivel: Nivel): boolean {
  return nivel === 'hora_zona'
}

export function admiteBarrioOrigen(nivel: Nivel): boolean {
  return nivel !== 'hora_zona'
}

export function admiteBarrioDestino(nivel: Nivel): boolean {
  return nivel === 'od_dia_barrio'
}

const PATRON_ISO = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?)?$/

/** Instante UTC (ms) de una fecha ISO sin zona; `null` si no es válida. */
export function marcaDe(iso: string | null | undefined): number | null {
  if (!iso) return null
  const m = PATRON_ISO.exec(iso.trim())
  if (!m) return null
  const [, a, me, d, h = '0', mi = '0', s = '0'] = m
  const marca = Date.UTC(Number(a), Number(me) - 1, Number(d), Number(h), Number(mi), Number(s))
  if (!Number.isFinite(marca)) return null
  const fecha = new Date(marca)
  // Descarta fechas como el 31/02, que Date.UTC «arregla» en silencio.
  if (fecha.getUTCMonth() !== Number(me) - 1 || fecha.getUTCDate() !== Number(d) || Number(h) > 23 || Number(mi) > 59) return null
  return marca
}

function dosCifras(n: number): string {
  return String(n).padStart(2, '0')
}

/** `2020-01-15T08:00:00` a partir de `2020-01-15` y la hora 8. */
export function isoDe(fecha: string, hora = 0): string {
  return `${fecha}T${dosCifras(hora)}:00:00`
}

/** ISO sin zona (`2020-01-15T08:00:00`) de un instante UTC en ms. */
export function isoDeMarca(marca: number): string {
  const f = new Date(marca)
  return `${f.getUTCFullYear()}-${dosCifras(f.getUTCMonth() + 1)}-${dosCifras(f.getUTCDate())}T${dosCifras(f.getUTCHours())}:${dosCifras(f.getUTCMinutes())}:${dosCifras(f.getUTCSeconds())}`
}

const MS_HORA = 3_600_000
const MS_DIA = 24 * MS_HORA

/** `n_viajes` primero y el resto en el orden del catálogo, sin repetidos. */
export function normalizarMetricas(metricas: readonly string[] | undefined): Metrica[] {
  const pedidas = new Set<string>(['n_viajes', ...(metricas ?? [])])
  return METRICAS.filter((m) => pedidas.has(m))
}

/** Formulario → Consulta. Los filtros que el nivel no admite se descartan. */
export function aConsulta(f: Formulario): Consulta {
  const porHoras = esPorHoras(f.nivel)
  const consulta: Consulta = {
    nivel: f.nivel,
    fuente: f.fuente,
    desde: isoDe(f.fechaDesde, porHoras ? f.horaDesde : 0),
    hasta: isoDe(f.fechaHasta, porHoras ? f.horaHasta : 0),
    metricas: normalizarMetricas(f.metricas),
  }
  if (admiteZona(f.nivel) && f.zonaOrigen != null) consulta.zona_origen = f.zonaOrigen
  if (admiteBarrioOrigen(f.nivel) && f.barrioOrigen) consulta.barrio_origen = f.barrioOrigen
  if (admiteBarrioDestino(f.nivel) && f.barrioDestino) consulta.barrio_destino = f.barrioDestino
  return consulta
}

/** Consulta → Formulario (al restaurar desde la URL o al rellenar una alternativa). */
export function aFormulario(c: Consulta): Formulario {
  const desde = c.desde.slice(0, 10)
  const hasta = c.hasta.slice(0, 10)
  return {
    nivel: c.nivel,
    fuente: c.fuente ?? 'historico',
    fechaDesde: desde,
    fechaHasta: hasta,
    horaDesde: Number(c.desde.slice(11, 13)) || 0,
    horaHasta: Number(c.hasta.slice(11, 13)) || 0,
    zonaOrigen: c.zona_origen ?? null,
    barrioOrigen: c.barrio_origen ?? null,
    barrioDestino: c.barrio_destino ?? null,
    metricas: normalizarMetricas(c.metricas),
  }
}

/** Consulta → parámetros de la URL (`?nivel=…&desde=…`), omitiendo lo que no está. */
export function aParametros(c: Consulta): URLSearchParams {
  const p = new URLSearchParams()
  p.set('nivel', c.nivel)
  p.set('fuente', c.fuente ?? 'historico')
  p.set('desde', c.desde)
  p.set('hasta', c.hasta)
  const metricas = normalizarMetricas(c.metricas)
  if (metricas.length > 1) p.set('metricas', metricas.join(','))
  if (c.zona_origen != null) p.set('zona_origen', String(c.zona_origen))
  if (c.barrio_origen) p.set('barrio_origen', c.barrio_origen)
  if (c.barrio_destino) p.set('barrio_destino', c.barrio_destino)
  return p
}

/** Parámetros de la URL → Consulta; `null` si faltan el nivel o las fechas o no son válidos. */
export function desdeParametros(p: URLSearchParams): Consulta | null {
  const nivel = p.get('nivel')
  const desde = p.get('desde')
  const hasta = p.get('hasta')
  if (!esNivel(nivel) || marcaDe(desde) === null || marcaDe(hasta) === null) return null
  const fuente = p.get('fuente')
  const consulta: Consulta = {
    nivel,
    fuente: esFuente(fuente) ? fuente : 'historico',
    desde: normalizarIso(desde as string),
    hasta: normalizarIso(hasta as string),
    metricas: normalizarMetricas((p.get('metricas') ?? '').split(',').filter(esMetrica)),
  }
  const zona = p.get('zona_origen')
  if (zona !== null && /^\d+$/.test(zona)) consulta.zona_origen = Number(zona)
  const origen = p.get('barrio_origen')
  if (origen) consulta.barrio_origen = origen
  const destino = p.get('barrio_destino')
  if (destino) consulta.barrio_destino = destino
  return consulta
}

function normalizarIso(iso: string): string {
  const marca = marcaDe(iso)
  return marca === null ? iso : isoDeMarca(marca)
}

export interface Errores {
  fechas?: string
  rango?: string
}

/** Validación en cliente: fechas válidas, `hasta > desde` y rango ≤ `maxDias`. Devuelve `{}` si todo está bien. */
export function validar(f: Formulario, maxDias = MAX_DIAS_POR_DEFECTO): Errores {
  const c = aConsulta(f)
  const desde = marcaDe(c.desde)
  const hasta = marcaDe(c.hasta)
  if (desde === null || hasta === null) return { fechas: 'Indica una fecha de inicio y otra de fin válidas.' }
  if (hasta <= desde) {
    return {
      fechas: esPorHoras(f.nivel)
        ? 'La hora de fin debe ser posterior a la de inicio (el fin no se incluye: de 08:00 a 12:00 cubre cuatro horas).'
        : 'La fecha de fin debe ser posterior a la de inicio (el fin no se incluye: para un solo día, indica el día siguiente).',
    }
  }
  if (hasta - desde > maxDias * MS_DIA) {
    return { rango: `El rango máximo por consulta es de ${maxDias} días (la ventana elegida tiene ${describirDuracion(hasta - desde)}).` }
  }
  return {}
}

function describirDuracion(ms: number): string {
  const horas = Math.round(ms / MS_HORA)
  if (horas < 24) return horas === 1 ? '1 hora' : `${horas} horas`
  const dias = Math.floor(horas / 24)
  const resto = horas % 24
  const textoDias = dias === 1 ? '1 día' : `${dias} días`
  return resto ? `${textoDias} y ${resto} h` : textoDias
}

/** Ventana legible: «1 día (03/03/2020)», «4 horas (15/01/2020 de 08:00 a 12:00)», «7 días (del 01/02 al 07/02/2020)». */
export function describirVentana(c: Pick<Consulta, 'desde' | 'hasta'>): string {
  const desde = marcaDe(c.desde)
  const hasta = marcaDe(c.hasta)
  if (desde === null || hasta === null || hasta <= desde) return 'ventana vacía'
  return `${describirDuracion(hasta - desde)} (${describirPeriodo(desde, hasta)})`
}

function fechaUtc(marca: number): string {
  const f = new Date(marca)
  return `${dosCifras(f.getUTCDate())}/${dosCifras(f.getUTCMonth() + 1)}/${f.getUTCFullYear()}`
}

function horaUtc(marca: number): string {
  const f = new Date(marca)
  return `${dosCifras(f.getUTCHours())}:${dosCifras(f.getUTCMinutes())}`
}

function esMedianoche(marca: number): boolean {
  return marca % MS_DIA === 0
}

/** «el 15/01/2020», «del 01/02/2020 al 07/02/2020», «el 15/01/2020 de 08:00 a 12:00»… (como `agente._ventana`). */
function describirPeriodo(desde: number, hasta: number): string {
  if (esMedianoche(desde) && esMedianoche(hasta)) {
    const ultimo = hasta - MS_DIA
    return ultimo === desde ? `el ${fechaUtc(desde)}` : `del ${fechaUtc(desde)} al ${fechaUtc(ultimo)}`
  }
  if (fechaUtc(hasta - 1000) === fechaUtc(desde)) {
    return `el ${fechaUtc(desde)} de ${horaUtc(desde)} a ${horaUtc(hasta)}`
  }
  return `del ${fechaUtc(desde)} ${horaUtc(desde)} al ${fechaUtc(hasta)} ${horaUtc(hasta)}`
}

const TEXTO_NIVEL: Record<Nivel, string> = {
  hora_zona: 'viajes por hora',
  dia_barrio: 'viajes por día',
  od_dia_barrio: 'flujos por día',
}

function enumerar(partes: string[]): string {
  if (partes.length <= 1) return partes.join('')
  return `${partes.slice(0, -1).join(', ')} y ${partes[partes.length - 1]}`
}

/**
 * «viajes por hora desde JFK Airport (zona 132) el 15/01/2020 de 08:00 a 12:00 (histórico)», como
 * `agente.describir` del chatbot.
 */
export function describirConsulta(c: Consulta, nombresZona?: ReadonlyMap<number, string>): string {
  const partes = [TEXTO_NIVEL[c.nivel] ?? 'viajes']
  if (c.zona_origen != null) {
    const nombre = nombresZona?.get(c.zona_origen)
    partes.push(nombre ? `desde ${nombre} (zona ${c.zona_origen})` : `desde la zona ${c.zona_origen}`)
  }
  if (c.barrio_origen) partes.push(`desde ${c.barrio_origen}`)
  if (c.barrio_destino) partes.push(`hacia ${c.barrio_destino}`)
  const desde = marcaDe(c.desde)
  const hasta = marcaDe(c.hasta)
  if (desde !== null && hasta !== null && hasta > desde) partes.push(describirPeriodo(desde, hasta))
  const metricas = normalizarMetricas(c.metricas).filter((m) => m !== 'n_viajes')
  if (metricas.length) partes.push(`con ${enumerar(metricas.map((m) => ETIQUETAS_METRICA[m].toLowerCase()))}`)
  partes.push(c.fuente === 'tiempo_real' ? '(tiempo real)' : '(histórico)')
  return partes.join(' ')
}

export interface Ejemplo {
  titulo: string
  descripcion: string
  consulta: Consulta
}

/** Ejemplos rápidos (los casos de uso CU1, CU2, CU4 y CU6 de `docs/casos_uso.md`, con datos de 2020). */
export const EJEMPLOS: readonly Ejemplo[] = [
  {
    titulo: 'JFK por horas el 15/01',
    descripcion: 'Viajes por hora desde JFK Airport (zona 132) el 15/01/2020, con importe y propina medios.',
    consulta: {
      nivel: 'hora_zona',
      fuente: 'historico',
      desde: '2020-01-15T00:00:00',
      hasta: '2020-01-16T00:00:00',
      zona_origen: 132,
      metricas: ['n_viajes', 'importe_medio', 'propina_media'],
    },
  },
  {
    titulo: 'Barrios el 03/03',
    descripcion: 'Viajes por barrio de origen el 03/03/2020 con todas las métricas (Staten Island sale enmascarado).',
    consulta: {
      nivel: 'dia_barrio',
      fuente: 'historico',
      desde: '2020-03-03T00:00:00',
      hasta: '2020-03-04T00:00:00',
      metricas: ['n_viajes', 'distancia_media', 'importe_medio', 'propina_media', 'pct_pago_tarjeta'],
    },
  },
  {
    titulo: 'Flujos Queens→Manhattan el 10/01',
    descripcion: 'Viajes de Queens a Manhattan el 10/01/2020 (el destino solo se publica por barrio y día).',
    consulta: {
      nivel: 'od_dia_barrio',
      fuente: 'historico',
      desde: '2020-01-10T00:00:00',
      hasta: '2020-01-11T00:00:00',
      barrio_origen: 'Queens',
      barrio_destino: 'Manhattan',
      metricas: ['n_viajes'],
    },
  },
  {
    titulo: 'Matriz de flujos el 10/01',
    descripcion: 'Todos los flujos entre barrios el 10/01/2020: la matriz origen → destino completa.',
    consulta: {
      nivel: 'od_dia_barrio',
      fuente: 'historico',
      desde: '2020-01-10T00:00:00',
      hasta: '2020-01-11T00:00:00',
      metricas: ['n_viajes'],
    },
  },
  {
    titulo: 'Staten Island (Stapleton) por horas el 01/01 (enmascarado)',
    descripcion: 'Viajes por hora desde Stapleton (zona 221, Staten Island) el 01/01/2020: todos los grupos tienen menos de 10 viajes.',
    consulta: {
      nivel: 'hora_zona',
      fuente: 'historico',
      desde: '2020-01-01T00:00:00',
      hasta: '2020-01-02T00:00:00',
      zona_origen: 221,
      metricas: ['n_viajes'],
    },
  },
]
