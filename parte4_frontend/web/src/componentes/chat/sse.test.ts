import { describe, expect, it } from 'vitest'

import { ParserSse, leerFlujoSse, parsearSse, type MensajeSse } from './sse'

function recolector() {
  const mensajes: MensajeSse[] = []
  const parser = new ParserSse((m) => mensajes.push(m))
  return { mensajes, parser }
}

describe('ParserSse', () => {
  it('separa event y data y entrega un mensaje por bloque', () => {
    const mensajes = parsearSse('event: paso\ndata: {"nombre":"buscar_zona"}\n\nevent: respuesta\ndata: {"respuesta":"hola"}\n\n')
    expect(mensajes).toEqual([
      { evento: 'paso', datos: '{"nombre":"buscar_zona"}' },
      { evento: 'respuesta', datos: '{"respuesta":"hola"}' },
    ])
  })

  it('admite terminadores \\r\\n (los de sse-starlette) y \\r sueltos', () => {
    expect(parsearSse('event: paso\r\ndata: 1\r\n\r\nevent: paso\rdata: 2\r\r')).toEqual([
      { evento: 'paso', datos: '1' },
      { evento: 'paso', datos: '2' },
    ])
  })

  it('recompone bloques partidos entre trozos, incluso a mitad de línea y de un \\r\\n', () => {
    const { mensajes, parser } = recolector()
    parser.alimentar('event: pa')
    parser.alimentar('so\r')
    expect(mensajes).toHaveLength(0)
    parser.alimentar('\ndata: {"a":')
    parser.alimentar('1}\r\n\r\nevent: respu')
    expect(mensajes).toEqual([{ evento: 'paso', datos: '{"a":1}' }])
    parser.alimentar('esta\ndata: fin\n\n')
    expect(mensajes[1]).toEqual({ evento: 'respuesta', datos: 'fin' })
  })

  it('ignora comentarios, id y retry, y usa «message» si no hay event', () => {
    const mensajes = parsearSse(': latido\n\n: otro comentario\nid: 7\nretry: 3000\ndata: sin tipo\n\n')
    expect(mensajes).toEqual([{ evento: 'message', datos: 'sin tipo' }])
  })

  it('une varias líneas data con saltos de línea y quita solo el primer espacio', () => {
    const mensajes = parsearSse('data: primera\ndata:  segunda con dos espacios\ndata\n\n')
    expect(mensajes).toEqual([{ evento: 'message', datos: 'primera\n segunda con dos espacios\n' }])
  })

  it('un bloque con event pero sin data no se entrega y no contamina al siguiente', () => {
    const mensajes = parsearSse('event: vacio\n\ndata: x\n\n')
    expect(mensajes).toEqual([{ evento: 'message', datos: 'x' }])
  })

  it('al terminar entrega el último mensaje aunque falte la línea en blanco final', () => {
    const { mensajes, parser } = recolector()
    parser.alimentar('event: respuesta\ndata: {"respuesta":"final"}')
    expect(mensajes).toHaveLength(0)
    parser.terminar()
    expect(mensajes).toEqual([{ evento: 'respuesta', datos: '{"respuesta":"final"}' }])
  })
})

describe('leerFlujoSse', () => {
  it('lee un ReadableStream por trozos y entrega los mensajes según llegan', async () => {
    const codificador = new TextEncoder()
    const trozos = ['event: paso\ndata: {"n":1}\n\nevent: pa', 'so\ndata: {"n":2}\n\n', 'event: respuesta\ndata: ñandú\n\n']
    const flujo = new ReadableStream<Uint8Array>({
      start(controlador) {
        for (const trozo of trozos) controlador.enqueue(codificador.encode(trozo))
        controlador.close()
      },
    })
    const mensajes: MensajeSse[] = []
    await leerFlujoSse(flujo, (m) => mensajes.push(m))
    expect(mensajes).toEqual([
      { evento: 'paso', datos: '{"n":1}' },
      { evento: 'paso', datos: '{"n":2}' },
      { evento: 'respuesta', datos: 'ñandú' },
    ])
  })

  it('no rompe un carácter multibyte partido entre dos trozos', async () => {
    const bytes = new TextEncoder().encode('data: año\n\n')
    const flujo = new ReadableStream<Uint8Array>({
      start(controlador) {
        controlador.enqueue(bytes.slice(0, 8))   // corta la «ñ» (2 bytes) por la mitad
        controlador.enqueue(bytes.slice(8))
        controlador.close()
      },
    })
    const mensajes: MensajeSse[] = []
    await leerFlujoSse(flujo, (m) => mensajes.push(m))
    expect(mensajes).toEqual([{ evento: 'message', datos: 'año' }])
  })
})
