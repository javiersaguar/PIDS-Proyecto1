/**
 * Privacidad (§6): tres pestañas. «Reglas E3» (las reglas leídas del catálogo de la API de acceso y una explicación
 * en lenguaje claro), «Auditoría» (resumen y tabla de `auditoria.decisiones`, con filtros) y «Cargas» (resúmenes
 * de `auditoria.cargas`). La pestaña activa va en la URL (`?pestana=auditoria`) para poder enlazarla.
 */
import { ClipboardList, ScrollText, ShieldCheck } from 'lucide-react'
import { useSearchParams } from 'react-router'

import { EncabezadoPagina } from '@/componentes/shell'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/componentes/ui/tabs'

import { Auditoria } from './Auditoria'
import { Cargas } from './Cargas'
import { ReglasE3 } from './ReglasE3'

const PESTANAS = ['reglas', 'auditoria', 'cargas'] as const
type Pestana = (typeof PESTANAS)[number]

function esPestana(valor: string | null): valor is Pestana {
  return (PESTANAS as readonly string[]).includes(valor ?? '')
}

export default function PaginaPrivacidad() {
  const [parametros, setParametros] = useSearchParams()
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
      <EncabezadoPagina
        titulo="Privacidad"
        descripcion="Las reglas del escenario E3 tal y como las aplica la API de acceso, la auditoría de cada decisión y el resultado de las cargas históricas."
      />
      <Tabs value={pestana} onValueChange={cambiar} className="gap-4">
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
        <TabsContent value="reglas">
          <ReglasE3 />
        </TabsContent>
        <TabsContent value="auditoria">
          <Auditoria />
        </TabsContent>
        <TabsContent value="cargas">
          <Cargas />
        </TabsContent>
      </Tabs>
    </>
  )
}
