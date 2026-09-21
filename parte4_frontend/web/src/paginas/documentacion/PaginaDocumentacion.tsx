/**
 * Documentación: el lienzo de arquitectura. Cada pieza se explica al pulsarla.
 * Los enlaces salen de `GET /api/panel` o de los puertos por defecto.
 */
import { useEnlaces } from '@/api/operaciones'

import { Lienzo } from './Lienzo'

export default function PaginaDocumentacion() {
  const { enlaces } = useEnlaces()
  return (
    <div className="h-full min-h-0">
      <h1 className="sr-only">Arquitectura de la plataforma</h1>
      <Lienzo enlaces={enlaces} />
    </div>
  )
}
