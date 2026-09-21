/**
 * Pestaña «Auditoría»: `auditoria.decisiones` leída por el BFF con `pids_auditor`. Selector de horas, KPIs por
 * resultado, barras de decisiones por cliente y de motivos de rechazo, y la tabla de decisiones. Cada fila
 * dice en una frase qué ocurrió; al abrirla, el detalle sale en dos capas por delante de la fila.
 */
import { ChevronDown, ChevronLeft, ChevronRight, Filter } from 'lucide-react'
import { Fragment, useState, type ReactNode } from 'react'

import { useAuditoriaResumen, useDecisiones } from '@/api/auditoria'
import type { AuditoriaResumen, DecisionAuditada } from '@/api/tipos'
import { formatearFechaHora, formatearNumero } from '@/componentes/chat/formato'
import { EstadoCargando, EstadoError, EstadoNoDisponible, EstadoVacio } from '@/componentes/shell'
import { Badge } from '@/componentes/ui/badge'
import { Button } from '@/componentes/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/componentes/ui/card'
import { Label } from '@/componentes/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/componentes/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/componentes/ui/table'
import { cn } from '@/lib/utils'

import { CapasDetalle } from './CapasDetalle'
import { describirAlternativa, describirConsulta, humanizarMotivo, nombreCliente, resumenDecision } from './explicar'
import { CLASE_RESULTADO, RESULTADOS, TEXTO_RESULTADO } from './etiquetas'
import { Segmentado } from './Segmentado'

const OPCIONES_RESULTADO = [{ valor: '', etiqueta: 'Todas' }, ...RESULTADOS.map((r) => ({ valor: r, etiqueta: `${TEXTO_RESULTADO[r]}s` }))]
const TODOS_LOS_CLIENTES = '__todos__'

