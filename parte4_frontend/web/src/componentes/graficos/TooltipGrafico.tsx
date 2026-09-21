/**
 * Contenido del tooltip de Recharts con formato español: etiqueta arriba y una línea por serie con su color.
 * Una serie puede describir su valor con `describirEntrada` (por ejemplo, «2 grupos enmascarados»).
 */
import type { TooltipContentProps } from 'recharts'

import { formatearEntero } from '@/componentes/datos/formato'

export interface EntradaDescrita {
  texto: string
  enmascarado?: boolean
}

export type DescribirEntrada = (
  clave: string | number | undefined,
  valor: unknown,
  punto: Record<string, unknown>,
) => EntradaDescrita | null | undefined

type Props = Partial<TooltipContentProps> & {
  formatearEtiqueta?: (etiqueta: string | number) => string
  formatearValor?: (valor: number) => string
  /** Personaliza (o descarta, devolviendo `null`) el texto de una entrada. */
  describirEntrada?: DescribirEntrada
  /** Líneas adicionales calculadas a partir del punto activo. */
  detalle?: (punto: Record<string, unknown>) => string | null | undefined
}

export function TooltipGrafico({ active, payload, label, formatearEtiqueta, formatearValor = formatearEntero, describirEntrada, detalle }: Props) {
  if (!active || !payload?.length) return null
  const punto = (payload[0]?.payload ?? {}) as Record<string, unknown>
  const etiqueta = label !== undefined && label !== null ? (formatearEtiqueta ? formatearEtiqueta(label) : String(label)) : null
  const lineaDetalle = detalle?.(punto)

  return (
    <div className="min-w-36 rounded-md border bg-superficie px-3 py-2 text-xs shadow-md">
      {etiqueta && <p className="mb-1 font-semibold text-foreground">{etiqueta}</p>}
      <ul className="space-y-0.5">
        {payload.map((entrada, indice) => {
          const descrita = describirEntrada?.(entrada.dataKey as string | number | undefined, entrada.value, punto)
          if (descrita === null) return null
          const valor = entrada.value
          const texto =
            descrita?.texto ??
            (typeof valor === 'number' ? formatearValor(valor) : valor === undefined || valor === null ? '—' : String(valor))
          return (
            <li key={`${String(entrada.dataKey ?? entrada.name)}-${indice}`} className="flex items-center justify-between gap-4">
              <span className="flex items-center gap-1.5 text-texto-suave">
                <span className="size-2 rounded-full" style={{ background: descrita?.enmascarado ? 'var(--enmascarado)' : entrada.color ?? 'var(--chart-1)' }} aria-hidden />
                {String(entrada.name ?? entrada.dataKey ?? '')}
              </span>
              <span className={descrita?.enmascarado ? 'cifra font-semibold text-enmascarado' : 'cifra font-semibold'}>{texto}</span>
            </li>
          )
        })}
      </ul>
      {lineaDetalle && <p className="mt-1 text-texto-suave">{lineaDetalle}</p>}
    </div>
  )
}
