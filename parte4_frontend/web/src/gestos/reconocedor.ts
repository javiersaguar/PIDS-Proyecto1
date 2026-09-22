/**
 * Los 21 puntos de la mano con MediaPipe Tasks para web (`HandLandmarker`), el mismo modelo de MediaPipe que usó la
 * parte 1 para extraer los puntos del dataset. Solo se descarga cuando alguien activa los gestos: el código de la
 * biblioteca va en un trozo aparte y el motor WebAssembly (unos 10 MB) y el modelo de la mano (7,8 MB) se piden a sus
 * CDN públicos, con la versión fija. La imagen de la cámara se procesa aquí, en el navegador, y no se envía a nadie.
 */
import type { HandLandmarker } from '@mediapipe/tasks-vision'

const VERSION = '1.0.1'
const WASM = `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${VERSION}/wasm`
const MODELO_MANO = 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task'

export type Punto = [number, number]

export interface Reconocedor {
  /** Los 21 puntos [x, y] (en [0, 1]) de la mano del fotograma, o `null` si no hay mano. */
  detectar: (video: HTMLVideoElement, instanteMs: number) => Punto[] | null
  cerrar: () => void
}

async function crear(delegado: 'GPU' | 'CPU'): Promise<HandLandmarker> {
  const { FilesetResolver, HandLandmarker } = await import('@mediapipe/tasks-vision')
  const fileset = await FilesetResolver.forVisionTasks(WASM)
  return HandLandmarker.createFromOptions(fileset, {
    baseOptions: { modelAssetPath: MODELO_MANO, delegate: delegado },
    runningMode: 'VIDEO',
    numHands: 1,                         // como en el dataset: una mano, umbral de detección 0,5
    minHandDetectionConfidence: 0.5,
  })
}

export async function crearReconocedor(): Promise<Reconocedor> {
  // la GPU va más fluida; si el navegador no la ofrece a WebGL, la CPU basta para una mano
  const mano = await crear('GPU').catch(() => crear('CPU'))
  return {
    detectar(video, instanteMs) {
      const resultado = mano.detectForVideo(video, instanteMs)
      const puntos = resultado.landmarks[0]
      return puntos && puntos.length === 21 ? puntos.map((p) => [p.x, p.y] as Punto) : null
    },
    cerrar: () => mano.close(),
  }
}
