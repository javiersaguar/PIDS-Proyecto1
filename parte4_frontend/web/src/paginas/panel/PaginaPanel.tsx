/**
 * Panel: fichero vacío que rellena F3 (CONTRATOS.md §6). F0 solo deja el encabezado y el aviso «En construcción».
 */
import { Construction } from 'lucide-react'

import { EncabezadoPagina } from '@/componentes/shell'

export default function PaginaPanel() {
  return (
    <>
      <EncabezadoPagina
        titulo="Panel"
        descripcion="KPIs del último día publicado (total y por barrio), frescura del tiempo real, decisiones de las últimas 24 h, estado de los servicios y accesos directos."
      />
      <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed bg-superficie px-6 py-16 text-center">
        <Construction className="size-7 text-acento" aria-hidden />
        <p className="font-medium">En construcción</p>
        <p className="max-w-md text-texto-suave">Esta sección la completa el bloque F3 del portal.</p>
      </div>
    </>
  )
}
