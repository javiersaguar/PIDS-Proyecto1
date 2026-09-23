/**
 * Gestos de la parte 1 en el portal. Con la cámara activada, cada fotograma pasa por MediaPipe (los 21 puntos de la
 * mano) y por el MLP de la parte 1; el filtro de la demo de Windows decide cuándo un gesto es de verdad, y entonces:
 *   - se avisa a quien escucha (TAXI AI confirma, cancela, pregunta o lee; el panel se abre o se cierra);
 *   - se envía a la plataforma (`POST /api/gestos` → API de captura → cola `gestos` de Redpanda), donde también lo
 *     ven los chatbots de Chainlit y los cuadros de Grafana. En la demostración pública se queda en el navegador.
 * Además escucha los gestos que entran por la plataforma (la demo de Windows): actúan igual que los de la cámara.
 *
 * La imagen de la cámara no sale del navegador. La cámara se apaga al desactivar los gestos o al cerrar la sesión.
 */
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { toast } from 'sonner'

import { ErrorApi } from '@/api/cliente'
import { marcarGesto } from '@/api/gestoActivo'
import { enviarGesto, escucharGestos } from '@/api/gestos'

import {
  AlmacenLectura, ContextoGestos, DISPOSITIVO, SIN_LECTURA,
  type DestinoGesto, type EstadoCamara, type EventoGesto, type ValorGestos,
} from './contexto'
import { FiltroGestos } from './filtro'
import { cargarModelo, predecir, type ModeloGestos } from './modelo'
import { crearReconocedor, type Punto, type Reconocedor } from './reconocedor'
import { CONFIANZA_MINIMA, esGesto, GESTOS, MS_ENTRE_MUESTRAS, type Gesto } from './tabla'
import { TarjetaGestos } from './TarjetaGestos'

/** Una detección cada ~90 ms basta para que los puntos de la mano sigan al vídeo sin cargar el equipo. */
const MS_ENTRE_DETECCIONES = 90
const ESPERA_INICIAL_MS = 2_000
const ESPERA_MAXIMA_MS = 60_000
/** Los ids de los gestos no se repiten en toda la página, aunque el proveedor se vuelva a montar (al volver a entrar):
 * el chat recuerda el último que atendió. */
let ultimoId = 0

interface Props {
  children: ReactNode
}

interface Recursos {
  flujo: MediaStream
  reconocedor: Reconocedor
  modelo: ModeloGestos
}

function explicarErrorCamara(error: unknown): string {
  const nombre = error instanceof DOMException || error instanceof Error ? error.name : ''
  if (nombre === 'NotAllowedError' || nombre === 'SecurityError') return 'El navegador no ha dado permiso para usar la cámara.'
  if (nombre === 'NotFoundError' || nombre === 'OverconstrainedError') return 'No se encuentra ninguna cámara en este equipo.'
  if (nombre === 'NotReadableError') return 'La cámara está ocupada por otra aplicación (o tapada por el obturador).'
  if (nombre === 'SinCamara') return 'Este navegador no puede usar la cámara (hace falta https o localhost).'
  return 'No se ha podido preparar el reconocimiento de gestos (sin conexión con el CDN de MediaPipe o el modelo).'
}

function dormir(ms: number, señal: AbortSignal): Promise<void> {
  return new Promise((resolver) => {
    const id = setTimeout(resolver, ms)
    señal.addEventListener('abort', () => {
      clearTimeout(id)
      resolver()
    }, { once: true })
  })
}

