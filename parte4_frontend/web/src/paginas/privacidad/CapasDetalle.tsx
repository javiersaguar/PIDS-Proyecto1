/**
 * Detalle de una fila abierta: dos hojas superpuestas, por delante de la fila, para que
 * el contenido se lea como otra superficie y no como más celdas de la tabla.
 */
import type { ReactNode } from 'react'

export function CapasDetalle({ children }: { children: ReactNode }) {
  return (
    <div className="relative px-3 pt-3 pb-6 sm:px-5">
      <div
        aria-hidden
        className="absolute top-6 right-3 bottom-2 left-8 rounded-2xl border border-slate-200 bg-slate-200 shadow-[0_10px_18px_rgb(15_23_42/0.08)] sm:right-5 sm:left-12"
      />
      <div className="relative mr-4 rounded-2xl border border-borde bg-white px-4 py-4 shadow-[0_18px_40px_rgb(15_23_42/0.16)] sm:mr-8 sm:px-5">
        {children}
      </div>
    </div>
  )
}
