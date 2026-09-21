/**
 * Explorador de agregados (§6). Sin título de página: los filtros van en una barra horizontal y el
 * resultado ocupa el resto. La consulta vive en la URL (`?nivel=…&desde=…&hasta=…`), de modo que se puede
 * compartir y el botón «atrás» funciona; el formulario se remonta con ella (`key`) cuando cambia, y el resultado
 * se pide con `useResultadoConsulta` (una sola vez por consulta, aunque React monte dos veces en desarrollo).
 */
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router'
import { toast } from 'sonner'

import { useCatalogo, useResultadoConsulta } from '@/api/consultas'
import type { Consulta } from '@/api/tipos'

import { aFormulario, aParametros, desdeParametros, FORMULARIO_INICIAL } from './consulta'
import { Ejemplos } from './Ejemplos'
import { FormularioConsulta } from './FormularioConsulta'
import { ResultadoConsulta } from './ResultadoConsulta'

export default function PaginaExplorador() {
  const [parametros, setParametros] = useSearchParams()
  const claveUrl = parametros.toString()
  const consulta = useMemo(() => desdeParametros(parametros), [parametros])
  const catalogo = useCatalogo()
  const resultado = useResultadoConsulta(consulta)
  const [borrador, setBorrador] = useState<Consulta | null>(null)

  const lanzar = (nueva: Consulta) => {
    const nuevos = aParametros(nueva)
    if (nuevos.toString() === claveUrl) {
      void resultado.refetch()
    } else {
      setParametros(nuevos)
    }
  }

  const compartir = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href)
      toast.success('Enlace de la consulta copiado')
    } catch {
      toast.error('No se ha podido copiar el enlace; cópialo de la barra de direcciones')
    }
  }

  return (
    <>
      <h1 className="sr-only">Explorador</h1>
      <div className="space-y-4">
        <FormularioConsulta
          key={claveUrl}
          inicial={consulta ? aFormulario(consulta) : FORMULARIO_INICIAL}
          catalogo={catalogo.data}
          catalogoNoDisponible={catalogo.isError}
          onEnviar={lanzar}
          onBorrador={setBorrador}
          enviando={resultado.isFetching}
          onCompartir={consulta ? () => void compartir() : undefined}
        />
        <ResultadoConsulta consulta={consulta} resultado={resultado} onAlternativa={lanzar} />
        <Ejemplos onElegir={lanzar} disabled={resultado.isFetching} borrador={borrador} />
      </div>
    </>
  )
}
