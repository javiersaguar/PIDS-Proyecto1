/** Si la barra lateral está abierta o cerrada: la elección se recuerda en este navegador. */
const CLAVE_MENU = 'pids-menu-abierto'

export function menuAbiertoGuardado(): boolean {
  try {
    return localStorage.getItem(CLAVE_MENU) !== '0'
  } catch {
    return true
  }
}

export function guardarMenuAbierto(abierto: boolean): void {
  try {
    localStorage.setItem(CLAVE_MENU, abierto ? '1' : '0')
  } catch {
    // el menú sigue funcionando aunque el navegador no deje guardar la preferencia
  }
}
