import { describe, expect, it } from 'vitest'

import { SECCIONES, seccionSiguiente } from './navegacion'

describe('✋: siguiente sección del menú', () => {
  it('recorre las secciones en orden y vuelve a la primera tras la última', () => {
    const rutas = SECCIONES.map((s) => s.ruta)
    rutas.forEach((ruta, i) => expect(seccionSiguiente(ruta)).toBe(rutas[(i + 1) % rutas.length]))
    expect(seccionSiguiente(rutas.at(-1)!)).toBe('/')
  })

  it('desde una subruta cuenta su sección, y desde una ruta sin sección va a la primera', () => {
    expect(seccionSiguiente('/explorador/algo')).toBe('/tiempo-real')
    expect(seccionSiguiente('/no-existe')).toBe('/')
  })
})
