/**
 * El BFF del modo demostración: responde a cada ruta de `/api` (CONTRATOS.md §5) con la instantánea grabada, con
 * las mismas formas y los mismos códigos que el BFF real. Lógica pura sobre `Instantanea`: se prueba sin navegador.
 *
 * Lo que cambia respecto al portal real:
 *   - la sesión se abre sola (y el formulario de acceso acepta cualquier contraseña);
 *   - las consultas pasan por el filtro de privacidad portado (`privacidad.ts`) y se responden con los agregados
 *     grabados, que ya salieron enmascarados de la API;
 *   - el «tiempo real» reproduce un día histórico y la frescura es la mediana medida (M3);
 *   - el asistente reproduce conversaciones grabadas del agente real; a otras preguntas contesta con las de ejemplo;
 *   - las operaciones (cargas en Airflow, simulador) se enseñan, pero no se lanzan;
 *   - «Capturar datos» (captura en directo del grafo) anima el flujo con un reloj de 2020 que avanza, pero no envía
 *     nada ni cambia el tiempo real grabado.
 */
import type { Catalogo, EstadoSesion, Zona } from '@/api/tipos'

import { type Instantanea, notaIncompleta } from './datos'
import {
  aIso, aMilisegundos, campoTiempo, cumple, enmascarar, evaluar, type FilaGuardada, K_MINIMO, MAX_FILAS, NOTA,
  proyectar, validar,
} from './privacidad'

export interface Peticion {
  metodo: string
  ruta: string
  parametros: URLSearchParams
  cuerpo: unknown
}

export type EventoSse = { evento: 'paso' | 'respuesta' | 'error'; datos: Record<string, unknown> }

export type Contestacion =
  | { tipo: 'json'; estado: number; cuerpo?: unknown }
  | { tipo: 'sse'; eventos: EventoSse[] }

interface Conversacion {
  pregunta: string
  eventos: EventoSse[]
  alternativa: EventoSse[] | null
}

interface Chat {
  motores: { id: string; disponible: boolean }[]
  conversaciones: Conversacion[]
}

interface Auditoria {
  resumenes: Record<string, Record<string, unknown>>
  decisiones: { instante: string; resultado: string; cliente: string }[]
  cargas: unknown[]
}

export const MENSAJE_OPERACIONES =
  'En la demostración pública no se lanzan operaciones: en el portal del equipo este botón pone en marcha el trabajo ' +
  'de verdad (Airflow y Spark, o el simulador contra la API de captura).'

const HORA = 3_600_000
const DIA = 24 * HORA
const FRESCURA_S = 27.6            // mediana medida de la latencia del tiempo real (docs/metricas_calidad.md, M3)
const MAX_HORAS_TIEMPO_REAL = 48

const json = (cuerpo: unknown, estado = 200): Contestacion => ({ tipo: 'json', estado, cuerpo })
const detalle = (estado: number, texto: string): Contestacion => json({ detail: texto }, estado)
const vacia = (): Contestacion => ({ tipo: 'json', estado: 204 })

/** Minúsculas, sin tildes ni signos: para reconocer una pregunta grabada aunque cambie la puntuación. */
export function normalizar(texto: string): string {
  return texto.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase().replace(/[^a-z0-9ñ]+/g, ' ').trim()
}

function visible(fila: FilaGuardada): boolean {
  return !fila.suprimido && typeof fila.n_viajes === 'number'
}

/** `UltimoDia` como `servicios/acceso.resumir_dia` del BFF: se suman solo los grupos visibles. */
function resumirDia(dia: string, filas: FilaGuardada[]) {
  const porBarrio: Record<string, number> = {}
  let enmascarados = 0
  for (const fila of filas) {
    if (visible(fila)) {
      const barrio = String(fila.barrio_origen || 'desconocido')
      porBarrio[barrio] = (porBarrio[barrio] ?? 0) + (fila.n_viajes as number)
    } else {
      enmascarados += 1
    }
  }
  const total = Object.values(porBarrio).reduce((a, b) => a + b, 0)
  return { dia, por_barrio: porBarrio, total, grupos_enmascarados: enmascarados }
}