export function ChipResultado({ resultado }: { resultado: string }) {
  return (
    <Badge variant="outline" className={cn('h-5 px-2 text-xs font-medium capitalize', CLASE_RESULTADO[resultado] ?? 'bg-muted text-texto-suave')}>
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
          <p className="text-sm font-medium text-texto-suave">Decisiones</p>
          <p className="cifra text-[1.7rem] leading-none font-semibold text-primario">{formatearNumero(resumen.total)}</p>
          <p className="text-sm text-texto-suave">
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
                <p className="text-sm font-medium text-texto-suave">{TEXTO_RESULTADO[resultado] ?? resultado}s</p>
                <ChipResultado resultado={resultado} />
              </div>
              <p className="cifra text-[1.7rem] leading-none font-semibold text-primario">{formatearNumero(cantidad)}</p>
              <p className="cifra text-sm text-texto-suave">{porcentaje} % del total</p>
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
    <Card className="sombra-tarjeta">
      <CardHeader>
        <CardTitle className="text-sm">{titulo}</CardTitle>
        <CardDescription className="text-sm">{descripcion}</CardDescription>
      </CardHeader>
      <CardContent>
        {datos.length === 0 ? (
          <p className="text-sm text-texto-suave">{vacio}</p>
        ) : (
          <ul className="space-y-3" aria-label={titulo}>
            {datos.map((dato, indice) => (
              <li key={`${indice}-${dato.etiqueta}`} className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-x-4 gap-y-2 text-sm">
                <span className="leading-snug">{dato.etiqueta}</span>
                <span className="cifra text-sm font-semibold">{formatearNumero(dato.valor)}</span>
                <div className="col-span-2 h-3 overflow-hidden rounded-full bg-muted">
                  <div
                    className={cn('h-full rounded-full', color)}
                    style={{ width: `${maximo ? Math.max(4, (dato.valor / maximo) * 100) : 0}%` }}
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

function Bloque({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <div>
      <p className="text-sm font-semibold text-primario">{titulo}</p>
      <div className="mt-1.5 space-y-2 text-sm leading-relaxed">{children}</div>
    </div>
  )
}

function DetalleDecision({ decision }: { decision: DecisionAuditada }) {
  const { libre, agregada } = describirConsulta(decision.consulta)
  return (
    <CapasDetalle>
      <div className="grid gap-5 lg:grid-cols-3">
        <Bloque titulo="Qué se preguntó">
          {libre ? <p>«{libre}»</p> : null}
          {agregada ? <p>{agregada.charAt(0).toUpperCase() + agregada.slice(1)}.</p> : null}
          {!libre && !agregada ? <p className="text-texto-suave">No hay más detalle de la consulta.</p> : null}
          <p className="text-sm text-texto-suave">
            La registró {nombreCliente(decision.cliente)}, desde {decision.componente}.
          </p>
        </Bloque>
        <Bloque titulo="Por qué quedó así">
          {decision.motivos.length ? (
            <ul className="space-y-2">
              {decision.motivos.map((motivo, indice) => (
                <li key={`${indice}-${motivo}`}>
                  <p>{humanizarMotivo(motivo)}</p>
                  <p className="text-sm text-texto-suave">{motivo}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p>Cumplía las reglas: se respondió con agregados.</p>
          )}
          {decision.filas_devueltas !== undefined && (
            <p className="text-sm text-texto-suave">
              {formatearNumero(decision.filas_devueltas)} {decision.filas_devueltas === 1 ? 'fila' : 'filas'}
              {decision.grupos_enmascarados
                ? `, ${formatearNumero(decision.grupos_enmascarados)} con la cifra oculta`
                : ', ninguna con la cifra oculta'}
              .
            </p>
          )}
        </Bloque>
        <Bloque titulo="En su lugar">
          {decision.alternativa ? (
            <p>{describirAlternativa(decision.alternativa)}</p>
          ) : (
            <p className="text-texto-suave">No hizo falta proponer otra consulta.</p>
          )}
        </Bloque>
      </div>
    </CapasDetalle>
  )
}

const POR_PAGINA = 12

function TablaDecisiones({ decisiones }: { decisiones: DecisionAuditada[] }) {
  const [abiertas, setAbiertas] = useState<Set<number>>(() => new Set())
  const [pagina, setPagina] = useState(0)
  const paginas = Math.max(1, Math.ceil(decisiones.length / POR_PAGINA))
  const actual = Math.min(pagina, paginas - 1)
  const inicio = actual * POR_PAGINA
  const mostradas = decisiones.slice(inicio, inicio + POR_PAGINA)
  const ir = (siguiente: number) => {
    setPagina(siguiente)
    setAbiertas(new Set())
  }
  const alternar = (indice: number) =>
    setAbiertas((previas) => {
      const siguientes = new Set(previas)
      if (siguientes.has(indice)) siguientes.delete(indice)
      else siguientes.add(indice)
      return siguientes
    })

  return (
    <div className="space-y-3">
    <Table className="text-sm">
      <TableHeader>
        <TableRow className="bg-superficie-alterna/60 hover:bg-superficie-alterna/60">
          <TableHead scope="col" className="w-8">
            <span className="sr-only">Detalle</span>
          </TableHead>
          <TableHead scope="col">Instante</TableHead>
          <TableHead scope="col">Cliente</TableHead>
          <TableHead scope="col">Resultado</TableHead>
          <TableHead scope="col">Qué pasó</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {mostradas.map((decision, indice) => {
          const abierta = abiertas.has(indice)
          return (
            <Fragment key={`${decision.instante}-${indice}`}>
              <TableRow
                className={cn('cursor-pointer', abierta && 'bg-slate-100 hover:bg-slate-100')}
                onClick={() => alternar(indice)}
              >
                <TableCell className="py-1">
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    onClick={(evento) => {
                      evento.stopPropagation()
                      alternar(indice)
                    }}
                    aria-expanded={abierta}
                    aria-label={abierta ? 'Ocultar el detalle' : 'Ver el detalle'}
                  >
                    {abierta ? <ChevronDown aria-hidden /> : <ChevronRight aria-hidden />}
                  </Button>
                </TableCell>
                <TableCell className="cifra text-texto-suave">{formatearFechaHora(decision.instante)}</TableCell>
                <TableCell className="font-medium">{nombreCliente(decision.cliente)}</TableCell>
                <TableCell>
                  <ChipResultado resultado={decision.resultado} />
                </TableCell>
                <TableCell className="max-w-xl whitespace-normal text-texto-suave">{resumenDecision(decision)}</TableCell>
              </TableRow>
              {abierta && (
                <TableRow className="bg-slate-50 hover:bg-slate-50">
                  <TableCell colSpan={5} className="p-0 whitespace-normal">
                    <DetalleDecision decision={decision} />
                  </TableCell>
                </TableRow>
              )}
            </Fragment>
          )
        })}
      </TableBody>
    </Table>
    {paginas > 1 && (
      <div className="flex items-center justify-between gap-3 text-sm text-texto-suave">
        <span>
          {inicio + 1}–{inicio + mostradas.length} de {decisiones.length}
        </span>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" disabled={actual === 0} onClick={() => ir(actual - 1)}>
            <ChevronLeft aria-hidden />
            Anterior
          </Button>
          <span className="cifra">
            {actual + 1} / {paginas}
          </span>
          <Button variant="outline" size="sm" disabled={actual >= paginas - 1} onClick={() => ir(actual + 1)}>
            Siguiente
            <ChevronRight aria-hidden />
          </Button>
        </div>
      </div>
    )}
    </div>
  )
}

/** Varios motivos crudos pueden decirse igual; se suman para que la barra y su clave sean únicas. */
function agruparMotivos(motivos: { motivo: string; cantidad: number }[]): { etiqueta: string; valor: number }[] {
  const acumulado = new Map<string, number>()
  for (const item of motivos) {
    const etiqueta = humanizarMotivo(item.motivo)
    acumulado.set(etiqueta, (acumulado.get(etiqueta) ?? 0) + item.cantidad)
  }
  return [...acumulado.entries()]
    .map(([etiqueta, valor]) => ({ etiqueta, valor }))
    .sort((a, b) => b.valor - a.valor)
    .slice(0, 8)
}

export function Auditoria({ horas }: { horas: number }) {
  const [resultado, setResultado] = useState('')
  const [cliente, setCliente] = useState('')
  const resumen = useAuditoriaResumen(horas)
  const disponible = resumen.data?.disponible === true
  const decisiones = useDecisiones({ horas, resultado: resultado || undefined, cliente: cliente || undefined, limite: 100 }, disponible)

  if (resumen.isPending) {
    return <EstadoCargando variante="tarjeta" lineas={5} etiqueta="Cargando la auditoría…" />
  }
  if (resumen.isError) {
    return (
      <EstadoError
        titulo="No se ha podido leer la auditoría"
        error={resumen.error}
        alReintentar={() => void resumen.refetch()}
        reintentando={resumen.isFetching}
      />
    )
  }
  if (!resumen.data.disponible) {
    return (
      <EstadoNoDisponible
          servicio="MongoDB"
          descripcion="El BFF no ha podido leer la colección auditoria.decisiones con el usuario pids_auditor. El resto del portal sigue funcionando."
          alReintentar={() => void resumen.refetch()}
        />
    )
  }

  const datos = resumen.data
  const clientes = Object.entries(datos.clientes)
    .map(([etiqueta, valor]) => ({ etiqueta, valor }))
    .sort((a, b) => b.valor - a.valor)
  const motivos = agruparMotivos(datos.motivos)
  const clientesLegibles = clientes.map((c) => ({ ...c, etiqueta: nombreCliente(c.etiqueta) }))

  return (
    <div className="space-y-4">
      <Kpis resumen={datos} />

      <div className="grid gap-4 lg:grid-cols-2">
        <Barras
          titulo="Decisiones por cliente"
          descripcion="Quién ha consultado en este periodo: el chatbot, este portal, Airflow o el equipo."
          datos={clientesLegibles}
          vacio="Ninguna decisión en el periodo."
        />
        <Barras
          titulo="Motivos de rechazo más frecuentes"
          descripcion="Agrupados por el tipo de motivo, sin el detalle de cada consulta."
          datos={motivos}
          vacio="Ningún rechazo en el periodo."
          color="bg-peligro"
        />
      </div>

      <Card className="sombra-tarjeta">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Filter className="size-4 text-texto-suave" aria-hidden />
            Consultas recientes
          </CardTitle>
          <CardDescription className="text-sm">Doce por página. Abre una fila para leer qué se pidió y cómo se resolvió.</CardDescription>
          <div className="mt-2 flex flex-wrap items-center gap-4">
            <Segmentado etiqueta="Resultado" opciones={OPCIONES_RESULTADO} valor={resultado} alCambiar={setResultado} />
            <div className="flex items-center gap-2">
              <Label htmlFor="filtro-cliente" className="text-sm text-texto-suave">
                Cliente
              </Label>
              <Select value={cliente || TODOS_LOS_CLIENTES} onValueChange={(v) => setCliente(v === TODOS_LOS_CLIENTES ? '' : v)}>
                <SelectTrigger id="filtro-cliente" className="min-w-44 text-sm">
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={TODOS_LOS_CLIENTES}>Todos</SelectItem>
                  {clientes.map((c) => (
                    <SelectItem key={c.etiqueta} value={c.etiqueta}>
                      {nombreCliente(c.etiqueta)}
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
            <TablaDecisiones key={`${horas}|${resultado}|${cliente}`} decisiones={decisiones.data} />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
