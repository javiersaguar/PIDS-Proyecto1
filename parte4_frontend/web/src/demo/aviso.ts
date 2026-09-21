/**
 * Aviso fijo del modo demostración, fuera del árbol de React para no tocar las páginas: deja claro que los datos
 * están grabados y enlaza con el repositorio. Se puede plegar; la preferencia se recuerda en este navegador.
 */
const CLAVE = 'pids-demo-aviso-plegado'
const REPOSITORIO = 'https://github.com/javiersaguar/PIDS-Proyecto1/blob/main/parte4_frontend/demo/README.md'

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

function montar(): void {
  const aviso = document.createElement('aside')
  aviso.setAttribute('aria-label', 'Demostración')
  // abajo a la izquierda, del ancho de la barra lateral: en escritorio tapa solo su pie, que es texto fijo
  aviso.className = 'fixed bottom-3 left-3 z-50 max-w-[216px] rounded-lg border bg-superficie text-xs text-texto shadow-lg'
  aviso.innerHTML = `
    <div class="flex items-center gap-2 px-3 py-2">
      <span class="size-2 shrink-0 rounded-full bg-aviso" aria-hidden="true"></span>
      <strong class="font-semibold">Demostración</strong>
      <button type="button" data-plegar class="ml-auto rounded px-1.5 py-0.5 text-texto-suave hover:bg-muted"></button>
    </div>
    <div data-texto class="space-y-1.5 border-t px-3 pb-2.5 pt-2 leading-snug text-texto-suave">
      <p>Datos grabados de la plataforma real: agregados de 2020, ya enmascarados. El tiempo real reproduce el 03/03/2020.</p>
      <a class="inline-block font-medium text-primario underline underline-offset-2" href="${REPOSITORIO}" target="_blank" rel="noreferrer">Ejecutarlo con datos en vivo</a>
    </div>`
  const texto = aviso.querySelector<HTMLElement>('[data-texto]')!
  const boton = aviso.querySelector<HTMLButtonElement>('[data-plegar]')!
  const aplicar = (plegado: boolean) => {
    texto.hidden = plegado
    boton.textContent = plegado ? 'Ver' : 'Ocultar'
    boton.setAttribute('aria-expanded', String(!plegado))
  }
  let plegado = leerPlegado()
  aplicar(plegado)
  boton.addEventListener('click', () => {
    plegado = !plegado
    guardarPlegado(plegado)
    aplicar(plegado)
  })
  document.body.append(aviso)
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', montar, { once: true })
else montar()
