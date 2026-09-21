/**
 * Explorador de agregados (§6). La consulta vive en la URL (`?nivel=…&desde=…&hasta=…`), de modo que se puede
 * compartir y el botón «atrás» funciona; el formulario se remonta con ella (`key`) cuando cambia, y el resultado
 * se pide con `useResultadoConsulta` (una sola vez por consulta, aunque React monte dos veces en desarrollo).
 */
import { Share2 } from 'lucide-react'
import { useMemo } from 'react'
import { useSearchParams } from 'react-router'
import { toast } from 'sonner'

import { useCatalogo, useResultadoConsulta } from '@/api/consultas'
import type { Consulta } from '@/api/tipos'
import { EncabezadoPagina } from '@/componentes/shell'
import { Button } from '@/componentes/ui/button'

import { aFormulario, aParametros, desdeParametros, FORMULARIO_INICIAL } from './consulta'
import { Ejemplos } from './Ejemplos'
import { FormularioConsulta } from './FormularioConsulta'
import { ResultadoConsulta } from './ResultadoConsulta'

const DESCRIPCION =
  'Consultas agregadas por hora y zona, por día y barrio o flujos entre barrios. Cada consulta pasa por el filtro de privacidad de la API de acceso: los grupos con menos de 10 viajes se enmascaran y nunca se suman.'

export default function PaginaExplorador() {
  const [parametros, setParametros] = useSearchParams()
  const claveUrl = parametros.toString()
  const consulta = useMemo(() => desdeParametros(parametros), [parametros])
  const catalogo = useCatalogo()
  const resultado = useResultadoConsulta(consulta)

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
      <EncabezadoPagina
        titulo="Explorador"
        descripcion={DESCRIPCION}
        acciones={
          consulta && (
            <Button variant="outline" size="sm" onClick={() => void compartir()}>
              <Share2 aria-hidden />
              Copiar enlace
            </Button>
          )
        }
      />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,24rem)_minmax(0,1fr)]">
        <div>
          <FormularioConsulta
            key={claveUrl}
            inicial={consulta ? aFormulario(consulta) : FORMULARIO_INICIAL}
            catalogo={catalogo.data}
            catalogoNoDisponible={catalogo.isError}
            onEnviar={lanzar}
            enviando={resultado.isFetching}
          />
        </div>
        <div className="min-w-0 space-y-4">
          <Ejemplos onElegir={lanzar} disabled={resultado.isFetching} />
          <ResultadoConsulta consulta={consulta} resultado={resultado} onAlternativa={lanzar} />
        </div>
      </div>
    </>
  )
}
