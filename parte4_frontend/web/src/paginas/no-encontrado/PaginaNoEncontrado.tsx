/**
 * Ruta `*` dentro del shell: página «No encontrado».
 */
import { Compass } from 'lucide-react'
import { Link, useLocation } from 'react-router'

import { EncabezadoPagina } from '@/componentes/shell'
import { Button } from '@/componentes/ui/button'

export default function PaginaNoEncontrado() {
  const { pathname } = useLocation()
  return (
    <>
      <EncabezadoPagina titulo="Página no encontrada" descripcion="La dirección no corresponde a ninguna sección del portal." />
      <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed bg-superficie px-6 py-16 text-center">
        <Compass className="size-7 text-texto-suave" aria-hidden />
        <p className="font-medium">
          No existe <code className="rounded bg-muted px-1.5 py-0.5 text-[13px]">{pathname}</code>
        </p>
        <Button asChild variant="outline" size="sm">
          <Link to="/">Volver al panel</Link>
        </Button>
      </div>
    </>
  )
}
