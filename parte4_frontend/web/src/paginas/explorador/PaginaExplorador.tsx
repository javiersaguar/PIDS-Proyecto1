/**
 * Explorador: fichero vacío que rellena F3 (CONTRATOS.md §6). F0 solo deja el encabezado y el aviso «En construcción».
 */
import { Construction } from 'lucide-react'

import { EncabezadoPagina } from '@/componentes/shell'

export default function PaginaExplorador() {
  return (
    <>
      <EncabezadoPagina
        titulo="Explorador"
        descripcion="Consultas agregadas (nivel, fuente, fechas, zona, barrios y métricas) con tabla, gráfico y nota de privacidad; los grupos con menos de 10 viajes aparecen como «<10»."
      />
      <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed bg-superficie px-6 py-16 text-center">
        <Construction className="size-7 text-acento" aria-hidden />
        <p className="font-medium">En construcción</p>
        <p className="max-w-md text-texto-suave">Esta sección la completa el bloque F3 del portal.</p>
      </div>
    </>
  )
}
