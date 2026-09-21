/**
 * Operaciones: fichero vacío que rellena F4 (CONTRATOS.md §6). F0 solo deja el encabezado y el aviso «En construcción».
 */
import { Construction } from 'lucide-react'

import { EncabezadoPagina } from '@/componentes/shell'

export default function PaginaOperaciones() {
  return (
    <>
      <EncabezadoPagina
        titulo="Operaciones"
        descripcion="Cargas históricas en Airflow (mes o muestra) con sus ejecuciones y simulador de viajes en tiempo real con barra de progreso."
      />
      <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed bg-superficie px-6 py-16 text-center">
        <Construction className="size-7 text-acento" aria-hidden />
        <p className="font-medium">En construcción</p>
        <p className="max-w-md text-texto-suave">Esta sección la completa el bloque F4 del portal.</p>
      </div>
    </>
  )
}
