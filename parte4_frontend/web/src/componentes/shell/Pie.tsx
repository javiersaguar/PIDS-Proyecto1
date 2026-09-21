/**
 * Pie de página: el aviso del escenario E3.
 */
import { Lock } from 'lucide-react'

export const AVISO_E3 = 'Solo agregados protegidos · k = 10'

export function Pie() {
  return (
    <footer className="flex flex-wrap items-center justify-between gap-2 border-t px-6 py-3 text-xs text-texto-suave">
      <p className="flex items-center gap-2">
        <Lock className="size-3.5 text-enmascarado" aria-hidden />
        <span className="font-medium text-foreground">{AVISO_E3}</span>
        <span className="hidden sm:inline">
          · Escenario E3, privacidad total: ninguna respuesta del portal contiene viajes individuales.
        </span>
      </p>
      <p>PIDS 26/27 · Proyecto 1 · Portal web</p>
    </footer>
  )
}
