/**
 * Vistas guardadas del explorador: consultas que el usuario quiere volver a abrir.
 * Viven en `localStorage` de este navegador; no se envían a la API.
 */
import type { Consulta } from '@/api/tipos'

import { aParametros, desdeParametros } from './consulta'

const CLAVE = 'pids.explorador.vistas'
export const MAX_VISTAS = 8

export interface VistaGuardada {
  id: string
  titulo: string
  consulta: Consulta
}

function nuevoId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `vista-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function normalizar(valor: unknown): VistaGuardada | null {
  if (!valor || typeof valor !== 'object') return null
  const vista = valor as Partial<VistaGuardada>
  if (typeof vista.id !== 'string' || typeof vista.titulo !== 'string' || !vista.titulo.trim() || !vista.consulta) return null
  try {
    const consulta = desdeParametros(aParametros(vista.consulta))
    if (!consulta) return null
    return { id: vista.id, titulo: vista.titulo.trim().slice(0, 80), consulta }
  } catch {
    return null
  }
}

export function leerVistas(): VistaGuardada[] {
  try {
    const crudo = localStorage.getItem(CLAVE)
    if (!crudo) return []
    const datos: unknown = JSON.parse(crudo)
    if (!Array.isArray(datos)) return []
    return datos.map(normalizar).filter((vista): vista is VistaGuardada => vista !== null).slice(0, MAX_VISTAS)
  } catch {
    return []
  }
}

export function guardarVistas(vistas: readonly VistaGuardada[]): void {
  localStorage.setItem(CLAVE, JSON.stringify(vistas.slice(0, MAX_VISTAS)))
}

export function crearVista(titulo: string, consulta: Consulta): VistaGuardada {
  return { id: nuevoId(), titulo: titulo.trim().slice(0, 80), consulta }
}
