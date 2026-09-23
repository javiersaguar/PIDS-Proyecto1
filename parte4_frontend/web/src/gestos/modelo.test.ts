/**
 * El MLP de la parte 1 en TypeScript predice lo mismo que en Python: `muestras.json` son imágenes reales del dataset
 * (sus 21 puntos de MediaPipe) con las probabilidades que da `parte1_gestos/entrenamiento/exportar_web.py`.
 */
import { describe, expect, it } from 'vitest'

import { FiltroGestos } from './filtro'
import { entradaDesde, predecir, probabilidades, type ModeloGestos } from './modelo'
import muestras from './muestras.json'
import { GESTOS, LISTA_GESTOS, PREGUNTAS_GESTO } from './tabla'

const MODELO = Object.values(
  import.meta.glob<ModeloGestos>('/public/gestos/modelo.json', { eager: true, import: 'default' }),
)[0]

type Punto = [number, number]

describe('MLP de la parte 1 en el navegador', () => {
  it('es el modelo exportado: 42 entradas, las seis clases y su acierto en LOPO', () => {
    expect(MODELO.capas.map((c) => [c.entradas, c.salidas, c.activacion])).toEqual([
      [42, 64, 'relu'], [64, 32, 'relu'], [32, 6, 'softmax'],
    ])
    expect(MODELO.clases).toEqual(['ok', 'paper', 'rock', 'rockandroll', 'scissors', 'thumbsup'])
    expect(MODELO.accuracy_lopo).toBeGreaterThan(0.96)
  })

  it('da las mismas probabilidades que Python en muestras reales del dataset', () => {
    expect(muestras).toHaveLength(24)
    let aciertos = 0
    for (const muestra of muestras) {
      const prediccion = predecir(MODELO, muestra.xy as Punto[], muestra.ancho, muestra.alto)
      prediccion.probabilidades.forEach((p, i) => expect(p).toBeCloseTo(muestra.probabilidades[i], 5))
      if (prediccion.gesto === muestra.clase) aciertos += 1
    }
    expect(aciertos).toBeGreaterThanOrEqual(22)
  })

  it('no depende de dónde esté la mano, de su tamaño ni de su giro en el plano', () => {
    const muestra = muestras.find((m) => m.clase === 'thumbsup')!
    const xy = muestra.xy as Punto[]
    const base = entradaDesde(xy, muestra.ancho, muestra.alto)
    const ar = muestra.ancho / muestra.alto
    const a = Math.PI / 7
    // mover, encoger y girar la mano en el espacio con el aspecto corregido
    const movida = xy.map(([x, y]) => {
      const [px, py] = [x * ar - 0.5, y - 0.5]
      const [rx, ry] = [0.7 * (Math.cos(a) * px - Math.sin(a) * py), 0.7 * (Math.sin(a) * px + Math.cos(a) * py)]
      return [(rx + 0.6) / ar, ry + 0.45] as Punto
    })
    const otra = entradaDesde(movida, muestra.ancho, muestra.alto)
    otra.forEach((v, i) => expect(v).toBeCloseTo(base[i], 9))
    expect(entradaDesde(xy, muestra.ancho, muestra.alto)[0]).toBe(0)          // la muñeca queda en el origen
  })

  it('se niega a clasificar una mano incompleta', () => {
    expect(() => entradaDesde([[0, 0]], 640, 480)).toThrow(/21 puntos/)
    expect(() => probabilidades(MODELO, [1, 2, 3])).toThrow(/42/)
  })
})

describe('filtro de gestos (el de la demo de Windows)', () => {
  it('solo da el gesto tras cuatro predicciones seguidas con confianza, y no lo repite en 3 s', () => {
    const filtro = new FiltroGestos()
    expect([0, 250, 500].map((t) => filtro.observar('thumbsup', 0.95, t))).toEqual([null, null, null])
    expect(filtro.progreso()).toBeCloseTo(0.75)
    expect(filtro.observar('thumbsup', 0.95, 750)).toBe('thumbsup')
    expect(filtro.observar('thumbsup', 0.95, 1000)).toBeNull()               // sigue ahí: no se repite
    expect(filtro.observar('thumbsup', 0.95, 4000)).toBe('thumbsup')         // pasados 3 s, sí
  })

  it('una predicción dudosa, sin mano o de otro gesto reinicia la cuenta', () => {
    const filtro = new FiltroGestos()
    filtro.observar('paper', 0.9, 0)
    filtro.observar('paper', 0.9, 250)
    filtro.observar('paper', 0.6, 500)
    filtro.observar(null, 0, 750)
    filtro.observar('paper', 0.9, 1000)
    filtro.observar('scissors', 0.9, 1250)
    expect(filtro.progreso()).toBeCloseTo(0.25)
    expect([1500, 1750, 2000].map((t) => filtro.observar('scissors', 0.9, t))).toEqual([null, null, 'scissors'])
  })
})

describe('tabla de gestos (config/gestos.json)', () => {
  it('da una acción distinta a cada una de las seis clases del modelo', () => {
    expect([...LISTA_GESTOS].sort()).toEqual([...MODELO.clases].sort())
    expect(new Set(LISTA_GESTOS.map((g) => GESTOS[g].accion)).size).toBe(6)
    expect(GESTOS.thumbsup.accion).toBe('motor')
    expect(GESTOS.paper.accion).toBe('seccion')
    expect(PREGUNTAS_GESTO.at(-1)).toMatch(/^Dame el viaje/)
  })
})
