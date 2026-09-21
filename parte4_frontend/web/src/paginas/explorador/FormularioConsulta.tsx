/**
 * Barra de filtros del explorador, en horizontal: nivel, fuente, ventana, zona o barrio y métricas
 * como selectores. Valida en cliente (`hasta > desde`, rango máximo) antes de lanzar la consulta.
 *
 * El estado se inicializa desde `inicial`; la página lo remonta (con `key`) cuando cambia la
 * consulta de la URL, de modo que una alternativa, un ejemplo o una vista guardada rellenan la barra.
 */
import { ChevronDown, LoaderCircle, Search, Share2, TriangleAlert } from 'lucide-react'
import { useEffect, useId, useMemo, useState, type FormEvent, type ReactNode } from 'react'

import type { Catalogo, Consulta, Fuente, Metrica, Nivel, Zona } from '@/api/tipos'
import { ETIQUETAS_FUENTE, ETIQUETAS_METRICA, ETIQUETAS_NIVEL, METRICAS, NIVELES } from '@/componentes/datos/agregados'
import { Button } from '@/componentes/ui/button'
import { DropdownMenu, DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuTrigger } from '@/componentes/ui/dropdown-menu'
import { Input } from '@/componentes/ui/input'
import { Label } from '@/componentes/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/componentes/ui/select'
import { cn } from '@/lib/utils'

import { BuscadorZona } from './BuscadorZona'
import {
  aConsulta,
  admiteBarrioDestino,
  admiteBarrioOrigen,
  admiteZona,
  BARRIOS_POR_DEFECTO,
  DESCRIPCIONES_NIVEL_POR_DEFECTO,
  esPorHoras,
  MAX_DIAS_POR_DEFECTO,
  validar,
  type Formulario,
} from './consulta'

/** Texto corto del selector cerrado. El desplegable sigue mostrando el nombre completo. */
const ETIQUETA_NIVEL_CORTA: Record<Nivel, string> = {
  hora_zona: 'Hora y zona',
  dia_barrio: 'Día y barrio',
  od_dia_barrio: 'Flujos por día',
}

interface Props {
  inicial: Formulario
  catalogo?: Catalogo
  /** El catálogo no ha podido cargarse: se usan los valores por defecto y se avisa. */
  catalogoNoDisponible?: boolean
  onEnviar: (consulta: Consulta) => void
  /** La consulta que saldría ahora de los filtros, o `null` si no se puede lanzar. */
  onBorrador?: (consulta: Consulta | null) => void
  enviando?: boolean
  onCompartir?: () => void
}

const TODOS = '__todos__'
const HORAS = Array.from({ length: 24 }, (_, h) => h)

function etiquetaHora(h: number): string {
  return `${String(h).padStart(2, '0')}:00`
}

function resumenMetricas(metricas: readonly Metrica[]): string {
  const extras = metricas.filter((m) => m !== 'n_viajes')
  if (extras.length === 0) return 'Viajes'
  if (extras.length === 1) return `Viajes, ${ETIQUETAS_METRICA[extras[0]].toLowerCase()}`
  return `${extras.length + 1} métricas`
}

function Campo({ idCampo, etiqueta, children, className }: { idCampo?: string; etiqueta: string; children: ReactNode; className?: string }) {
  return (
    <div className={cn('flex min-w-0 flex-col gap-1', className)}>
      {idCampo ? (
        <Label htmlFor={idCampo} className="text-[11px] font-medium text-slate-500">
          {etiqueta}
        </Label>
      ) : (
        <span className="text-[11px] font-medium text-slate-500">{etiqueta}</span>
      )}
      {children}
    </div>
  )
}

