/**
 * Zoom y desplazamiento del grafo sin tocar el zoom del navegador.
 *
 * - Rueda del ratón: acerca o aleja hacia el puntero.
 * - Panel táctil: pellizcar hace zoom (el navegador lo entrega como `wheel` con `ctrlKey`, y se anula su zoom de
 *   página); desplazar con dos dedos mueve el grafo.
 * - Arrastrar el fondo (ratón o un dedo) lo mueve; en pantalla táctil, dos dedos lo acercan o alejan.
 * - Doble clic en el fondo: vuelve a la vista inicial. Los botones de la esquina (`ControlesZoom`) acercan y alejan.
 *
 * La escala multiplica el ajuste que ya calcula el lienzo para que quepa entero; el desplazamiento va en píxeles de
 * pantalla desde el centro del marco. `acercarHacia` y `esRuedaDeRaton` son lógica pura (se prueban sin navegador).
 */
import { useCallback, useEffect, useRef, useState, type RefObject } from 'react'

export const ZOOM_MINIMO = 0.5
export const ZOOM_MAXIMO = 3
export const PASO_BOTON = 1.25
/** Cuánto zoom da cada píxel de rueda (exponencial: igual de suave al acercar que al alejar). */
const SENSIBILIDAD_RUEDA = 0.0015
/** Píxeles que hay que mover el puntero para que una pulsación cuente como arrastre y no como clic. */
const UMBRAL_ARRASTRE = 4

export interface Vista {
  zoom: number
  x: number
  y: number
}

export const VISTA_INICIAL: Vista = { zoom: 1, x: 0, y: 0 }

export interface Punto {
  x: number
  y: number
}

/** La vista tras multiplicar el zoom por `factor`, con `punto` (relativo al centro del marco) quieto en pantalla. */
export function acercarHacia(vista: Vista, factor: number, punto: Punto = { x: 0, y: 0 }): Vista {
  const zoom = Math.min(ZOOM_MAXIMO, Math.max(ZOOM_MINIMO, vista.zoom * factor))
  const real = zoom / vista.zoom
  return { zoom, x: punto.x - (punto.x - vista.x) * real, y: punto.y - (punto.y - vista.y) * real }
}

/**
 * ¿Es la rueda de un ratón (zoom) o el desplazamiento con dos dedos de un panel táctil (mover)? El pellizco llega
 * con `ctrlKey` y se trata aparte. Los ratones dan saltos enteros y grandes, solo en vertical, o líneas (Firefox).
 */
export function esRuedaDeRaton(evento: Pick<WheelEvent, 'deltaMode' | 'deltaX' | 'deltaY'>): boolean {
  if (evento.deltaMode !== 0) return true
  return evento.deltaX === 0 && Math.abs(evento.deltaY) >= 50 && Number.isInteger(evento.deltaY)
}

function relativoAlCentro(marco: HTMLElement, x: number, y: number): Punto {
  const caja = marco.getBoundingClientRect()
  return { x: x - (caja.left + caja.width / 2), y: y - (caja.top + caja.height / 2) }
}

/** Pulsaciones sobre las piezas y los botones no mueven el grafo: son clics. */
function esControl(objetivo: EventTarget | null): boolean {
  return objetivo instanceof Element && objetivo.closest('button, a, [role="dialog"]') !== null
}

