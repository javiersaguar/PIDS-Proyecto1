import { describe, expect, it } from 'vitest'

import { acercarHacia, esRuedaDeRaton, VISTA_INICIAL, ZOOM_MAXIMO, ZOOM_MINIMO } from './zoom'

describe('zoom del grafo', () => {
  it('el punto bajo el cursor se queda quieto al acercar o alejar', () => {
    const vista = { zoom: 1.2, x: 30, y: -10 }
    const cursor = { x: 200, y: 80 }
    // un punto del lienzo (en unidades sin escalar) que está justo debajo del cursor
    const local = { x: (cursor.x - vista.x) / vista.zoom, y: (cursor.y - vista.y) / vista.zoom }
    for (const factor of [1.5, 0.7]) {
      const nueva = acercarHacia(vista, factor, cursor)
      expect(nueva.x + local.x * nueva.zoom).toBeCloseTo(cursor.x)
      expect(nueva.y + local.y * nueva.zoom).toBeCloseTo(cursor.y)
    }
  })

  it('no pasa de los límites y los botones acercan hacia el centro', () => {
    expect(acercarHacia(VISTA_INICIAL, 100).zoom).toBe(ZOOM_MAXIMO)
    expect(acercarHacia(VISTA_INICIAL, 0.01).zoom).toBe(ZOOM_MINIMO)
    expect(acercarHacia({ zoom: 1, x: 40, y: 20 }, 2)).toEqual({ zoom: 2, x: 80, y: 40 })
  })

  it('distingue la rueda del ratón del desplazamiento con dos dedos del panel táctil', () => {
    expect(esRuedaDeRaton({ deltaMode: 0, deltaX: 0, deltaY: 100 })).toBe(true)
    expect(esRuedaDeRaton({ deltaMode: 1, deltaX: 0, deltaY: 3 })).toBe(true)          // Firefox: líneas
    expect(esRuedaDeRaton({ deltaMode: 0, deltaX: 0, deltaY: 4.5 })).toBe(false)       // panel táctil
    expect(esRuedaDeRaton({ deltaMode: 0, deltaX: 12, deltaY: 60 })).toBe(false)       // con componente horizontal
  })
})
