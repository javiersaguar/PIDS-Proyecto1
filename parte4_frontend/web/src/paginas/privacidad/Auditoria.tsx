/**
 * Pestaña «Auditoría»: `auditoria.decisiones` leída por el BFF con `pids_auditor`. Selector de horas, KPIs por
 * resultado, barras de decisiones por cliente y de motivos de rechazo, y la tabla de decisiones con filtros y
 * filas expandibles (consulta, motivos y alternativa como JSON legible).
 */
import { ChevronDown, ChevronRight, Filter } from 'lucide-react'
import { Fragment, useState } from 'react'

import { HORAS_AUDITORIA, useAuditoriaResumen, useDecisiones } from '@/api/auditoria'
import type { AuditoriaResumen, DecisionAuditada } from '@/api/tipos'
import { abreviar, formatearFechaHora, formatearNumero, jsonLegible } from '@/componentes/chat/formato'
import { EstadoCargando, EstadoError, EstadoNoDisponible, EstadoVacio } from '@/componentes/shell'
import { Badge } from '@/componentes/ui/badge'
import { Button } from '@/componentes/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/componentes/ui/card'
import { Label } from '@/componentes/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/componentes/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/componentes/ui/table'
import { cn } from '@/lib/utils'

import { CLASE_RESULTADO, RESULTADOS, TEXTO_RESULTADO } from './etiquetas'
import { Segmentado } from './Segmentado'

const OPCIONES_HORAS = HORAS_AUDITORIA.map((h) => ({ valor: h, etiqueta: h === 168 ? '7 días' : `${h} h` }))
const OPCIONES_RESULTADO = [{ valor: '', etiqueta: 'Todas' }, ...RESULTADOS.map((r) => ({ valor: r, etiqueta: `${TEXTO_RESULTADO[r]}s` }))]
const TODOS_LOS_CLIENTES = '__todos__'

export function ChipResultado({ resultado }: { resultado: string }) {
  return (
    <Badge variant="outline" className={cn('h-5 px-1.5 font-medium capitalize', CLASE_RESULTADO[resultado] ?? 'bg-muted text-texto-suave')}>
      {TEXTO_RESULTADO[resultado] ?? resultado}
    </Badge>
  )
}