export function useZoomLienzo(marco: RefObject<HTMLElement | null>) {
  const [vista, setVista] = useState<Vista>(VISTA_INICIAL)
  const [arrastrando, setArrastrando] = useState(false)
  const vistaActual = useRef(vista)          // la vista al empezar un arrastre o un pellizco
  useEffect(() => {
    vistaActual.current = vista
  }, [vista])
  const punteros = useRef(new Map<number, Punto>())
  const inicio = useRef<{ punto: Punto; vista: Vista; movido: boolean } | null>(null)
  const pellizco = useRef<{ distancia: number; vista: Vista } | null>(null)

  const acercar = useCallback(() => setVista((v) => acercarHacia(v, PASO_BOTON)), [])
  const alejar = useCallback(() => setVista((v) => acercarHacia(v, 1 / PASO_BOTON)), [])
  const restablecer = useCallback(() => setVista(VISTA_INICIAL), [])

  useEffect(() => {
    const el = marco.current
    if (!el) return

    // `wheel` no pasivo: si no, el navegador desplazaría la página o haría su propio zoom con el pellizco
    const alRodar = (evento: WheelEvent) => {
      evento.preventDefault()
      if (evento.ctrlKey || esRuedaDeRaton(evento)) {
        const factor = Math.exp(-evento.deltaY * (evento.deltaMode === 1 ? 40 : 1) * SENSIBILIDAD_RUEDA * (evento.ctrlKey ? 4 : 1))
        const punto = relativoAlCentro(el, evento.clientX, evento.clientY)
        setVista((v) => acercarHacia(v, factor, punto))
      } else {
        setVista((v) => ({ ...v, x: v.x - evento.deltaX, y: v.y - evento.deltaY }))
      }
    }

    const alPulsar = (evento: PointerEvent) => {
      if (esControl(evento.target) || (evento.pointerType === 'mouse' && evento.button !== 0)) return
      punteros.current.set(evento.pointerId, { x: evento.clientX, y: evento.clientY })
      el.setPointerCapture?.(evento.pointerId)
      if (punteros.current.size === 1) {
        inicio.current = { punto: { x: evento.clientX, y: evento.clientY }, vista: vistaActual.current, movido: false }
      } else if (punteros.current.size === 2) {
        const [a, b] = [...punteros.current.values()]
        pellizco.current = { distancia: Math.hypot(a.x - b.x, a.y - b.y), vista: vistaActual.current }
      }
    }

    const alMover = (evento: PointerEvent) => {
      if (!punteros.current.has(evento.pointerId)) return
      punteros.current.set(evento.pointerId, { x: evento.clientX, y: evento.clientY })
      if (punteros.current.size >= 2 && pellizco.current) {
        const [a, b] = [...punteros.current.values()]
        const centro = relativoAlCentro(el, (a.x + b.x) / 2, (a.y + b.y) / 2)
        const factor = Math.hypot(a.x - b.x, a.y - b.y) / Math.max(1, pellizco.current.distancia)
        setVista(acercarHacia(pellizco.current.vista, factor, centro))
        return
      }
      const arrastre = inicio.current
      if (!arrastre) return
      const dx = evento.clientX - arrastre.punto.x
      const dy = evento.clientY - arrastre.punto.y
      if (!arrastre.movido && Math.hypot(dx, dy) < UMBRAL_ARRASTRE) return
      if (!arrastre.movido) {
        arrastre.movido = true
        setArrastrando(true)
      }
      setVista({ ...arrastre.vista, x: arrastre.vista.x + dx, y: arrastre.vista.y + dy })
    }

    const alSoltar = (evento: PointerEvent) => {
      punteros.current.delete(evento.pointerId)
      if (punteros.current.size < 2) pellizco.current = null
      if (punteros.current.size === 0) {
        inicio.current = null
        setArrastrando(false)
      }
    }

    const alDobleClic = (evento: MouseEvent) => {
      if (!esControl(evento.target)) setVista(VISTA_INICIAL)
    }

    el.addEventListener('wheel', alRodar, { passive: false })
    el.addEventListener('pointerdown', alPulsar)
    el.addEventListener('pointermove', alMover)
    el.addEventListener('pointerup', alSoltar)
    el.addEventListener('pointercancel', alSoltar)
    el.addEventListener('dblclick', alDobleClic)
    return () => {
      el.removeEventListener('wheel', alRodar)
      el.removeEventListener('pointerdown', alPulsar)
      el.removeEventListener('pointermove', alMover)
      el.removeEventListener('pointerup', alSoltar)
      el.removeEventListener('pointercancel', alSoltar)
      el.removeEventListener('dblclick', alDobleClic)
    }
  }, [marco])

  return { vista, arrastrando, acercar, alejar, restablecer }
}
