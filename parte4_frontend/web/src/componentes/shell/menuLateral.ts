/**
 * Estado del menú izquierdo: expandido (15 rem, con los títulos) o contraído (4 rem, solo iconos con su
 * descripción emergente). La preferencia se guarda en el navegador y sobrevive a la recarga.
 */
import { useCallback, useState } from 'react'

export const CLAVE_MENU_CONTRAIDO = 'pids.menu-contraido'
export const ID_MENU_SECCIONES = 'menu-secciones'

/** Anchura de la barra y relleno del contenido, en las dos posiciones (clases literales: Tailwind no genera dinámicas). */
export const ANCHO_BARRA = { expandido: 'w-60', contraido: 'w-16' } as const
export const RELLENO_CONTENIDO = { expandido: 'pl-60', contraido: 'pl-16' } as const

function leerPreferencia(): boolean {
  try {
    return window.localStorage.getItem(CLAVE_MENU_CONTRAIDO) === '1'
  } catch {
    return false
  }
}

function guardarPreferencia(contraido: boolean): void {
  try {
    window.localStorage.setItem(CLAVE_MENU_CONTRAIDO, contraido ? '1' : '0')
  } catch {
    // sin almacenamiento (modo privado estricto) el menú funciona igual, solo no recuerda la preferencia
  }
}

export function useMenuContraido(): [boolean, () => void] {
  const [contraido, setContraido] = useState(leerPreferencia)
  const alternar = useCallback(() => {
    guardarPreferencia(!contraido)
    setContraido(!contraido)
  }, [contraido])
  return [contraido, alternar]
}
