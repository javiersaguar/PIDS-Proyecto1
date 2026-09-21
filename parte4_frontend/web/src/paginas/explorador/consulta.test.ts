import { describe, expect, it } from 'vitest'

import type { Consulta } from '@/api/tipos'

import {
  aConsulta,
  aFormulario,
  aParametros,
  describirConsulta,
  describirVentana,
  desdeParametros,
  EJEMPLOS,
  FORMULARIO_INICIAL,
  marcaDe,
  validar,
  type Formulario,
} from './consulta'

const FORMULARIO_HORAS: Formulario = {
  ...FORMULARIO_INICIAL,
  nivel: 'hora_zona',
  fechaDesde: '2020-01-15',
  fechaHasta: '2020-01-15',
  horaDesde: 8,
  horaHasta: 12,
  zonaOrigen: 132,
  barrioOrigen: 'Queens',
  metricas: ['importe_medio', 'n_viajes'],
}

describe('formulario ↔ consulta', () => {
  it('monta las fechas con la hora en punto y descarta los filtros que el nivel no admite', () => {
    expect(aConsulta(FORMULARIO_HORAS)).toEqual({
      nivel: 'hora_zona',
      fuente: 'historico',
      desde: '2020-01-15T08:00:00',
      hasta: '2020-01-15T12:00:00',
      metricas: ['n_viajes', 'importe_medio'],
      zona_origen: 132,
    })
  })

  it('en los niveles por día ignora las horas y la zona, y el destino solo en flujos', () => {
    const porDia = aConsulta({ ...FORMULARIO_HORAS, nivel: 'dia_barrio', barrioDestino: 'Manhattan' })
    expect(porDia).toEqual({
      nivel: 'dia_barrio',
      fuente: 'historico',
      desde: '2020-01-15T00:00:00',
      hasta: '2020-01-15T00:00:00',
      metricas: ['n_viajes', 'importe_medio'],
      barrio_origen: 'Queens',
    })
    const flujos = aConsulta({ ...FORMULARIO_HORAS, nivel: 'od_dia_barrio', fechaHasta: '2020-01-16', barrioDestino: 'Manhattan' })
    expect(flujos.barrio_destino).toBe('Manhattan')
    expect(flujos.zona_origen).toBeUndefined()
  })

  it('reconstruye el formulario desde una consulta (por ejemplo, una alternativa)', () => {
    const consulta: Consulta = {
      nivel: 'dia_barrio',
      fuente: 'historico',
      desde: '2020-01-01T00:00:00',
      hasta: '2020-01-02T00:00:00',
      metricas: ['n_viajes'],
      zona_origen: null,
      barrio_origen: 'Staten Island',
      barrio_destino: null,
    }
    expect(aFormulario(consulta)).toEqual({
      nivel: 'dia_barrio',
      fuente: 'historico',
      fechaDesde: '2020-01-01',
      fechaHasta: '2020-01-02',
      horaDesde: 0,
      horaHasta: 0,
      zonaOrigen: null,
      barrioOrigen: 'Staten Island',
      barrioDestino: null,
      metricas: ['n_viajes'],
    })
  })
})

describe('consulta ↔ URL', () => {
  it('serializa y vuelve a leer la misma consulta', () => {
    const consulta = aConsulta(FORMULARIO_HORAS)
    const parametros = aParametros(consulta)
    expect(parametros.toString()).toBe('nivel=hora_zona&fuente=historico&desde=2020-01-15T08%3A00%3A00&hasta=2020-01-15T12%3A00%3A00&metricas=n_viajes%2Cimporte_medio&zona_origen=132')
    expect(desdeParametros(parametros)).toEqual(consulta)
  })

  it('devuelve null si faltan el nivel o las fechas, o no son válidos', () => {
    expect(desdeParametros(new URLSearchParams(''))).toBeNull()
    expect(desdeParametros(new URLSearchParams('nivel=dia_barrio&desde=2020-01-01'))).toBeNull()
    expect(desdeParametros(new URLSearchParams('nivel=otro&desde=2020-01-01T00:00:00&hasta=2020-01-02T00:00:00'))).toBeNull()
    expect(desdeParametros(new URLSearchParams('nivel=dia_barrio&desde=2020-02-31T00:00:00&hasta=2020-03-02T00:00:00'))).toBeNull()
  })

  it('tolera fechas sin hora, métricas desconocidas y fuente ausente', () => {
    const consulta = desdeParametros(new URLSearchParams('nivel=dia_barrio&desde=2020-03-03&hasta=2020-03-04&metricas=propina_media,inventada&barrio_origen=Manhattan'))
    expect(consulta).toEqual({
      nivel: 'dia_barrio',
      fuente: 'historico',
      desde: '2020-03-03T00:00:00',
      hasta: '2020-03-04T00:00:00',
      metricas: ['n_viajes', 'propina_media'],
      barrio_origen: 'Manhattan',
    })
  })
})

