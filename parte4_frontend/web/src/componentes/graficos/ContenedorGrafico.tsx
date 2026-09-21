/**
 * Contenedor que mide su ancho con `ResizeObserver` y se lo pasa al gráfico, en lugar de `ResponsiveContainer`
 * de Recharts: así el gráfico se dibuja también donde no hay medidas (jsdom en los tests) con un ancho por
 * defecto, sin avisos de «width(0)», y en el navegador se adapta al contenedor.
 */
import { useEffect, useRef, useState, type ReactNode } from 'react'

import { cn } from '@/lib/utils'

export interface Medidas {
  ancho: number
  alto: number
}

interface Props {
  altura: number
  /** Ancho que se usa hasta que el navegador mide el contenedor (y siempre en los tests). */
  anchoInicial?: number
  children: (medidas: Medidas) => ReactNode
  className?: string
}

export function ContenedorGrafico({ altura, anchoInicial = 640, children, className }: Props) {
  const referencia = useRef<HTMLDivElement>(null)
  const [ancho, setAncho] = useState(anchoInicial)

  useEffect(() => {
    const elemento = referencia.current
    if (!elemento || typeof ResizeObserver === 'undefined') return
    // El observador avisa nada más observar (con el tamaño actual) y en cada cambio de tamaño.
    const observador = new ResizeObserver((entradas) => {
      const medido = entradas[0]?.contentRect.width ?? 0
      if (medido > 0) setAncho((actual) => (Math.abs(actual - medido) < 1 ? actual : Math.floor(medido)))
    })
    observador.observe(elemento)
    return () => observador.disconnect()
  }, [])

  return (
    <div ref={referencia} className={cn('w-full overflow-hidden', className)} style={{ height: altura }}>
      {children({ ancho, alto: altura })}
    </div>
  )
}