export function FormularioConsulta({ inicial, catalogo, catalogoNoDisponible, onEnviar, onBorrador, enviando, onCompartir }: Props) {
  const [f, setF] = useState<Formulario>(inicial)
  const [tocado, setTocado] = useState(false)
  const idBase = useId()
  const id = (campo: string) => `${idBase}-${campo}`

  const cambiar = (parcial: Partial<Formulario>) => {
    setTocado(true)
    setF((actual) => ({ ...actual, ...parcial }))
  }

  const maxDias = catalogo?.max_dias_por_consulta ?? MAX_DIAS_POR_DEFECTO
  const barrios = catalogo?.barrios?.length ? catalogo.barrios : BARRIOS_POR_DEFECTO
  const metricasDisponibles = (catalogo?.metricas?.length ? catalogo.metricas : METRICAS) as readonly Metrica[]
  const fuentes = (catalogo?.fuentes?.length ? catalogo.fuentes : (['historico', 'tiempo_real'] as Fuente[])) as readonly Fuente[]
  const errores = useMemo(() => validar(f, maxDias), [f, maxDias])
  const hayErrores = Object.keys(errores).length > 0
  const consulta = useMemo(() => aConsulta(f), [f])
  const porHoras = esPorHoras(f.nivel)

  useEffect(() => {
    onBorrador?.(hayErrores ? null : consulta)
  }, [onBorrador, hayErrores, consulta])

  const enviar = (evento: FormEvent<HTMLFormElement>) => {
    evento.preventDefault()
    setTocado(true)
    if (hayErrores || enviando) return
    onEnviar(consulta)
  }

  const alternarMetrica = (metrica: Metrica, activa: boolean) => {
    if (metrica === 'n_viajes') return
    cambiar({ metricas: activa ? [...f.metricas, metrica] : f.metricas.filter((m) => m !== metrica) })
  }

  return (
    <section className="rounded-2xl border border-slate-200/80 bg-white px-4 py-3 shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
      <form onSubmit={enviar} noValidate aria-label="Formulario de consulta">
        {catalogoNoDisponible && (
          <p role="status" className="mb-3 flex items-start gap-2 rounded-lg border border-aviso/30 bg-aviso/5 px-3 py-2 text-xs text-aviso">
            <TriangleAlert className="mt-0.5 size-3.5 shrink-0" aria-hidden />
            El catálogo no está disponible: se usan los niveles, barrios y límites por defecto.
          </p>
        )}

        <div className="flex items-start gap-3">
          <div className="grid min-w-0 flex-1 grid-cols-[repeat(auto-fit,minmax(8.5rem,1fr))] items-end gap-x-2.5 gap-y-3">
          <Campo idCampo={id('nivel')} etiqueta="Nivel">
            <Select value={f.nivel} onValueChange={(v) => cambiar({ nivel: v as Nivel })}>
              <SelectTrigger id={id('nivel')} type="button" className="w-full bg-white" aria-label="Nivel de agregación" title={catalogo?.niveles?.[f.nivel]?.descripcion ?? DESCRIPCIONES_NIVEL_POR_DEFECTO[f.nivel]}>
                <span className="truncate">{ETIQUETA_NIVEL_CORTA[f.nivel]}</span>
              </SelectTrigger>
              <SelectContent>
                {NIVELES.map((nivel) => (
                  <SelectItem key={nivel} value={nivel}>
                    {ETIQUETAS_NIVEL[nivel]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Campo>

          <Campo idCampo={id('fuente')} etiqueta="Fuente">
            <Select value={f.fuente} onValueChange={(v) => cambiar({ fuente: v as Fuente })}>
              <SelectTrigger id={id('fuente')} type="button" className="w-full bg-white" aria-label="Fuente">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {fuentes.map((fuente) => (
                  <SelectItem key={fuente} value={fuente}>
                    {ETIQUETAS_FUENTE[fuente]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Campo>

          <Campo idCampo={id('desde')} etiqueta="Desde">
            <Input id={id('desde')} type="date" value={f.fechaDesde} onChange={(e) => cambiar({ fechaDesde: e.target.value })} aria-invalid={tocado && !!errores.fechas ? true : undefined} className="bg-white" />
          </Campo>
          {porHoras && (
            <Campo etiqueta="Hora">
              <Select value={String(f.horaDesde)} onValueChange={(v) => cambiar({ horaDesde: Number(v) })}>
                <SelectTrigger id={id('hora-desde')} type="button" className="w-full bg-white" aria-label="Hora de inicio">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {HORAS.map((h) => (
                    <SelectItem key={h} value={String(h)}>
                      {etiquetaHora(h)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Campo>
          )}

          <Campo idCampo={id('hasta')} etiqueta="Hasta">
            <Input
              id={id('hasta')}
              type="date"
              value={f.fechaHasta}
              aria-label="Hasta (no incluido)"
              onChange={(e) => cambiar({ fechaHasta: e.target.value })}
              aria-invalid={tocado && !!(errores.fechas || errores.rango) ? true : undefined}
              className="bg-white"
            />
          </Campo>
          {porHoras && (
            <Campo etiqueta="Hora fin">
              <Select value={String(f.horaHasta)} onValueChange={(v) => cambiar({ horaHasta: Number(v) })}>
                <SelectTrigger id={id('hora-hasta')} type="button" className="w-full bg-white" aria-label="Hora de fin">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {HORAS.map((h) => (
                    <SelectItem key={h} value={String(h)}>
                      {etiquetaHora(h)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Campo>
          )}

          {admiteZona(f.nivel) && (
            <Campo idCampo={id('zona')} etiqueta="Zona">
              <BuscadorZona id={id('zona')} compacto valor={f.zonaOrigen} onCambiar={(zona: Zona | null) => cambiar({ zonaOrigen: zona?._id ?? null })} />
            </Campo>
          )}

          {admiteBarrioOrigen(f.nivel) && (
            <Campo idCampo={id('barrio-origen')} etiqueta="Origen">
              <Select value={f.barrioOrigen ?? TODOS} onValueChange={(v) => cambiar({ barrioOrigen: v === TODOS ? null : v })}>
                <SelectTrigger id={id('barrio-origen')} type="button" className="w-full bg-white" aria-label="Barrio de origen">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={TODOS}>Todos los barrios</SelectItem>
                  {barrios.map((b) => (
                    <SelectItem key={b} value={b}>
                      {b}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Campo>
          )}

          {admiteBarrioDestino(f.nivel) && (
            <Campo idCampo={id('barrio-destino')} etiqueta="Destino">
              <Select value={f.barrioDestino ?? TODOS} onValueChange={(v) => cambiar({ barrioDestino: v === TODOS ? null : v })}>
                <SelectTrigger id={id('barrio-destino')} type="button" className="w-full bg-white" aria-label="Barrio de destino">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={TODOS}>Todos los barrios</SelectItem>
                  {barrios.map((b) => (
                    <SelectItem key={b} value={b}>
                      {b}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Campo>
          )}

          <Campo etiqueta="Métricas">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button type="button" variant="outline" className="w-full justify-between bg-white px-2.5 font-normal" aria-label="Métricas">
                  <span className="truncate">{resumenMetricas(f.metricas)}</span>
                  <ChevronDown className="size-4 text-slate-400" aria-hidden />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="min-w-52" align="start">
                {metricasDisponibles.map((metrica) => {
                  const siempre = metrica === 'n_viajes'
                  const activa = siempre || f.metricas.includes(metrica)
                  return (
                    <DropdownMenuCheckboxItem
                      key={metrica}
                      checked={activa}
                      disabled={siempre}
                      onSelect={(evento) => evento.preventDefault()}
                      onCheckedChange={(v) => alternarMetrica(metrica, v === true)}
                    >
                      {ETIQUETAS_METRICA[metrica] ?? metrica}
                    </DropdownMenuCheckboxItem>
                  )
                })}
              </DropdownMenuContent>
            </DropdownMenu>
          </Campo>
          </div>

          <div className="flex shrink-0 flex-col gap-1">
            <span className="text-[11px] leading-none font-medium text-transparent select-none" aria-hidden>
              Acciones
            </span>
            <div className="flex items-center gap-2">
              {onCompartir && (
                <Button type="button" variant="outline" className="bg-white" onClick={onCompartir}>
                  <Share2 aria-hidden />
                  Copiar enlace
                </Button>
              )}
              <Button type="submit" disabled={enviando || (tocado && hayErrores)}>
                {enviando ? <LoaderCircle className="animate-spin" aria-hidden /> : <Search aria-hidden />}
                {enviando ? 'Consultando…' : 'Consultar'}
              </Button>
            </div>
          </div>
        </div>

        {tocado && (errores.fechas || errores.rango) && (
          <p role="alert" className="mt-2 flex items-start gap-2 text-xs text-peligro">
            <TriangleAlert className="mt-0.5 size-3.5 shrink-0" aria-hidden />
            <span>{errores.fechas ?? errores.rango}</span>
          </p>
        )}
      </form>
    </section>
  )
}