export class BffDemo {
  private readonly datos: Instantanea
  private readonly ahora: () => number
  private autenticado = true
  private siguienteSesion = 1
  private readonly alternativas = new Map<string, EventoSse[] | null>()
  /** La captura en directo de la demostración: solo su reloj, para animar el grafo. */
  private captura: { inicio: number; desde: number; velocidad: number } | null = null
  private relojCaptura = Date.UTC(2020, 11, 1)

  constructor(datos: Instantanea, ahora: () => number = Date.now) {
    this.datos = datos
    this.ahora = ahora
  }

  async atender(p: Peticion): Promise<Contestacion> {
    const { metodo, ruta } = p
    if (ruta === '/api/salud') return json({ estado: 'ok' })
    if (ruta === '/api/sesion') return this.sesion(metodo)
    if (!this.autenticado) return detalle(401, 'Sesión no iniciada')

    if (metodo === 'GET' && ruta === '/api/catalogo') return json(await this.datos.leer<Catalogo>('catalogo.json'))
    if (metodo === 'GET' && ruta === '/api/zonas') return json(await this.zonas(p.parametros.get('texto')))
    if (metodo === 'POST' && ruta === '/api/consultas') return this.consultar(p.cuerpo)
    if (metodo === 'GET' && ruta === '/api/panel') return json(await this.panel())
    if (metodo === 'GET' && ruta === '/api/tiempo-real') return this.tiempoReal(p.parametros.get('horas'))
    if (ruta.startsWith('/api/auditoria/')) return this.auditoria(ruta, p.parametros)
    if (ruta.startsWith('/api/operaciones/')) return this.operaciones(metodo, ruta, p.cuerpo)
    if (ruta.startsWith('/api/chat/')) return this.chat(metodo, ruta, p.cuerpo)
    return detalle(404, 'Not Found')
  }

  private sesion(metodo: string): Contestacion {
    if (metodo === 'GET') return json({ autenticado: this.autenticado } satisfies EstadoSesion)
    this.autenticado = metodo === 'POST'
    return vacia()
  }

