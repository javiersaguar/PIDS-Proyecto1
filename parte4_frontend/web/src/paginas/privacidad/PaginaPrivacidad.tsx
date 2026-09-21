/**
 * Privacidad (§6): tres pestañas, sin título de página. «Reglas E3» explica las reglas en texto,
 * «Auditoría» lista las decisiones y «Cargas» el resultado de cada carga histórica.
 * La pestaña activa va en la URL (`?pestana=auditoria`) para poder enlazarla.
 */
import { ClipboardList, ScrollText, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { useSearchParams } from 'react-router'

import { HORAS_AUDITORIA } from '@/api/auditoria'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/componentes/ui/tabs'

import { Auditoria } from './Auditoria'
import { Cargas } from './Cargas'
import { ReglasE3 } from './ReglasE3'
import { Segmentado } from './Segmentado'

const OPCIONES_HORAS = HORAS_AUDITORIA.map((h) => ({
  valor: h,
  etiqueta: h === 1 ? '1 hora' : h === 168 ? '7 días' : `${h} horas`,
}))

const PESTANAS = ['reglas', 'auditoria', 'cargas'] as const
type Pestana = (typeof PESTANAS)[number]

function esPestana(valor: string | null): valor is Pestana {
  return (PESTANAS as readonly string[]).includes(valor ?? '')
}

export default function PaginaPrivacidad() {
  const [parametros, setParametros] = useSearchParams()
  const [horas, setHoras] = useState<number>(24)
  const pestana: Pestana = esPestana(parametros.get('pestana')) ? (parametros.get('pestana') as Pestana) : 'reglas'

  const cambiar = (valor: string) => {
    if (!esPestana(valor)) return
    setParametros(
      (previos) => {
        const siguientes = new URLSearchParams(previos)
        if (valor === 'reglas') siguientes.delete('pestana')
        else siguientes.set('pestana', valor)
        return siguientes
      },
      { replace: true },
    )
  }

  return (
    <>
      <h1 className="sr-only">Privacidad</h1>
      <Tabs value={pestana} onValueChange={cambiar} className="gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <TabsList aria-label="Secciones de privacidad">
            <TabsTrigger value="reglas">
              <ShieldCheck aria-hidden />
              Reglas E3
            </TabsTrigger>
            <TabsTrigger value="auditoria">
              <ScrollText aria-hidden />
              Auditoría
            </TabsTrigger>
            <TabsTrigger value="cargas">
              <ClipboardList aria-hidden />
              Cargas
            </TabsTrigger>
          </TabsList>
          {pestana === 'auditoria' && (
            <Segmentado etiqueta="Periodo" opciones={OPCIONES_HORAS} valor={horas} alCambiar={setHoras} />
          )}
        </div>
        <TabsContent value="reglas">
          <ReglasE3 />
        </TabsContent>
        <TabsContent value="auditoria">
          <Auditoria horas={horas} />
        </TabsContent>
        <TabsContent value="cargas">
          <Cargas />
        </TabsContent>
      </Tabs>
    </>
  )
}