export function ProveedorGestos({ children }: Props) {
  const [estado, setEstado] = useState<EstadoCamara>('apagada')
  const [error, setError] = useState<string | null>(null)
  const [destino, setDestino] = useState<DestinoGesto | null>(null)
  const estadoRef = useRef<EstadoCamara>('apagada')
  const videoRef = useRef<HTMLVideoElement>(null)
  const recursos = useRef<Recursos | null>(null)
  const oyentes = useRef(new Set<(evento: EventoGesto) => void>())
  const ultimo = useRef<EventoGesto | null>(null)
  const [lectura] = useState(() => new AlmacenLectura())

  const cambiarEstado = useCallback((nuevo: EstadoCamara) => {
    estadoRef.current = nuevo
    setEstado(nuevo)
  }, [])

  const emitir = useCallback((gesto: Gesto, confianza: number, origen: EventoGesto['origen']) => {
    ultimoId += 1
    const evento: EventoGesto = { id: ultimoId, gesto, confianza, origen, instante: Date.now() }
    ultimo.current = evento
    const datos = GESTOS[gesto]
    toast(`${datos.emoji} ${datos.titulo}`, {
      description: origen === 'plataforma' ? 'Gesto recibido de la plataforma' : `${Math.round(confianza * 100)} % de confianza`,
      duration: 1800,
    })
    oyentes.current.forEach((oyente) => oyente(evento))
    if (origen === 'plataforma') {
      marcarGesto(gesto, true)
      return
    }
    enviarGesto({ gesto, confianza, dispositivo: DISPOSITIVO })
      .then((resultado) => {
        setDestino(resultado.enviado ? 'plataforma' : 'navegador')
        marcarGesto(gesto, resultado.enviado)
      })
      .catch(() => {
        setDestino('navegador')
        marcarGesto(gesto, false)
      })
  }, [])

  const liberar = useCallback(() => {
    const actuales = recursos.current
    recursos.current = null
    actuales?.flujo.getTracks().forEach((pista) => pista.stop())
    actuales?.reconocedor.cerrar()
    if (videoRef.current) videoRef.current.srcObject = null
    lectura.publicar(SIN_LECTURA)
  }, [lectura])

  const desactivar = useCallback(() => {
    liberar()
    setError(null)
    cambiarEstado('apagada')
  }, [liberar, cambiarEstado])

  const activar = useCallback(() => {
    if (estadoRef.current === 'cargando' || estadoRef.current === 'activa') return
    cambiarEstado('cargando')
    setError(null)
    void (async () => {
      let flujo: MediaStream | null = null
      let reconocedor: Reconocedor | null = null
      try {
        if (!navigator.mediaDevices?.getUserMedia) throw new DOMException('sin cámara', 'SinCamara')
        // primero el permiso de la cámara, para que el aviso del navegador salga enseguida
        flujo = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, facingMode: 'user' }, audio: false })
        const [modelo, creado] = await Promise.all([cargarModelo(), crearReconocedor()])
        reconocedor = creado
        if (estadoRef.current !== 'cargando') throw new DOMException('cancelado', 'AbortError')
        recursos.current = { flujo, reconocedor, modelo }
        const video = videoRef.current
        if (video) {
          video.srcObject = flujo
          await video.play().catch(() => undefined)
        }
        cambiarEstado('activa')
      } catch (fallo) {
        flujo?.getTracks().forEach((pista) => pista.stop())
        reconocedor?.cerrar()
        recursos.current = null
        if (fallo instanceof DOMException && fallo.name === 'AbortError') return
        setError(explicarErrorCamara(fallo))
        cambiarEstado('error')
      }
    })()
  }, [cambiarEstado])

  // Bucle de reconocimiento mientras la cámara está activa.
  useEffect(() => {
    if (estado !== 'activa') return
    const actuales = recursos.current
    const video = videoRef.current
    if (!actuales || !video) return
    const filtro = new FiltroGestos()
    let ultimaDeteccion = 0
    let ultimaMuestra = 0
    let marco = requestAnimationFrame(function paso(t: number) {
      marco = requestAnimationFrame(paso)
      if (t - ultimaDeteccion < MS_ENTRE_DETECCIONES || video.readyState < 2 || !video.videoWidth) return
      ultimaDeteccion = t
      let puntos: Punto[] | null
      try {
        puntos = actuales.reconocedor.detectar(video, t)
      } catch {
        return
      }
      const prediccion = puntos ? predecir(actuales.modelo, puntos, video.videoWidth, video.videoHeight) : null
      if (t - ultimaMuestra >= MS_ENTRE_MUESTRAS) {
        ultimaMuestra = t
        const confirmado = filtro.observar(prediccion?.gesto ?? null, prediccion?.confianza ?? 0, t)
        if (confirmado && prediccion) emitir(confirmado, prediccion.confianza, 'camara')
      }
      lectura.publicar({
        gesto: prediccion?.gesto ?? null,
        confianza: prediccion?.confianza ?? 0,
        progreso: filtro.progreso(),
        puntos,
      })
    })
    return () => cancelAnimationFrame(marco)
  }, [estado, emitir, lectura])

  // Gestos que entran por la plataforma (la demo de Windows u otra pestaña). En la demostración no hay flujo (404).
  useEffect(() => {
    const control = new AbortController()
    void (async () => {
      let espera = ESPERA_INICIAL_MS
      while (!control.signal.aborted) {
        try {
          await escucharGestos((recibido) => {
            espera = ESPERA_INICIAL_MS
            if (recibido.dispositivo === DISPOSITIVO || !esGesto(recibido.gesto)) return
            if (!(recibido.confianza >= CONFIANZA_MINIMA)) return
            emitir(recibido.gesto, recibido.confianza, 'plataforma')
          }, control.signal)
        } catch (fallo) {
          if (control.signal.aborted) return
          // sin sesión, sin flujo (demostración) o sin clave de gestos: no tiene sentido insistir
          if (fallo instanceof ErrorApi && [401, 403, 404, 503].includes(fallo.status)) return
        }
        await dormir(espera, control.signal)
        espera = Math.min(espera * 2, ESPERA_MAXIMA_MS)
      }
    })()
    return () => control.abort()
  }, [emitir])

  // La cámara no se queda encendida al salir del portal.
  useEffect(() => liberar, [liberar])

  const suscribir = useCallback((oyente: (evento: EventoGesto) => void) => {
    const lista = oyentes.current
    lista.add(oyente)
    return () => {
      lista.delete(oyente)
    }
  }, [])
  const leerUltimo = useCallback(() => ultimo.current, [])

  const valor = useMemo<ValorGestos>(
    () => ({ estado, error, destino, activar, desactivar, suscribir, ultimo: leerUltimo, lectura }),
    [estado, error, destino, activar, desactivar, suscribir, leerUltimo, lectura],
  )

  return (
    <ContextoGestos.Provider value={valor}>
      {children}
      {estado !== 'apagada' && <TarjetaGestos videoRef={videoRef} />}
    </ContextoGestos.Provider>
  )
}
