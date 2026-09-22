import { describe, expect, it } from 'vitest'

import {
  aIsoFecha,
  aIsoLocal,
  describirAntiguedad,
  formatearDecimal,
  formatearDistancia,
  formatearEntero,
  formatearFecha,
  formatearFechaCorta,
  formatearFechaHora,
  formatearHora,
  formatearImporte,
  formatearPorcentaje,
  formatearViajes,
  parsearFecha,
  pluralizar,
  SIN_DATO,
} from './formato'

describe('formato de cifras', () => {
  it('agrupa los millares con punto', () => {
    expect(formatearEntero(1234567)).toBe('1.234.567')
    expect(formatearEntero(1234)).toBe('1.234')
    expect(formatearEntero(999)).toBe('999')
    expect(formatearEntero(0)).toBe('0')
    expect(formatearEntero(-12345)).toBe('-12.345')
    expect(formatearEntero(203866)).toBe('203.866')
  })

  it('redondea al entero más próximo', () => {
    expect(formatearEntero(2.6)).toBe('3')
  })

  it('devuelve las cadenas tal cual (grupos enmascarados) y el guion cuando no hay valor', () => {
    expect(formatearEntero('oculto')).toBe('oculto')
    expect(formatearViajes('oculto')).toBe('oculto')
    expect(formatearViajes(7182)).toBe('7.182')
    expect(formatearEntero(null)).toBe(SIN_DATO)
    expect(formatearEntero(undefined)).toBe(SIN_DATO)
    expect(formatearEntero(Number.NaN)).toBe(SIN_DATO)
  })

  it('usa la coma decimal y agrupa la parte entera', () => {
    expect(formatearDecimal(2.07, 2)).toBe('2,07')
    expect(formatearDecimal(2.5)).toBe('2,50')
    expect(formatearDecimal(1234.5, 1)).toBe('1.234,5')
    expect(formatearDecimal(3, 0)).toBe('3')
    expect(formatearDecimal(-0.004, 2)).toBe('0,00')
    expect(formatearDecimal(null)).toBe(SIN_DATO)
  })

  it('formatea importes, porcentajes y distancias con su unidad', () => {
    expect(formatearImporte(2.07)).toBe('2,07 $')
    expect(formatearImporte(54.05)).toBe('54,05 $')
    expect(formatearImporte(null)).toBe(SIN_DATO)
    expect(formatearPorcentaje(35.4)).toBe('35,4 %')
    expect(formatearPorcentaje(78.07, 2)).toBe('78,07 %')
    expect(formatearPorcentaje(undefined)).toBe(SIN_DATO)
    expect(formatearDistancia(10.77)).toBe('10,77 mi')
  })

  it('pluraliza con la cifra formateada', () => {
    expect(pluralizar(1, 'fila')).toBe('1 fila')
    expect(pluralizar(2500, 'fila')).toBe('2.500 filas')
    expect(pluralizar(0, 'grupo enmascarado', 'grupos enmascarados')).toBe('0 grupos enmascarados')
  })
})

describe('formato de fechas', () => {
  it('interpreta el ISO sin zona como hora local, sin desplazarlo', () => {
    const fecha = parsearFecha('2020-01-15T08:00:00')
    expect(fecha).not.toBeNull()
    expect(fecha?.getHours()).toBe(8)
    expect(fecha?.getDate()).toBe(15)
    expect(parsearFecha('2020-03-03')?.getDate()).toBe(3)
    expect(parsearFecha('no es una fecha')).toBeNull()
    expect(parsearFecha(null)).toBeNull()
    expect(parsearFecha('')).toBeNull()
  })

  it('formatea fecha, hora y fecha-hora en español', () => {
    expect(formatearFecha('2020-01-15T08:00:00')).toBe('15/01/2020')
    expect(formatearFecha('2020-03-03')).toBe('03/03/2020')
    expect(formatearFechaCorta('2020-03-03T00:00:00')).toBe('03/03')
    expect(formatearHora('2020-01-15T08:00:00')).toBe('08:00')
    expect(formatearHora('2020-01-15T23:00:00')).toBe('23:00')
    expect(formatearFechaHora('2020-01-15T08:00:00')).toBe('15/01/2020 08:00')
    expect(formatearFecha(new Date(2020, 11, 30, 23, 0))).toBe('30/12/2020')
  })

  it('devuelve el guion si la fecha no es válida', () => {
    expect(formatearFecha('')).toBe(SIN_DATO)
    expect(formatearHora(null)).toBe(SIN_DATO)
    expect(formatearFechaHora('cualquier cosa')).toBe(SIN_DATO)
  })

  it('serializa a ISO local como espera la API', () => {
    expect(aIsoLocal(new Date(2020, 0, 15, 8, 0, 0))).toBe('2020-01-15T08:00:00')
    expect(aIsoFecha(new Date(2020, 0, 5))).toBe('2020-01-05')
  })
})

describe('describirAntiguedad', () => {
  it('elige la unidad según los segundos transcurridos', () => {
    expect(describirAntiguedad(0)).toBe('hace 0 s')
    expect(describirAntiguedad(45.7)).toBe('hace 45 s')
    expect(describirAntiguedad(60)).toBe('hace 1 min')
    expect(describirAntiguedad(200)).toBe('hace 3 min 20 s')
    expect(describirAntiguedad(3600)).toBe('hace 1 h')
    expect(describirAntiguedad(7500)).toBe('hace 2 h 5 min')
    expect(describirAntiguedad(3 * 86400 + 100)).toBe('hace 3 d')
  })

  it('no muestra valores negativos y trata el nulo como «sin dato»', () => {
    expect(describirAntiguedad(-5)).toBe('hace 0 s')
    expect(describirAntiguedad(null)).toBe('sin dato')
    expect(describirAntiguedad(undefined)).toBe('sin dato')
  })
})
