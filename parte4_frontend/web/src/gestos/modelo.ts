/**
 * El MLP de la parte 1 (normalización muñeca + escala + rotación, 96,5 % con una persona no vista) ejecutado en el
 * navegador. `parte1_gestos/entrenamiento/exportar_web.py` escribe sus pesos en `public/gestos/modelo.json` y unas
 * muestras reales del dataset en `muestras.json`, con las que `modelo.test.ts` comprueba que aquí sale lo mismo que
 * en Python. Lógica pura: sin DOM ni cámara.
 *
 * La entrada es la de `hgr/features.py` al entrenar:
 *   x, y de MediaPipe (en [0, 1])  →  x · ancho/alto (aspecto corregido)  →  restar la muñeca (punto 0)
 *   →  dividir por la distancia muñeca → nudillo del corazón (punto 9)  →  girar para que ese vector apunte arriba
 *   →  42 valores intercalados x0, y0, x1, y1…
 */
import type { Gesto } from './tabla'

const MUNECA = 0
const MCP_CORAZON = 9
export const PUNTOS = 21

export interface CapaDensa {
  activacion: 'relu' | 'softmax' | 'linear'
  entradas: number
  salidas: number
  /** Matriz (entradas × salidas) por filas, como el `kernel` de Keras. */
  kernel: number[]
  sesgo: number[]
}

export interface ModeloGestos {
  origen: string
  experimento: string
  accuracy_lopo: number
  normalizacion: 'muneca_escala_rot'
  clases: Gesto[]
  capas: CapaDensa[]
}

export interface Prediccion {
  gesto: Gesto
  confianza: number
  probabilidades: number[]
}

/** Los 42 valores de entrada del MLP a partir de los 21 puntos [x, y] de MediaPipe y el tamaño de la imagen. */
export function entradaDesde(xy: readonly (readonly [number, number])[], ancho: number, alto: number): Float64Array {
  if (xy.length !== PUNTOS) throw new Error(`se esperaban ${PUNTOS} puntos de la mano y hay ${xy.length}`)
  const ar = ancho / alto
  const puntos = xy.map(([x, y]) => [x * ar, y] as const)
  const [x0, y0] = puntos[MUNECA]
  const relativos = puntos.map(([x, y]) => [x - x0, y - y0] as const)
  const [vx, vy] = relativos[MCP_CORAZON]
  const norma = Math.hypot(vx, vy)
  const escala = norma < 1e-9 ? 1 : norma
  // girar para llevar el vector muñeca → nudillo a (0, -1): «arriba» con el eje y hacia abajo
  const angulo = Math.atan2(vy / escala, vx / escala)
  const giro = -Math.PI / 2 - angulo
  const c = Math.cos(giro)
  const s = Math.sin(giro)
  const entrada = new Float64Array(PUNTOS * 2)
  relativos.forEach(([x, y], i) => {
    const px = x / escala
    const py = y / escala
    entrada[2 * i] = c * px - s * py
    entrada[2 * i + 1] = s * px + c * py
  })
  return entrada
}

/** Probabilidades de cada clase, capa a capa (lo mismo que `predecir` de `exportar_web.py`). */
export function probabilidades(modelo: ModeloGestos, entrada: ArrayLike<number>): number[] {
  let h = Array.from(entrada)
  for (const capa of modelo.capas) {
    if (h.length !== capa.entradas) throw new Error(`la capa espera ${capa.entradas} valores y recibe ${h.length}`)
    const salida = capa.sesgo.slice()
    for (let i = 0; i < capa.entradas; i++) {
      const valor = h[i]
      if (valor === 0) continue
      const fila = i * capa.salidas
      for (let j = 0; j < capa.salidas; j++) salida[j] += valor * capa.kernel[fila + j]
    }
    if (capa.activacion === 'relu') {
      h = salida.map((v) => (v > 0 ? v : 0))
    } else if (capa.activacion === 'softmax') {
      const maximo = Math.max(...salida)
      const exp = salida.map((v) => Math.exp(v - maximo))
      const suma = exp.reduce((a, b) => a + b, 0)
      h = exp.map((v) => v / suma)
    } else {
      h = salida
    }
  }
  return h
}

export function predecir(modelo: ModeloGestos, xy: readonly (readonly [number, number])[], ancho: number, alto: number): Prediccion {
  const p = probabilidades(modelo, entradaDesde(xy, ancho, alto))
  let mejor = 0
  for (let i = 1; i < p.length; i++) if (p[i] > p[mejor]) mejor = i
  return { gesto: modelo.clases[mejor], confianza: p[mejor], probabilidades: p }
}

let pendiente: Promise<ModeloGestos> | null = null

/** Descarga el modelo la primera vez que se activan los gestos (unos 50 KiB). */
export function cargarModelo(ruta = '/gestos/modelo.json'): Promise<ModeloGestos> {
  pendiente ??= fetch(ruta).then(async (respuesta) => {
    if (!respuesta.ok) throw new Error(`no se ha podido descargar el modelo de gestos (HTTP ${respuesta.status})`)
    return (await respuesta.json()) as ModeloGestos
  })
  pendiente.catch(() => {
    pendiente = null
  })
  return pendiente
}
