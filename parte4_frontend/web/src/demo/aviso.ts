/**
 * Aviso fijo de la web pública, fuera del árbol de React para no tocar las páginas. Dice si lo que se ve es la
 * plataforma en vivo (por el túnel) o la demostración con datos grabados, y deja cambiar de una a otra: sin la
 * contraseña del portal, «Ver la demostración»; con el equipo encendido, «Ver en vivo». Se puede plegar; la
 * preferencia se recuerda en este navegador.
 */
import { elegirModo, vivoDisponible, type Modo } from './modo'

const CLAVE = 'pids-demo-aviso-plegado'

function leerPlegado(): boolean {
  try {
    return localStorage.getItem(CLAVE) === '1'
  } catch {
    return false
  }
}

function guardarPlegado(plegado: boolean): void {
  try {
    localStorage.setItem(CLAVE, plegado ? '1' : '0')
  } catch {
    // sin almacenamiento (ventana privada) el aviso simplemente vuelve a salir desplegado
  }
}

const TEXTOS: Record<Modo, { titulo: string; texto: string; boton: string }> = {
  demo: {
    titulo: 'Demostración',
    texto: 'Datos grabados de la plataforma real: agregados de 2020, ya enmascarados. El tiempo real reproduce el 03/03/2020.',
    boton: 'Ver en vivo',
  },
  vivo: {
    titulo: 'En vivo',
    texto: 'La plataforma del equipo, ahora mismo. Entra con la contraseña del portal.',
    boton: 'Ver la demostración',
  },
}

export function montarAviso(modo: Modo): void {
  const montar = () => {
    const textos = TEXTOS[modo]
    const aviso = document.createElement('aside')
    aviso.setAttribute('aria-label', textos.titulo)
    // el botón «Gestos» se coloca encima de este aviso (gestos/BotonGestos.tsx)
    aviso.dataset.avisoModo = modo
    // abajo a la izquierda, del ancho de la barra lateral y por encima de su pie, para no tapar «Cerrar sesión»
    aviso.className = 'fixed bottom-[4.5rem] left-3 z-50 max-w-[216px] rounded-lg border bg-superficie text-xs text-texto shadow-lg'
    aviso.innerHTML = `
      <div class="flex items-center gap-2 px-3 py-2">
        <span class="size-2 shrink-0 rounded-full ${modo === 'vivo' ? 'bg-ok' : 'bg-aviso'}" aria-hidden="true"></span>
        <strong class="font-semibold"></strong>
        <button type="button" data-plegar class="ml-auto rounded px-1.5 py-0.5 text-texto-suave hover:bg-muted"></button>
      </div>
      <div data-texto class="space-y-1.5 border-t px-3 pb-2.5 pt-2 leading-snug text-texto-suave">
        <p data-parrafo></p>
        <button type="button" data-cambiar class="font-medium text-primario underline underline-offset-2"></button>
        <p data-nota class="hidden"></p>
      </div>`
    aviso.querySelector('strong')!.textContent = textos.titulo
    aviso.querySelector('[data-parrafo]')!.textContent = textos.texto
    const cambiar = aviso.querySelector<HTMLButtonElement>('[data-cambiar]')!
    const nota = aviso.querySelector<HTMLElement>('[data-nota]')!
    cambiar.textContent = textos.boton
    cambiar.addEventListener('click', async () => {
      if (modo === 'vivo') return elegirModo('demo')
      cambiar.disabled = true
      cambiar.textContent = 'Comprobando…'
      if (await vivoDisponible()) return elegirModo('vivo')
      cambiar.disabled = false
      cambiar.textContent = textos.boton
      nota.textContent = 'Ahora mismo la plataforma del equipo está apagada: sigue la demostración.'
      nota.classList.remove('hidden')
    })

    const texto = aviso.querySelector<HTMLElement>('[data-texto]')!
    const plegar = aviso.querySelector<HTMLButtonElement>('[data-plegar]')!
    const aplicar = (plegado: boolean) => {
      texto.hidden = plegado
      plegar.textContent = plegado ? 'Ver' : 'Ocultar'
      plegar.setAttribute('aria-expanded', String(!plegado))
    }
    let plegado = leerPlegado()
    aplicar(plegado)
    plegar.addEventListener('click', () => {
      plegado = !plegado
      guardarPlegado(plegado)
      aplicar(plegado)
    })
    document.body.append(aviso)
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', montar, { once: true })
  else montar()
}
