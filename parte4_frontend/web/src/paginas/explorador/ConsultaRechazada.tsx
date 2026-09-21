/**
 * Tarjeta «Consulta rechazada por privacidad» (403 de `POST /api/consultas`): los motivos como lista, la
 * alternativa que propone la API descrita en lenguaje natural y el botón «Consultar la alternativa», que rellena
 * el formulario con ella y la lanza.
 */
import { ArrowRight, ShieldBan } from 'lucide-react'
import { useMemo } from 'react'

import { useZonas } from '@/api/consultas'
import type { Consulta, Decision } from '@/api/tipos'
import { ChipResultado } from '@/componentes/datos'
import { Button } from '@/componentes/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/componentes/ui/card'

import { describirConsulta } from './consulta'

interface Props {
  decision: Decision
  consulta: Consulta
  onAlternativa: (consulta: Consulta) => void
  enviando?: boolean
}

export function ConsultaRechazada({ decision, consulta, onAlternativa, enviando }: Props) {
  const alternativa = decision.alternativa
  const necesitaZonas = consulta.zona_origen != null || alternativa?.zona_origen != null
  const zonas = useZonas('', { habilitado: necesitaZonas })
  const nombresZona = useMemo(() => new Map((zonas.data ?? []).map((z) => [z._id, z.nombre] as const)), [zonas.data])

  return (
    <Card role="alert" className="sombra-tarjeta border-l-4 border-l-peligro">
      <CardHeader>
        <div className="flex items-center gap-2">
          <ShieldBan className="size-5 text-peligro" aria-hidden />
          <CardTitle className="text-xl text-primario">Consulta rechazada por privacidad</CardTitle>
          <ChipResultado resultado="rechazada" />
        </div>
        <CardDescription>
          La API de acceso no ha respondido a <span className="font-medium text-foreground">{describirConsulta(consulta, nombresZona)}</span>. La decisión
          queda registrada en la auditoría.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="mb-1.5 text-sm font-medium">Motivos</p>
          <ul className="list-disc space-y-1 pl-5 text-sm" aria-label="Motivos del rechazo">
            {decision.motivos.map((motivo, indice) => (
              <li key={`${indice}-${motivo}`}>{motivo}</li>
            ))}
          </ul>
        </div>
        {alternativa ? (
          <div className="rounded-lg border border-ok/30 bg-ok/5 p-3">
            <p className="text-sm font-medium text-ok">Alternativa que sí se puede responder</p>
            <p className="mt-1 text-sm">{describirConsulta(alternativa, nombresZona)}</p>
            <Button type="button" className="mt-3" onClick={() => onAlternativa(alternativa)} disabled={enviando}>
              Consultar la alternativa
              <ArrowRight aria-hidden />
            </Button>
          </div>
        ) : (
          <p className="text-sm text-texto-suave">La API no ha propuesto ninguna alternativa para esta consulta.</p>
        )}
      </CardContent>
    </Card>
  )
}