  private async zonas(texto: string | null): Promise<Zona[]> {
    const zonas = await this.datos.zonas()
    const buscado = (texto ?? '').trim().slice(0, 50)
    if (!buscado) return zonas.slice(0, 300)
    let patron: RegExp
    try {
      patron = new RegExp(buscado, 'i')                 // la API busca con una expresión regular de MongoDB
    } catch {
      patron = new RegExp(buscado.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i')
    }
    return zonas.filter((z) => patron.test(z.nombre)).slice(0, 300)
  }

  // --- explorador -----------------------------------------------------------------------------------------

  async consultar(cuerpo: unknown): Promise<Contestacion> {
    const validada = validar(cuerpo)
    if ('errores' in validada) return json({ detail: validada.errores }, 422)
    const consulta = validada.consulta
    const decision = evaluar(consulta)
    if (decision.resultado === 'rechazada') return json(decision, 403)

    const { filas: candidatas, incompleta } = await this.datos.candidatas(consulta)
    const tiempo = campoTiempo(consulta.nivel)
    const encontradas = candidatas
      .filter((fila) => cumple(fila, consulta))
      .sort((a, b) => (String(a[tiempo]) < String(b[tiempo]) ? -1 : String(a[tiempo]) > String(b[tiempo]) ? 1 : 0))
      .slice(0, MAX_FILAS + 1)
    const truncada = encontradas.length > MAX_FILAS
    const { filas, ocultas } = enmascarar(
      encontradas.slice(0, MAX_FILAS).map((fila) => proyectar(fila, consulta)),
      consulta.metricas.filter((m) => m !== 'n_viajes'),
    )
    const nota = incompleta ? `${NOTA} ${notaIncompleta(await this.datos.manifiesto())}` : NOTA
    return json({
      resultado: ocultas ? 'enmascarada' : 'permitida', consulta, filas, grupos_enmascarados: ocultas, truncada, nota,
    })
  }

  /** Las filas de una consulta interna del portal (panel y tiempo real), que siempre se permite. */
  private async filas(cuerpo: Record<string, unknown>): Promise<FilaGuardada[]> {
    const contestacion = await this.consultar(cuerpo)
    if (contestacion.tipo !== 'json' || contestacion.estado !== 200) return []
    return (contestacion.cuerpo as { filas: FilaGuardada[] }).filas
  }

  // --- panel y tiempo real ---------------------------------------------------------------------------------

  private frescura() {
    return { instante: new Date(this.ahora() - FRESCURA_S * 1000).toISOString(), segundos: FRESCURA_S }
  }

  private async ultimoDia(fuente: 'historico' | 'tiempo_real') {
    const { dia_tiempo_real: diaTiempoReal } = await this.datos.manifiesto()
    const desde = fuente === 'historico' ? aMilisegundos('2020-12-01')! : aMilisegundos(diaTiempoReal)!
    const hasta = fuente === 'historico' ? aMilisegundos('2021-01-01')! : desde + DIA
    const filas = await this.filas({ nivel: 'dia_barrio', fuente, desde: aIso(desde), hasta: aIso(hasta) })
    if (!filas.length) return null
    const ultimo = filas.map((f) => String(f.dia)).sort().at(-1)!
    return resumirDia(ultimo, filas.filter((f) => f.dia === ultimo))
  }

  private async panel() {
    const panel = await this.datos.leer<Record<string, unknown>>('panel.json')
    const [historico, tiempoReal] = await Promise.all([this.ultimoDia('historico'), this.ultimoDia('tiempo_real')])
    return {
      ultimo_dia: { historico, tiempo_real: tiempoReal },
      frescura_tiempo_real: this.frescura(),
      consultas_24h: panel.consultas_24h,
      servicios: panel.servicios,
      enlaces: panel.enlaces,
      prometheus_disponible: true,
      acceso_disponible: true,
    }
  }

  private async tiempoReal(horasTexto: string | null): Promise<Contestacion> {
    const horas = horasTexto === null ? 6 : Number(horasTexto)
    if (!Number.isInteger(horas) || horas < 1 || horas > MAX_HORAS_TIEMPO_REAL) {
      return json({ detail: [{ type: 'less_than_equal', loc: ['query', 'horas'], msg: `Input should be between 1 and ${MAX_HORAS_TIEMPO_REAL}`, input: horasTexto }] }, 422)
    }
    const { dia_tiempo_real: dia } = await this.datos.manifiesto()
    const porHora = new Map<string, FilaGuardada[]>()
    for (let h = 0, inicio = aMilisegundos(dia)!; h < 24; h += 1) {
      const desde = aIso(inicio + h * HORA)
      const filas = await this.filas({ nivel: 'hora_zona', fuente: 'tiempo_real', desde, hasta: aIso(inicio + (h + 1) * HORA) })
      if (filas.length) porHora.set(desde, filas)
    }
    const ultimas = [...porHora.keys()].sort().slice(-horas)
    const ultimo = await this.ultimoDia('tiempo_real')
    return json({
      frescura: this.frescura(),
      ultimo_dia: ultimo?.dia ?? null,
      por_hora: ultimas.map((hora) => {
        const filas = porHora.get(hora)!
        const visibles = filas.filter(visible)
        return {
          hora,
          n_viajes: visibles.reduce((suma, f) => suma + (f.n_viajes as number), 0),
          grupos: filas.length,
          grupos_enmascarados: filas.length - visibles.length,
        }
      }),
      por_zona_ultima_hora: ultimas.length ? porHora.get(ultimas.at(-1)!) : [],
      acceso_disponible: true,
    })
  }

  // --- auditoría ---------------------------------------------------------------------------------------------

  private async auditoria(ruta: string, parametros: URLSearchParams): Promise<Contestacion> {
    const [auditoria, { generado }] = await Promise.all([this.datos.leer<Auditoria>('auditoria.json'), this.datos.manifiesto()])
    const hasta = Date.parse(generado)
    const horas = Number(parametros.get('horas') ?? 24)
    if (ruta === '/api/auditoria/cargas') return json(auditoria.cargas)
    if (!Number.isFinite(horas) || horas <= 0) return detalle(422, 'horas no válidas')
    if (ruta === '/api/auditoria/resumen') {
      const claves = Object.keys(auditoria.resumenes).map(Number).sort((a, b) => a - b)
      const clave = claves.find((c) => c >= horas) ?? claves.at(-1)!
      return json({
        desde: new Date(hasta - horas * HORA).toISOString(), hasta: new Date(hasta).toISOString(),
        ...auditoria.resumenes[String(clave)], disponible: true,
      })
    }
    if (ruta === '/api/auditoria/decisiones') {
      const resultado = parametros.get('resultado')
      const cliente = parametros.get('cliente')
      const limite = Math.min(Number(parametros.get('limite') ?? 100) || 100, 500)
      return json(auditoria.decisiones
        .filter((d) => Date.parse(d.instante) >= hasta - horas * HORA)
        .filter((d) => (!resultado || d.resultado === resultado) && (!cliente || d.cliente === cliente))
        .slice(0, limite))
    }
    return detalle(404, 'Not Found')
  }

  // --- operaciones -------------------------------------------------------------------------------------------

  private async operaciones(metodo: string, ruta: string, cuerpo: unknown = null): Promise<Contestacion> {
    const operaciones = await this.datos.leer<{ ejecuciones: unknown[]; ficheros: string[] }>('operaciones.json')
    if (ruta === '/api/operaciones/airflow/ejecuciones' && metodo === 'GET') return json(operaciones.ejecuciones)
    if (ruta === '/api/operaciones/simulacion/ficheros' && metodo === 'GET') return json(operaciones.ficheros)
    if (ruta === '/api/operaciones/simulacion' && metodo === 'GET') return json(this.estadoCaptura())
    if (ruta === '/api/operaciones/captura' && metodo === 'GET') {
      return json({
        disponible: true, primer_dia: '2020-12-01', ultimo_dia: '2020-12-31', reloj: this.captura ? null : aIso(this.relojCaptura),
        velocidad_por_defecto: 60, velocidad_maxima: 600, demostracion: true,
      })
    }
    if (ruta === '/api/operaciones/captura' && metodo === 'POST') {
      if (this.captura) return detalle(409, 'Ya hay una simulación en marcha; párala antes de capturar')
      const velocidad = Number((cuerpo as { velocidad?: unknown } | null)?.velocidad ?? 60)
      this.captura = { inicio: this.ahora(), desde: this.relojCaptura, velocidad: Math.min(600, Math.max(1, velocidad || 60)) }
      return json(this.estadoCaptura(), 202)
    }
    if ((ruta === '/api/operaciones/simulacion' || ruta === '/api/operaciones/captura') && metodo === 'DELETE') {
      const estado = this.estadoCaptura()
      if (this.captura) this.relojCaptura = this.relojActual()
      this.captura = null
      return json({ ...estado, activa: false, fin: new Date(this.ahora()).toISOString() })
    }
    if (metodo === 'POST') return detalle(503, MENSAJE_OPERACIONES)
    return detalle(404, 'Not Found')
  }

  /** Hora de 2020 por la que va la captura de la demostración (sin pasar del 31/12). */
  private relojActual(): number {
    if (!this.captura) return this.relojCaptura
    const avanzado = this.captura.desde + (this.ahora() - this.captura.inicio) * this.captura.velocidad
    return Math.min(avanzado, Date.UTC(2021, 0, 1) - 1000)
  }

  /** La `Simulacion` del contrato: parada, o la captura en directo con un ritmo aproximado al de diciembre de 2020. */
  private estadoCaptura() {
    if (!this.captura) {
      return { activa: false, lote: null, fichero: null, enviados: 0, total: 0, ritmo: 50, inicio: null, fin: null, error: null }
    }
    const segundos = (this.ahora() - this.captura.inicio) / 1000
    const ritmo = Math.round(this.captura.velocidad * 0.55 * 10) / 10     // ~2000 viajes por hora de 2020
    return {
      activa: true, lote: 'demostracion', fichero: null, enviados: Math.floor(segundos * ritmo), total: 0, ritmo,
      inicio: new Date(this.captura.inicio).toISOString(), fin: null, error: null,
      modo: 'directo', reloj: aIso(this.relojActual()), velocidad: this.captura.velocidad,
    }
  }

  // --- asistente ---------------------------------------------------------------------------------------------

  private async chat(metodo: string, ruta: string, cuerpo: unknown): Promise<Contestacion> {
    const chat = await this.datos.leer<Chat>('chat.json')
    if (ruta === '/api/chat/motores' && metodo === 'GET') return json(chat.motores)
    if (ruta === '/api/chat/sesiones' && metodo === 'POST') {
      const motor = (cuerpo as { motor?: unknown } | null)?.motor
      const elegido = chat.motores.find((m) => m.id === motor)
      if (!elegido) return detalle(422, 'Motor desconocido')
      if (!elegido.disponible) return detalle(409, 'Este motor no está disponible en la demostración pública')
      const id = `demo-${this.siguienteSesion++}`
      this.alternativas.set(id, null)
      return json({ id, motor: elegido.id }, 201)
    }
    const partes = /^\/api\/chat\/sesiones\/([^/]+)(\/mensajes|\/alternativa)?$/.exec(ruta)
    if (!partes) return detalle(404, 'Not Found')
    const [, id, accion] = partes
    if (!this.alternativas.has(id)) return detalle(404, 'La sesión no existe o ha caducado')
    if (metodo === 'DELETE' && !accion) {
      this.alternativas.delete(id)
      return vacia()
    }
    if (metodo === 'POST' && accion === '/alternativa') {
      const pendiente = this.alternativas.get(id)
      if (!pendiente) return detalle(400, 'No hay ninguna alternativa pendiente')
      this.alternativas.set(id, null)
      return { tipo: 'sse', eventos: pendiente }
    }
    if (metodo === 'POST' && accion === '/mensajes') {
      const texto = String((cuerpo as { texto?: unknown } | null)?.texto ?? '').trim()
      if (!texto) return detalle(400, 'El mensaje está vacío')
      const grabada = chat.conversaciones.find((c) => normalizar(c.pregunta) === normalizar(texto))
      this.alternativas.set(id, grabada?.alternativa ?? null)
      return { tipo: 'sse', eventos: grabada ? grabada.eventos : [this.sinGrabar(chat)] }
    }
    return detalle(405, 'Method Not Allowed')
  }

  private sinGrabar(chat: Chat): EventoSse {
    const ejemplos = chat.conversaciones.map((c) => `- ${c.pregunta}`).join('\n')
    return {
      evento: 'respuesta',
      datos: {
        respuesta:
          'Esta es la **demostración pública** del portal: aquí el asistente no está conectado a ningún modelo y solo ' +
          'reproduce respuestas grabadas del agente real, que corre con Ollama en el equipo del grupo. Prueba con una ' +
          `de estas preguntas:\n\n${ejemplos}\n\n_Las barreras de privacidad (k = ${K_MINIMO}, sin viajes individuales) ` +
          'son las mismas en las respuestas grabadas._',
        bloqueo: null, pasos_llm: 0, segundos: 0, tokens: null, alternativa: null, alternativa_descripcion: null, fuentes: [],
      },
    }
  }
}
