/**
 * Privacidad: fichero vacío que rellena F4 (CONTRATOS.md §6). F0 solo deja el encabezado y el aviso «En construcción».
 */
import { Construction } from 'lucide-react'

import { EncabezadoPagina } from '@/componentes/shell'

export default function PaginaPrivacidad() {
  return (
    <>
      <EncabezadoPagina
        titulo="Privacidad"
        descripcion="Reglas del escenario E3 en lenguaje claro, resumen de la auditoría, tabla de decisiones y cargas históricas con sus grupos publicados y suprimidos."
      />
      <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed bg-superficie px-6 py-16 text-center">
        <Construction className="size-7 text-acento" aria-hidden />
        <p className="font-medium">En construcción</p>
        <p className="max-w-md text-texto-suave">Esta sección la completa el bloque F4 del portal.</p>
      </div>
    </>
  )
}
