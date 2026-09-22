/**
 * Filtro de privacidad de la API de acceso (`parte2_plataforma/comun/privacidad.py`), portado para el modo
 * demostración: el portal publicado en Vercel no tiene API detrás y este módulo decide igual que ella qué consulta
 * se responde, cuál se rechaza y qué alternativa se propone. Las reglas se leen de `config/privacidad.json`, el mismo
 * fichero que usan la API y Spark, y `privacidad.test.ts` compara las decisiones con respuestas reales de la API.
 *
 * Solo decide y da forma: los datos que acaban en la respuesta son los que la API ya devolvió enmascarados.
 * Las fechas son ISO sin zona (`2020-01-15T08:00:00`) y se operan como milisegundos UTC.
 */
import reglas from '../../../../config/privacidad.json'

import type { Nivel } from '@/api/tipos'

export const REGLAS = reglas
export const K_MINIMO = reglas.k_minimo
export const MAX_FILAS = reglas.max_filas_por_respuesta
export const NOTA =
  'Los grupos enmascarados no se suman a ningún total: ocultarlos no serviría si se pudieran deducir por diferencia.'

/** Los de `privacidad.py`: la API no los lee de la configuración. */
export const BARRIOS = ['Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island', 'EWR', 'N/A', 'Unknown']
const NIVELES = Object.keys(reglas.niveles) as Nivel[]
const FUENTES = Object.keys(reglas.fuentes)

const HORA = 3_600_000
const DIA = 24 * HORA

/** La `Consulta` de la API ya validada, con sus valores por defecto (así la devuelve la API en `Respuesta.consulta`). */
export interface ConsultaApi {
  nivel: Nivel
  fuente: 'historico' | 'tiempo_real'
  desde: string
  hasta: string
  metricas: string[]
  zona_origen: number | null
  barrio_origen: string | null
  barrio_destino: string | null
  campos_extra: string[]
}

/** Un error de validación con la forma de los de FastAPI (`{"detail": [ErrorValidacion, …]}`). */
export interface ErrorValidacion {
  type: string
  loc: (string | number)[]
  msg: string
  input: unknown
}

export type Decision =
  | { resultado: 'permitida'; motivos: string[]; alternativa: null }
  | { resultado: 'rechazada'; motivos: string[]; alternativa: ConsultaApi }

// --- fechas ------------------------------------------------------------------------------------------------

const FECHA = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?)?$/

/** Milisegundos UTC de una fecha ISO sin zona, o null si no lo es. */
export function aMilisegundos(texto: unknown): number | null {
  const partes = typeof texto === 'string' ? FECHA.exec(texto.trim()) : null
  if (!partes) return null
  const [anio, mes, dia, hora = '0', minuto = '0', segundo = '0'] = partes.slice(1)
  const ms = Date.UTC(+anio, +mes - 1, +dia, +hora, +minuto, +segundo)
  const fecha = new Date(ms)
  // 2020-02-31 no es una fecha: Date.UTC la convertiría en el 2 de marzo
  if (fecha.getUTCMonth() !== +mes - 1 || fecha.getUTCDate() !== +dia || +hora > 23 || +minuto > 59 || +segundo > 59) {
    return null
  }
  return ms
}

/** `2020-01-15T08:00:00` */
export function aIso(ms: number): string {
  return new Date(ms).toISOString().slice(0, 19)
}

// --- validación (el modelo pydantic `Consulta`) --------------------------------------------------------------