function Kpis({ resumen }: { resumen: AuditoriaResumen }) {
  const resultados = [...RESULTADOS, ...Object.keys(resumen.resultados).filter((r) => !(RESULTADOS as readonly string[]).includes(r))]
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" role="group" aria-label="Resumen por resultado">
      <Card size="sm" className="sombra-tarjeta">
        <CardContent>
          <p className="text-xs font-medium text-texto-suave uppercase">Decisiones</p>
          <p className="cifra text-2xl font-semibold text-primario">{formatearNumero(resumen.total)}</p>
          <p className="text-xs text-texto-suave">
            {formatearFechaHora(resumen.desde)} → {formatearFechaHora(resumen.hasta)}
          </p>
        </CardContent>
      </Card>
      {resultados.map((resultado) => {
        const cantidad = resumen.resultados[resultado] ?? 0
        const porcentaje = resumen.total ? Math.round((cantidad / resumen.total) * 100) : 0
        return (
          <Card key={resultado} size="sm" className="sombra-tarjeta">
            <CardContent>
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-medium text-texto-suave uppercase">{TEXTO_RESULTADO[resultado] ?? resultado}s</p>
                <ChipResultado resultado={resultado} />
              </div>
              <p className="cifra text-2xl font-semibold text-primario">{formatearNumero(cantidad)}</p>
              <p className="cifra text-xs text-texto-suave">{porcentaje} % del total</p>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}

function Barras({ titulo, descripcion, datos, vacio, color = 'bg-primario' }: {
  titulo: string
  descripcion: string
  datos: { etiqueta: string; valor: number }[]
  vacio: string
  color?: string
}) {
  const maximo = Math.max(0, ...datos.map((d) => d.valor))
  return (
    <Card size="sm" className="sombra-tarjeta">
      <CardHeader>
        <CardTitle>{titulo}</CardTitle>
        <CardDescription>{descripcion}</CardDescription>
      </CardHeader>
      <CardContent>
        {datos.length === 0 ? (
          <p className="text-xs text-texto-suave">{vacio}</p>
        ) : (
          <ul className="space-y-2" aria-label={titulo}>
            {datos.map((dato) => (
              <li key={dato.etiqueta} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 text-xs">
                <span className="truncate" title={dato.etiqueta}>
                  {dato.etiqueta}
                </span>
                <span className="cifra font-medium">{formatearNumero(dato.valor)}</span>
                <div className="col-span-2 h-1.5 overflow-hidden rounded-full bg-muted">
                  <div
                    className={cn('h-full rounded-full', color)}
                    style={{ width: `${maximo ? Math.max(2, (dato.valor / maximo) * 100) : 0}%` }}
                    role="presentation"
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

function ResumenDecision({ decision }: { decision: DecisionAuditada }) {
  if (decision.resultado === 'rechazada') {
    const motivo = decision.motivos[0] ?? '—'
    return (
      <span className="text-texto-suave" title={decision.motivos.join(' · ')}>
        {abreviar(motivo, 70)}
        {decision.motivos.length > 1 && <span> (+{decision.motivos.length - 1})</span>}
      </span>
    )
  }
  const partes: string[] = []
  if (typeof decision.consulta.nivel === 'string') partes.push(decision.consulta.nivel)
  if (decision.filas_devueltas !== undefined) partes.push(`${formatearNumero(decision.filas_devueltas)} filas`)
  if (decision.grupos_enmascarados) partes.push(`${formatearNumero(decision.grupos_enmascarados)} enmascarados`)
  return <span className="cifra text-texto-suave">{partes.join(' · ') || '—'}</span>
}

function DetalleDecision({ decision }: { decision: DecisionAuditada }) {
  return (
    <div className="grid gap-3 py-1 text-xs lg:grid-cols-3">
      <div>
        <p className="mb-1 font-medium text-texto-suave">Consulta</p>
        <pre className="max-h-64 overflow-auto rounded-md bg-superficie p-2 font-mono text-[11px] leading-relaxed whitespace-pre-wrap">
          {jsonLegible(decision.consulta)}
        </pre>
      </div>
      <div>
        <p className="mb-1 font-medium text-texto-suave">Motivos</p>
        {decision.motivos.length ? (
          <ul className="list-disc space-y-0.5 pl-4">
            {decision.motivos.map((motivo, indice) => (
              <li key={indice}>{motivo}</li>
            ))}
          </ul>
        ) : (
          <p className="text-texto-suave">Sin motivos: la consulta cumplía las reglas.</p>
        )}
        <p className="mt-2 text-texto-suave">
          Componente: <span className="font-mono text-foreground">{decision.componente}</span>
        </p>
      </div>
      <div>
        <p className="mb-1 font-medium text-texto-suave">Alternativa propuesta</p>
        {decision.alternativa ? (
          <pre className="max-h-64 overflow-auto rounded-md bg-superficie p-2 font-mono text-[11px] leading-relaxed whitespace-pre-wrap">
            {jsonLegible(decision.alternativa)}
          </pre>
        ) : (
          <p className="text-texto-suave">Ninguna.</p>
        )}
      </div>
    </div>
  )
}

const PAGINA = 25

function TablaDecisiones({ decisiones }: { decisiones: DecisionAuditada[] }) {
  const [abiertas, setAbiertas] = useState<Set<number>>(() => new Set())
  const [visibles, setVisibles] = useState(PAGINA)
  const mostradas = decisiones.slice(0, visibles)
  const restantes = decisiones.length - mostradas.length
  const alternar = (indice: number) =>
    setAbiertas((previas) => {
      const siguientes = new Set(previas)
      if (siguientes.has(indice)) siguientes.delete(indice)
      else siguientes.add(indice)
      return siguientes
    })

  return (
    <div className="space-y-3">
    <Table>
      <TableHeader>
        <TableRow className="bg-superficie-alterna/60 hover:bg-superficie-alterna/60">
          <TableHead scope="col" className="w-8">
            <span className="sr-only">Detalle</span>
          </TableHead>
          <TableHead scope="col">Instante</TableHead>
          <TableHead scope="col">Cliente</TableHead>
          <TableHead scope="col">Resultado</TableHead>
          <TableHead scope="col">Consulta / motivos</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {mostradas.map((decision, indice) => {
          const abierta = abiertas.has(indice)
          return (
            <Fragment key={`${decision.instante}-${indice}`}>
              <TableRow className={cn(abierta && 'bg-muted/40')}>
                <TableCell className="py-1">
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    onClick={() => alternar(indice)}
                    aria-expanded={abierta}
                    aria-label={abierta ? 'Ocultar el detalle' : 'Ver el detalle'}
                  >
                    {abierta ? <ChevronDown aria-hidden /> : <ChevronRight aria-hidden />}
                  </Button>
                </TableCell>
                <TableCell className="cifra text-texto-suave">{formatearFechaHora(decision.instante)}</TableCell>
                <TableCell className="font-medium">{decision.cliente}</TableCell>
                <TableCell>
                  <ChipResultado resultado={decision.resultado} />
                </TableCell>
                <TableCell className="max-w-[28rem] truncate">
                  <ResumenDecision decision={decision} />
                </TableCell>
              </TableRow>
              {abierta && (
                <TableRow className="bg-muted/30 hover:bg-muted/30">
                  <TableCell colSpan={5} className="whitespace-normal">
                    <DetalleDecision decision={decision} />
                  </TableCell>
                </TableRow>
              )}
            </Fragment>
          )
        })}
      </TableBody>
    </Table>
    {restantes > 0 && (
      <div className="flex items-center justify-between gap-3 text-xs text-texto-suave">
        <span>
          Mostrando {mostradas.length} de {decisiones.length}.
        </span>
        <Button variant="outline" size="sm" onClick={() => setVisibles((v) => v + PAGINA)}>
          Mostrar {Math.min(PAGINA, restantes)} más
        </Button>
      </div>
    )}
    </div>
  )
}

export function Auditoria() {
  const [horas, setHoras] = useState<number>(24)
  const [resultado, setResultado] = useState('')
  const [cliente, setCliente] = useState('')
  const resumen = useAuditoriaResumen(horas)
  const disponible = resumen.data?.disponible === true
  const decisiones = useDecisiones({ horas, resultado: resultado || undefined, cliente: cliente || undefined, limite: 100 }, disponible)

  const selectorHoras = <Segmentado etiqueta="Periodo" opciones={OPCIONES_HORAS} valor={horas} alCambiar={setHoras} />

  if (resumen.isPending) {
    return (
      <div className="space-y-4">
        {selectorHoras}
        <EstadoCargando variante="tarjeta" lineas={5} etiqueta="Cargando la auditoría…" />
      </div>
    )
  }
  if (resumen.isError) {
    return (
      <div className="space-y-4">
        {selectorHoras}
        <EstadoError
          titulo="No se ha podido leer la auditoría"
          error={resumen.error}
          alReintentar={() => void resumen.refetch()}
          reintentando={resumen.isFetching}
        />
      </div>
    )
  }
  if (!resumen.data.disponible) {
    return (
      <div className="space-y-4">
        {selectorHoras}
        <EstadoNoDisponible
          servicio="MongoDB"
          descripcion="El BFF no ha podido leer la colección auditoria.decisiones con el usuario pids_auditor. El resto del portal sigue funcionando."
          alReintentar={() => void resumen.refetch()}
        />
      </div>
    )
  }

  const datos = resumen.data
  const clientes = Object.entries(datos.clientes)
    .map(([etiqueta, valor]) => ({ etiqueta, valor }))
    .sort((a, b) => b.valor - a.valor)
  const motivos = datos.motivos.slice(0, 8).map((m) => ({ etiqueta: m.motivo, valor: m.cantidad }))

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-texto-suave">
          Cada consulta a la API de acceso deja una decisión (permitida, enmascarada o rechazada) en{' '}
          <code className="font-mono text-[11px]">auditoria.decisiones</code>, que solo admite inserciones.
        </p>
        {selectorHoras}
      </div>

      <Kpis resumen={datos} />

      <div className="grid gap-3 lg:grid-cols-2">
        <Barras
          titulo="Decisiones por cliente"
          descripcion="Quién consulta: el chatbot, este portal (cliente «frontend»), Airflow o el equipo."
          datos={clientes}
          vacio="Ninguna decisión en el periodo."
        />
        <Barras
          titulo="Motivos de rechazo más frecuentes"
          descripcion="Tipo de motivo (el texto antes de «: »), como en scripts/informe_auditoria.py."
          datos={motivos}
          vacio="Ningún rechazo en el periodo."
          color="bg-peligro"
        />
      </div>

      <Card className="sombra-tarjeta">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="size-4 text-texto-suave" aria-hidden />
            Decisiones recientes
          </CardTitle>
          <CardDescription>Las 100 más recientes del periodo que cumplen los filtros; cada fila se despliega para ver el detalle.</CardDescription>
          <div className="mt-2 flex flex-wrap items-end gap-4">
            <Segmentado etiqueta="Resultado" opciones={OPCIONES_RESULTADO} valor={resultado} alCambiar={setResultado} />
            <div className="flex items-center gap-2">
              <Label htmlFor="filtro-cliente" className="text-xs text-texto-suave">
                Cliente
              </Label>
              <Select value={cliente || TODOS_LOS_CLIENTES} onValueChange={(v) => setCliente(v === TODOS_LOS_CLIENTES ? '' : v)}>
                <SelectTrigger id="filtro-cliente" size="sm" className="min-w-40">
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={TODOS_LOS_CLIENTES}>Todos</SelectItem>
                  {clientes.map((c) => (
                    <SelectItem key={c.etiqueta} value={c.etiqueta}>
                      {c.etiqueta}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {decisiones.isPending ? (
            <EstadoCargando lineas={6} etiqueta="Cargando las decisiones…" />
          ) : decisiones.isError ? (
            <EstadoError
              titulo="No se han podido leer las decisiones"
              error={decisiones.error}
              alReintentar={() => void decisiones.refetch()}
              reintentando={decisiones.isFetching}
            />
          ) : decisiones.data.length === 0 ? (
            <EstadoVacio titulo="Sin decisiones" descripcion="Ninguna decisión cumple los filtros en este periodo." />
          ) : (
            <TablaDecisiones decisiones={decisiones.data} />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
