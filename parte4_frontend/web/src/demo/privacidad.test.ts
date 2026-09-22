/**
 * El modo demostración decide y responde como la API de acceso real: `referencias.json` guarda respuestas reales
 * de la API (código y cuerpo) a consultas permitidas, enmascaradas, rechazadas y mal formadas, grabadas por
 * `parte4_frontend/demo/instantanea.py` con la misma instantánea que usa la demo.
 */
import { Instantanea } from './datos'
import { validar } from './privacidad'
import { BffDemo, normalizar, type Contestacion } from './rutas'

interface Referencia {
  consulta: Record<string, unknown>
  estado: number
  cuerpo: Record<string, unknown>
}

const REFERENCIAS = Object.values(
  import.meta.glob<Referencia[]>('./referencias.json', { eager: true, import: 'default' }),
)[0]
const FICHEROS = import.meta.glob<unknown>('/public/demo/**/*.json', { import: 'default' })

function nuevaDemo(ahora = () => Date.parse('2026-09-21T18:00:00Z')) {
  const datos = new Instantanea((ruta) => {
    const cargar = FICHEROS[`/public/demo/${ruta}`]
    if (!cargar) throw new Error(`falta ${ruta} en la instantánea`)
    return cargar()
  })
  return new BffDemo(datos, ahora)
}

function cuerpo(contestacion: Contestacion): Record<string, unknown> {
  if (contestacion.tipo !== 'json') throw new Error('se esperaba JSON')
  return contestacion.cuerpo as Record<string, unknown>
}

/** Las filas como conjunto: la API no garantiza el orden dentro de la misma hora o el mismo día. */
function comoConjunto(filas: unknown): string[] {
  return (filas as Record<string, unknown>[])
    .map((fila) => JSON.stringify(Object.fromEntries(Object.entries(fila).sort(([a], [b]) => a.localeCompare(b)))))
    .sort()
}

describe('filtro de privacidad de la demostración frente a la API real', () => {
  it('hay referencias de todos los tipos', () => {
    const estados = new Set(REFERENCIAS.map((r) => r.estado))
    expect([...estados].sort()).toEqual([200, 403, 422])
    expect(REFERENCIAS.some((r) => r.estado === 200 && r.cuerpo.resultado === 'enmascarada')).toBe(true)
  })

  it.each(REFERENCIAS.map((r) => [JSON.stringify(r.consulta), r] as const))('%s', async (_, referencia) => {
    const contestacion = await nuevaDemo().consultar(referencia.consulta)
    expect(contestacion.tipo === 'json' && contestacion.estado).toBe(referencia.estado)
    const obtenido = cuerpo(contestacion)
    if (referencia.estado === 403) {
      expect(obtenido).toEqual(referencia.cuerpo)
    } else if (referencia.estado === 422) {
      const campos = (c: Record<string, unknown>) => (c.detail as { loc: unknown[] }[]).map((e) => e.loc.join('.')).sort()
      expect(campos(obtenido)).toEqual(campos(referencia.cuerpo))
    } else {
      const { filas, ...resto } = referencia.cuerpo
      const { filas: filasDemo, ...restoDemo } = obtenido
      expect(restoDemo).toEqual(resto)
      expect(comoConjunto(filasDemo)).toEqual(comoConjunto(filas))
    }
  })
})

describe('validación de la consulta', () => {
  it('acepta las formas tolerantes de la API', () => {
    const validada = validar({ nivel: 'hora_zona', desde: '2020-01-15', hasta: '2020-01-15 09:00', zona_origen: ' 132 ',
      metricas: 'n_viajes, propina_media', barrio_origen: '' })
    expect(validada).toEqual({ consulta: {
      nivel: 'hora_zona', fuente: 'historico', desde: '2020-01-15T00:00:00', hasta: '2020-01-15T09:00:00',
      metricas: ['n_viajes', 'propina_media'], zona_origen: 132, barrio_origen: null, barrio_destino: null, campos_extra: [],
    } })
  })

  it('rechaza fechas imposibles y zonas que no son números', () => {
    const validada = validar({ nivel: 'dia_barrio', desde: '2020-02-31', hasta: '2020-03-01', zona_origen: 'JFK' })
    expect('errores' in validada && validada.errores.map((e) => e.loc[1])).toEqual(['desde', 'zona_origen'])
  })
})