function listaTolerante(valor: unknown): string[] {
  let lista: unknown[]
  if (valor === null || valor === undefined || valor === '') {
    lista = []
  } else if (typeof valor === 'string') {
    try {
      const cargado: unknown = JSON.parse(valor)
      lista = Array.isArray(cargado) ? cargado : [cargado]
    } catch {
      lista = valor.trim().replace(/^[[\]]+|[[\]]+$/g, '').split(',')
    }
  } else {
    lista = Array.isArray(valor) ? valor : [valor]
  }
  return lista.map((v) => String(v).trim().replace(/^['"]+|['"]+$/g, '')).filter(Boolean)
}

function barrio(valor: unknown): string | null {
  if (valor === null || valor === undefined) return null
  return String(valor).trim() || null
}

/** Valida el cuerpo como lo hace FastAPI con `Consulta`: la consulta normalizada o la lista de errores (422). */
export function validar(cuerpo: unknown): { consulta: ConsultaApi } | { errores: ErrorValidacion[] } {
  if (!cuerpo || typeof cuerpo !== 'object' || Array.isArray(cuerpo)) {
    return { errores: [{ type: 'model_attributes_type', loc: ['body'], msg: 'Input should be a valid dictionary', input: cuerpo }] }
  }
  const datos = cuerpo as Record<string, unknown>
  const errores: ErrorValidacion[] = []
  const error = (campo: string, type: string, msg: string) =>
    errores.push({ type, loc: ['body', campo], msg, input: datos[campo] })

  if (datos.nivel === undefined) error('nivel', 'missing', 'Field required')
  else if (!NIVELES.includes(datos.nivel as Nivel)) {
    error('nivel', 'literal_error', "Input should be 'hora_zona', 'dia_barrio' or 'od_dia_barrio'")
  }
  const fuente = datos.fuente ?? 'historico'
  if (!FUENTES.includes(fuente as string)) error('fuente', 'literal_error', "Input should be 'historico' or 'tiempo_real'")

  const fechas: Record<'desde' | 'hasta', number | null> = { desde: null, hasta: null }
  for (const campo of ['desde', 'hasta'] as const) {
    if (datos[campo] === undefined) error(campo, 'missing', 'Field required')
    else if ((fechas[campo] = aMilisegundos(datos[campo])) === null) {
      error(campo, 'datetime_from_date_parsing', 'Input should be a valid datetime or date')
    }
  }

  let zona: number | null = null
  const zonaPedida = datos.zona_origen
  if (!(zonaPedida === null || zonaPedida === undefined || zonaPedida === '' || zonaPedida === 'null' || zonaPedida === 'None')) {
    const numero = typeof zonaPedida === 'boolean' ? Number(zonaPedida) : Number(String(zonaPedida).trim())
    if (typeof zonaPedida === 'string' && !/^\s*[+-]?\d+\s*$/.test(zonaPedida)) {
      error('zona_origen', 'int_parsing', 'Input should be a valid integer, unable to parse string as an integer')
    } else if (!Number.isInteger(numero)) {
      error('zona_origen', 'int_from_float', 'Input should be a valid integer, got a number with a fractional part')
    } else {
      zona = numero
    }
  }

  if (errores.length) return { errores }
  const metricas = listaTolerante(datos.metricas)
  return {
    consulta: {
      nivel: datos.nivel as Nivel,
      fuente: fuente as ConsultaApi['fuente'],
      desde: aIso(fechas.desde!),
      hasta: aIso(fechas.hasta!),
      metricas: metricas.length ? metricas : ['n_viajes'],
      zona_origen: zona,
      barrio_origen: barrio(datos.barrio_origen),
      barrio_destino: barrio(datos.barrio_destino),
      campos_extra: listaTolerante(datos.campos_extra),
    },
  }
}

// --- decisión (`privacidad.evaluar`) ---------------------------------------------------------------------

function paso(nivel: Nivel): number {
  return reglas.niveles[nivel].tiempo === 'hora' ? HORA : DIA
}

function alinear(momento: number, intervalo: number, arriba: boolean): number {
  let base = Math.floor(momento / HORA) * HORA
  if (intervalo >= DIA) base = Math.floor(momento / DIA) * DIA
  if (arriba && base < momento) base += intervalo
  return base
}

/** `repr()` de Python para un texto, como en los motivos de la API. */
function repr(texto: string): string {
  if (texto.includes("'") && !texto.includes('"')) return `"${texto}"`
  return `'${texto.replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'`
}

/** Decide si la consulta se puede responder; `enmascarada` se decide después, al ver los datos. */
export function evaluar(consulta: ConsultaApi): Decision {
  const motivos: string[] = []
  const alt: ConsultaApi = { ...consulta, metricas: [...consulta.metricas], campos_extra: [] }
  const individuales = new Set(reglas.campos_individuales)

  const pedidosIndividuales = [...new Set(consulta.campos_extra.filter((c) => individuales.has(c)))].sort()
  if (pedidosIndividuales.length) motivos.push(`pide campos individuales: ${pedidosIndividuales.join(', ')}`)
  const desconocidos = [...new Set(consulta.campos_extra.filter((c) => !individuales.has(c)))].sort()
  if (desconocidos.length) motivos.push(`campos no publicados: ${desconocidos.join(', ')}`)

  const noPublicadas = consulta.metricas.filter((m) => !reglas.metricas.includes(m))
  if (noPublicadas.length) {
    motivos.push(`métricas no publicadas: ${noPublicadas.join(', ')}`)
    const publicadas = consulta.metricas.filter((m) => reglas.metricas.includes(m))
    alt.metricas = publicadas.length ? publicadas : ['n_viajes']
  }

  // primero el nivel al que hay que subir; después, los filtros que ese nivel no admite
  const dimensiones = reglas.niveles[consulta.nivel].dimensiones
  if (consulta.barrio_destino !== null && !dimensiones.includes('barrio_destino')) {
    motivos.push('el destino solo se publica por barrio y día (nivel od_dia_barrio)')
    alt.nivel = 'od_dia_barrio'
  } else if (consulta.barrio_origen !== null && !dimensiones.includes('barrio_origen')) {
    motivos.push(`el nivel ${consulta.nivel} no filtra por barrio; se usa dia_barrio`)
    alt.nivel = 'dia_barrio'
  }
  for (const campo of ['barrio_origen', 'barrio_destino'] as const) {
    const valor = consulta[campo]
    if (valor !== null && !BARRIOS.includes(valor)) {
      motivos.push(`${campo} desconocido: ${repr(valor)} (los barrios son: ${BARRIOS.slice(0, 6).join(', ')})`)
      alt[campo] = null
    }
  }

  if (consulta.zona_origen !== null && !reglas.niveles[alt.nivel].dimensiones.includes('zona_origen')) {
    motivos.push(`el nivel ${alt.nivel} no tiene zona; se agrega por barrio`)
    alt.zona_origen = null
  }

  const intervalo = paso(alt.nivel)
  const pedidoDesde = aMilisegundos(consulta.desde)!
  const pedidoHasta = aMilisegundos(consulta.hasta)!
  let altHasta = pedidoHasta
  if (pedidoHasta <= pedidoDesde) {
    motivos.push('la ventana temporal está vacía')
    altHasta = pedidoDesde + intervalo
  }
  const desde = alinear(pedidoDesde, intervalo, false)
  let hasta = alinear(altHasta, intervalo, true)
  if (hasta - desde < intervalo) hasta = desde + intervalo
  if (desde !== pedidoDesde || hasta !== pedidoHasta) {
    motivos.push(`la granularidad mínima es de ${intervalo === HORA ? 'una hora completa' : 'un día completo'}`)
  }
  const maximo = reglas.max_dias_por_consulta * DIA
  if (hasta - desde > maximo) {
    motivos.push(`el rango máximo por consulta es de ${reglas.max_dias_por_consulta} días`)
    hasta = desde + maximo
  }
  alt.desde = aIso(desde)
  alt.hasta = aIso(hasta)

  if (motivos.length) return { resultado: 'rechazada', motivos, alternativa: alt }
  return { resultado: 'permitida', motivos: [], alternativa: null }
}

// --- respuesta (`repositorio.proyeccion` y `privacidad.enmascarar`) ---------------------------------------------

export type FilaGuardada = Record<string, unknown>

/** Campo temporal del nivel (`hora` o `dia`). */
export function campoTiempo(nivel: Nivel): 'hora' | 'dia' {
  return nivel === 'hora_zona' ? 'hora' : 'dia'
}

/** ¿La fila cumple los filtros de la consulta (ventana y dimensiones)? Como `repositorio.filtro_mongo`. */
export function cumple(fila: FilaGuardada, consulta: ConsultaApi): boolean {
  const tiempo = String(fila[campoTiempo(consulta.nivel)])
  if (tiempo < consulta.desde || tiempo >= consulta.hasta) return false
  return (['zona_origen', 'barrio_origen', 'barrio_destino'] as const).every(
    (campo) => consulta[campo] === null || fila[campo] === consulta[campo],
  )
}

/** Solo los campos que la API proyecta para esta consulta. */
export function proyectar(fila: FilaGuardada, consulta: ConsultaApi): FilaGuardada {
  const extra = consulta.nivel === 'hora_zona' ? ['zona_origen_nombre', 'barrio_origen'] : []
  const campos = new Set([...reglas.niveles[consulta.nivel].dimensiones, ...extra, ...consulta.metricas, 'n_viajes', 'suprimido'])
  return Object.fromEntries(Object.entries(fila).filter(([campo, valor]) => campos.has(campo) && valor !== undefined))
}

/** Oculta las cifras de los grupos suprimidos: `n_viajes` pasa a `"oculto"` y el resto de métricas a null. */
export function enmascarar(filas: FilaGuardada[], metricas: string[]): { filas: FilaGuardada[]; ocultas: number } {
  let ocultas = 0
  const salida = filas.map((fila) => {
    if (!fila.suprimido) return fila
    ocultas += 1
    const oculta: FilaGuardada = { ...fila }
    for (const metrica of metricas) oculta[metrica] = null
    oculta.n_viajes = 'oculto'
    return oculta
  })
  return { filas: salida, ocultas }
}
