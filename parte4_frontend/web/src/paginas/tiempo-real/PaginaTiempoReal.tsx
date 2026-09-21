/**
 * Tiempo real: fichero vacío que rellena F3 (CONTRATOS.md §6). F0 solo deja el encabezado y el aviso «En construcción».
 */
import { Construction } from 'lucide-react'

import { EncabezadoPagina } from '@/componentes/shell'

export default function PaginaTiempoReal() {
  return (
    <>
      <EncabezadoPagina
        titulo="Tiempo real"
        descripcion="Frescura del flujo de captura, viajes por hora de las últimas horas y tabla de la última hora por zona; se refresca cada 30 s."
      />
      <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed bg-superficie px-6 py-16 text-center">
        <Construction className="size-7 text-acento" aria-hidden />
        <p className="font-medium">En construcción</p>
        <p className="max-w-md text-texto-suave">Esta sección la completa el bloque F3 del portal.</p>
      </div>
    </>
  )
}