describe('resto del BFF de la demostración', () => {
  const peticion = (metodo: string, ruta: string, cuerpo: unknown = null) => {
    const url = new URL(ruta, 'http://demo')
    return { metodo, ruta: url.pathname, parametros: url.searchParams, cuerpo }
  }

  it('el panel suma solo los grupos visibles del último día', async () => {
    const panel = cuerpo(await nuevaDemo().atender(peticion('GET', '/api/panel')))
    const ultimo = (panel.ultimo_dia as Record<string, { dia: string; total: number; por_barrio: Record<string, number> }>)
    expect(ultimo.historico.dia).toBe('2020-12-31T00:00:00')
    expect(ultimo.tiempo_real.dia).toBe('2020-03-03T00:00:00')
    expect(ultimo.historico.total).toBe(Object.values(ultimo.historico.por_barrio).reduce((a, b) => a + b, 0))
    expect(panel.frescura_tiempo_real).toEqual({ instante: '2026-09-21T17:59:32.400Z', segundos: 27.6 })
  })

  it('el tiempo real devuelve las últimas horas pedidas del día reproducido', async () => {
    const tiempoReal = cuerpo(await nuevaDemo().atender(peticion('GET', '/api/tiempo-real?horas=6')))
    const horas = (tiempoReal.por_hora as { hora: string }[]).map((h) => h.hora)
    expect(horas).toEqual(['18', '19', '20', '21', '22', '23'].map((h) => `2020-03-03T${h}:00:00`))
    expect((tiempoReal.por_zona_ultima_hora as { hora: string }[]).every((f) => f.hora === '2020-03-03T23:00:00')).toBe(true)
    const invalida = await nuevaDemo().atender(peticion('GET', '/api/tiempo-real?horas=0'))
    expect(invalida.tipo === 'json' && invalida.estado).toBe(422)
  })

  it('el asistente reproduce la conversación grabada y su alternativa', async () => {
    const demo = nuevaDemo()
    const { id } = cuerpo(await demo.atender(peticion('POST', '/api/chat/sesiones', { motor: 'ollama' }))) as { id: string }
    const texto = 'dame el viaje de las 3:12 del 15 de enero desde times square'
    const rechazo = await demo.atender(peticion('POST', `/api/chat/sesiones/${id}/mensajes`, { texto }))
    expect(rechazo.tipo === 'sse' && rechazo.eventos.at(-1)?.datos.bloqueo).toBe('filtro_previo')
    const alternativa = await demo.atender(peticion('POST', `/api/chat/sesiones/${id}/alternativa`))
    expect(alternativa.tipo === 'sse' && alternativa.eventos.at(-1)?.evento).toBe('respuesta')
    const repetida = await demo.atender(peticion('POST', `/api/chat/sesiones/${id}/alternativa`))
    expect(repetida.tipo === 'json' && repetida.estado).toBe(400)
  })

  it('a una pregunta no grabada contesta con las de ejemplo, sin inventar cifras', async () => {
    const demo = nuevaDemo()
    const { id } = cuerpo(await demo.atender(peticion('POST', '/api/chat/sesiones', { motor: 'ollama' }))) as { id: string }
    const respuesta = await demo.atender(peticion('POST', `/api/chat/sesiones/${id}/mensajes`, { texto: '¿Y en Brooklyn?' }))
    const texto = respuesta.tipo === 'sse' ? String(respuesta.eventos[0].datos.respuesta) : ''
    expect(texto).toContain('demostración pública')
    expect(texto).not.toMatch(/\d{3,}/)
    expect(normalizar('¿Qué barrio tuvo MÁS viajes?')).toBe('que barrio tuvo mas viajes')
  })

  it('«Capturar datos» anima el flujo con un reloj de 2020 que avanza, sin enviar nada', async () => {
    let ahora = Date.parse('2026-09-22T12:00:00Z')
    const demo = nuevaDemo(() => ahora)
    const info = cuerpo(await demo.atender(peticion('GET', '/api/operaciones/captura')))
    expect(info).toMatchObject({ disponible: true, demostracion: true, reloj: '2020-12-01T00:00:00' })
    const inicial = await demo.atender(peticion('POST', '/api/operaciones/captura', { velocidad: 60 }))
    expect(inicial.tipo === 'json' && inicial.estado).toBe(202)
    ahora += 90_000                                                  // minuto y medio: hora y media de 2020
    const estado = cuerpo(await demo.atender(peticion('GET', '/api/operaciones/simulacion')))
    expect(estado).toMatchObject({ activa: true, modo: 'directo', reloj: '2020-12-01T01:30:00', enviados: 2970, total: 0 })
    const repetida = await demo.atender(peticion('POST', '/api/operaciones/captura', { velocidad: 60 }))
    expect(repetida.tipo === 'json' && repetida.estado).toBe(409)
    expect(cuerpo(await demo.atender(peticion('DELETE', '/api/operaciones/captura'))).activa).toBe(false)
    // la siguiente sigue donde se quedó
    expect(cuerpo(await demo.atender(peticion('GET', '/api/operaciones/captura'))).reloj).toBe('2020-12-01T01:30:00')
  })

  it('las operaciones se enseñan pero no se lanzan, y el motor RAG no está disponible', async () => {
    const demo = nuevaDemo()
    const carga = await demo.atender(peticion('POST', '/api/operaciones/airflow/cargas', { mes: '2020-01', muestra: true }))
    expect(carga.tipo === 'json' && carga.estado).toBe(503)
    const rag = await demo.atender(peticion('POST', '/api/chat/sesiones', { motor: 'rag' }))
    expect(rag.tipo === 'json' && rag.estado).toBe(409)
  })

  it('los cuadros de observabilidad son los grabados, con sus datos, y solo los ocho de Grafana', async () => {
    const demo = nuevaDemo()
    const lista = cuerpo(await demo.atender(peticion('GET', '/api/observabilidad/cuadros'))) as unknown as { uid: string }[]
    expect(lista.map((c) => c.uid)).toContain('pids-plataforma')
    expect(lista).toHaveLength(8)
    const cuadro = cuerpo(await demo.atender(peticion('GET', '/api/observabilidad/cuadros/pids-spark')))
    expect(cuadro).toMatchObject({ uid: 'pids-spark', disponible: true })
    expect(cuadro.grabado).toEqual(expect.any(String))
    const otro = await demo.atender(peticion('GET', '/api/observabilidad/cuadros/..%2Fpanel'))
    expect(otro.tipo === 'json' && otro.estado).toBe(404)
  })

  it('cerrar la sesión exige volver a entrar; cualquier contraseña vale', async () => {
    const demo = nuevaDemo()
    await demo.atender(peticion('DELETE', '/api/sesion'))
    const sinSesion = await demo.atender(peticion('GET', '/api/panel'))
    expect(sinSesion.tipo === 'json' && sinSesion.estado).toBe(401)
    expect(cuerpo(await demo.atender(peticion('GET', '/api/sesion')))).toEqual({ autenticado: false })
    await demo.atender(peticion('POST', '/api/sesion', { clave: 'cualquiera' }))
    expect(cuerpo(await demo.atender(peticion('GET', '/api/sesion')))).toEqual({ autenticado: true })
  })
})
