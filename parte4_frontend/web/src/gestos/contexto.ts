/**
 * Estado compartido de los gestos: el proveedor (`ProveedorGestos.tsx`) enciende la cámara y emite cada gesto
 * confirmado; quien quiera reaccionar se suscribe con `useAlGesto` (TAXI AI, el panel que se abre y se cierra).
 * La lectura en directo (gesto, confianza, puntos de la mano) cambia unas diez veces por segundo y va en un almacén
 * aparte (`useLectura`), para que solo se repinte la tarjeta de la cámara.
 */
import { createContext, useContext, useEffect, useRef, useSyncExternalStore } from 'react'

import type { Punto } from './reconocedor'
import type { Gesto } from './tabla'

export type EstadoCamara = 'apagada' | 'cargando' | 'activa' | 'error'
/** Dónde acabó el último gesto de la cámara: en la plataforma (API de captura → Redpanda) o solo en el navegador. */
export type DestinoGesto = 'plataforma' | 'navegador'

export interface EventoGesto {
  id: number
  gesto: Gesto
  confianza: number
  /** `camara`: la de este navegador; `plataforma`: otro dispositivo (la demo de Windows u otra pestaña). */
  origen: 'camara' | 'plataforma'
  /** ms desde la época. */
  instante: number
}

export interface Lectura {
  gesto: Gesto | null
  confianza: number
  /** Cuánto falta para confirmar el gesto que se sostiene (0 a 1). */
  progreso: number
  puntos: Punto[] | null
}

export const SIN_LECTURA: Lectura = { gesto: null, confianza: 0, progreso: 0, puntos: null }

export class AlmacenLectura {
  private valor: Lectura = SIN_LECTURA
  private readonly oyentes = new Set<() => void>()
  suscribir = (oyente: () => void) => {
    this.oyentes.add(oyente)
    return () => {
      this.oyentes.delete(oyente)
    }
  }
  leer = () => this.valor
  publicar(valor: Lectura): void {
    this.valor = valor
    this.oyentes.forEach((oyente) => oyente())
  }
}

export interface ValorGestos {
  estado: EstadoCamara
  error: string | null
  destino: DestinoGesto | null
  activar: () => void
  desactivar: () => void
  suscribir: (oyente: (evento: EventoGesto) => void) => () => void
  /** El último gesto emitido (para quien se monta justo después, como el panel que ese gesto ha abierto). */
  ultimo: () => EventoGesto | null
  lectura: AlmacenLectura
}

const SIN_PROVEEDOR: ValorGestos = {
  estado: 'apagada', error: null, destino: null, activar: () => undefined, desactivar: () => undefined,
  suscribir: () => () => undefined, ultimo: () => null, lectura: new AlmacenLectura(),
}

export const ContextoGestos = createContext<ValorGestos>(SIN_PROVEEDOR)

export function useGestos(): ValorGestos {
  return useContext(ContextoGestos)
}

export function useLectura(): Lectura {
  const { lectura } = useGestos()
  return useSyncExternalStore(lectura.suscribir, lectura.leer, lectura.leer)
}

/** Llama a `manejador` con cada gesto confirmado (siempre la versión más reciente del manejador). */
export function useAlGesto(manejador: (evento: EventoGesto) => void): void {
  const { suscribir } = useGestos()
  const ultimo = useRef(manejador)
  useEffect(() => {
    ultimo.current = manejador
  })
  useEffect(() => suscribir((evento) => ultimo.current(evento)), [suscribir])
}

function aleatorio(): string {
  const bytes = new Uint8Array(8)
  crypto.getRandomValues(bytes)
  return Array.from(bytes, (b) => (b % 36).toString(36)).join('')
}

/** Esta pestaña, para la API de captura (`dispositivo`): así no reacciona dos veces a su propio gesto. */
export const DISPOSITIVO = `portal-${aleatorio()}`
