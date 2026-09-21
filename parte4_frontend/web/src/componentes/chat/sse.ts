/**
 * Lector de `text/event-stream` para respuestas de `fetch` (el chat del BFF responde a un POST, así que
 * `EventSource` no sirve). Lógica pura, sin DOM: se prueba sola en `sse.test.ts`.
 *
 * Sigue el formato de la especificación de Server-Sent Events:
 *   - los mensajes se separan por una línea en blanco; las líneas terminan en `\r\n`, `\n` o `\r`;
 *   - `event:` fija el tipo (por defecto `message`); cada `data:` añade una línea al contenido;
 *   - las líneas que empiezan por `:` son comentarios (sse-starlette las usa como latido) y se ignoran,
 *     igual que `id:` y `retry:`, que aquí no se necesitan;
 *   - un mensaje sin `data` no se entrega.
 * Los trozos pueden partir un mensaje (incluso una línea) por cualquier sitio: el parser guarda lo pendiente.
 */

export interface MensajeSse {
  /** Tipo del evento (`paso`, `respuesta`, `error`…; `message` si el servidor no lo indica). */
  evento: string
  /** Contenido: las líneas `data:` unidas con `\n`. */
  datos: string
}

export class ParserSse {
  private pendiente = ''
  private evento = ''
  private datos: string[] = []
  private readonly alMensaje: (mensaje: MensajeSse) => void

  constructor(alMensaje: (mensaje: MensajeSse) => void) {
    this.alMensaje = alMensaje
  }

  /** Añade un trozo de texto y entrega los mensajes que hayan quedado completos. */
  alimentar(trozo: string): void {
    this.pendiente += trozo
    for (;;) {
      const corte = this.pendiente.search(/\r|\n/)
      if (corte === -1) return
      let siguiente = corte + 1
      if (this.pendiente[corte] === '\r') {
        // Un `\r` al final del trozo puede ser la primera mitad de un `\r\n`: se espera al siguiente trozo.
        if (corte + 1 >= this.pendiente.length) return
        if (this.pendiente[corte + 1] === '\n') siguiente = corte + 2
      }
      const linea = this.pendiente.slice(0, corte)
      this.pendiente = this.pendiente.slice(siguiente)
      this.procesarLinea(linea)
    }
  }

  /** Fin del flujo: procesa la última línea sin terminador y entrega el mensaje pendiente, si lo hay. */
  terminar(): void {
    if (this.pendiente) {
      const linea = this.pendiente.replace(/\r$/, '')
      this.pendiente = ''
      this.procesarLinea(linea)
    }
    this.despachar()
  }

  private procesarLinea(linea: string): void {
    if (linea === '') {
      this.despachar()
      return
    }
    if (linea.startsWith(':')) return
    const separador = linea.indexOf(':')
    const campo = separador === -1 ? linea : linea.slice(0, separador)
    let valor = separador === -1 ? '' : linea.slice(separador + 1)
    if (valor.startsWith(' ')) valor = valor.slice(1)
    if (campo === 'event') this.evento = valor
    else if (campo === 'data') this.datos.push(valor)
    // `id`, `retry` y campos desconocidos se ignoran.
  }

  private despachar(): void {
    if (this.datos.length > 0) {
      this.alMensaje({ evento: this.evento || 'message', datos: this.datos.join('\n') })
    }
    this.evento = ''
    this.datos = []
  }
}

/** Interpreta un texto completo (útil en tests y para respuestas ya descargadas). */
export function parsearSse(texto: string): MensajeSse[] {
  const mensajes: MensajeSse[] = []
  const parser = new ParserSse((m) => mensajes.push(m))
  parser.alimentar(texto)
  parser.terminar()
  return mensajes
}

/**
 * Lee el cuerpo de una respuesta `fetch` hasta el final, entregando cada mensaje según llega.
 * Si la petición se aborta (`AbortSignal`), `read()` rechaza y el error se propaga al que llamó.
 */
export async function leerFlujoSse(cuerpo: ReadableStream<Uint8Array>, alMensaje: (mensaje: MensajeSse) => void): Promise<void> {
  const lector = cuerpo.getReader()
  const decodificador = new TextDecoder('utf-8')
  const parser = new ParserSse(alMensaje)
  try {
    for (;;) {
      const { done, value } = await lector.read()
      if (done) break
      parser.alimentar(decodificador.decode(value, { stream: true }))
    }
    parser.alimentar(decodificador.decode())
    parser.terminar()
  } finally {
    lector.releaseLock()
  }
}