describe('validar', () => {
  it('acepta una ventana correcta', () => {
    expect(validar(FORMULARIO_HORAS, 31)).toEqual({})
    expect(validar(FORMULARIO_INICIAL, 31)).toEqual({})
  })

  it('rechaza una ventana vacía o invertida (el fin no se incluye)', () => {
    expect(validar({ ...FORMULARIO_HORAS, horaHasta: 8 }).fechas).toMatch(/posterior/)
    expect(validar({ ...FORMULARIO_INICIAL, fechaHasta: '2020-01-01' }).fechas).toMatch(/día siguiente/)
    expect(validar({ ...FORMULARIO_INICIAL, fechaHasta: '2019-12-31' }).fechas).toBeDefined()
  })

  it('rechaza un rango mayor que el máximo del catálogo', () => {
    expect(validar({ ...FORMULARIO_INICIAL, fechaHasta: '2020-02-01' }, 31)).toEqual({})
    expect(validar({ ...FORMULARIO_INICIAL, fechaHasta: '2020-02-02' }, 31).rango).toBe(
      'El rango máximo por consulta es de 31 días (la ventana elegida tiene 32 días).',
    )
    expect(validar({ ...FORMULARIO_INICIAL, fechaHasta: '2020-01-09' }, 7).rango).toMatch(/7 días/)
  })

  it('avisa si alguna fecha está vacía', () => {
    expect(validar({ ...FORMULARIO_INICIAL, fechaDesde: '' }).fechas).toMatch(/válidas/)
  })
})

describe('descripciones', () => {
  it('describe la consulta en lenguaje natural como el chatbot', () => {
    expect(describirConsulta(aConsulta(FORMULARIO_HORAS), new Map([[132, 'JFK Airport']]))).toBe(
      'viajes por hora desde JFK Airport (zona 132) el 15/01/2020 de 08:00 a 12:00 con importe medio (histórico)',
    )
    expect(describirConsulta(aConsulta(FORMULARIO_HORAS))).toContain('desde la zona 132')
    expect(describirConsulta(EJEMPLOS[2].consulta)).toBe('flujos por día desde Queens hacia Manhattan el 10/01/2020 (histórico)')
    expect(
      describirConsulta({ nivel: 'dia_barrio', fuente: 'tiempo_real', desde: '2020-02-01T00:00:00', hasta: '2020-02-08T00:00:00', metricas: ['n_viajes', 'propina_media', 'importe_medio'] }),
    ).toBe('viajes por día del 01/02/2020 al 07/02/2020 con importe medio y propina media (tiempo real)')
    expect(describirConsulta({ nivel: 'hora_zona', desde: '2020-01-15T22:00:00', hasta: '2020-01-16T02:00:00' })).toBe(
      'viajes por hora del 15/01/2020 22:00 al 16/01/2020 02:00 (histórico)',
    )
  })

  it('describe la ventana con su duración', () => {
    expect(describirVentana({ desde: '2020-03-03T00:00:00', hasta: '2020-03-04T00:00:00' })).toBe('1 día (el 03/03/2020)')
    expect(describirVentana({ desde: '2020-01-15T08:00:00', hasta: '2020-01-15T12:00:00' })).toBe('4 horas (el 15/01/2020 de 08:00 a 12:00)')
    expect(describirVentana({ desde: '2020-02-01T00:00:00', hasta: '2020-02-08T00:00:00' })).toBe('7 días (del 01/02/2020 al 07/02/2020)')
    expect(describirVentana({ desde: '2020-02-01T00:00:00', hasta: '2020-02-01T00:00:00' })).toBe('ventana vacía')
  })

  it('interpreta las fechas ISO sin zona como UTC para la aritmética', () => {
    expect(marcaDe('2020-01-15T08:00:00')).toBe(Date.UTC(2020, 0, 15, 8))
    expect(marcaDe('2020-01-15')).toBe(Date.UTC(2020, 0, 15))
    expect(marcaDe('2020-01-15T24:00:00')).toBeNull()
    expect(marcaDe('')).toBeNull()
  })

  it('los ejemplos son consultas válidas', () => {
    for (const ejemplo of EJEMPLOS) {
      expect(validar(aFormulario(ejemplo.consulta))).toEqual({})
      expect(desdeParametros(aParametros(ejemplo.consulta))).toEqual({ ...ejemplo.consulta, metricas: ejemplo.consulta.metricas })
    }
  })
})
