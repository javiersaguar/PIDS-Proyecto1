/**
 * Formulario de consulta del explorador: nivel (con su descripción del catálogo), fuente, ventana temporal
 * alineada al nivel (horas en punto en `hora_zona`, días completos en los demás; el fin no se incluye), zona con
 * buscador, barrios y métricas. Valida en cliente (`hasta > desde`, rango máximo) antes de lanzar la consulta.
 *
 * El estado del formulario se inicializa desde `inicial`; la página lo remonta (con `key`) cuando cambia la
 * consulta de la URL, de modo que una alternativa o un ejemplo rellenan el formulario.
 */
import { LoaderCircle, Search, TriangleAlert } from 'lucide-react'
import { useId, useMemo, useState, type FormEvent } from 'react'

import type { Catalogo, Consulta, Fuente, Metrica, Zona } from '@/api/tipos'
import { DESCRIPCIONES_METRICA, ETIQUETAS_FUENTE, ETIQUETAS_METRICA, ETIQUETAS_NIVEL, METRICAS, NIVELES } from '@/componentes/datos/agregados'
import { Button } from '@/componentes/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/componentes/ui/card'
import { Input } from '@/componentes/ui/input'
import { Label } from '@/componentes/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/componentes/ui/select'
import { Switch } from '@/componentes/ui/switch'
import { cn } from '@/lib/utils'

import { BuscadorZona } from './BuscadorZona'
import {
  aConsulta,
  admiteBarrioDestino,
  admiteBarrioOrigen,
  admiteZona,
  BARRIOS_POR_DEFECTO,
  DESCRIPCIONES_NIVEL_POR_DEFECTO,
  describirVentana,
  esPorHoras,
  MAX_DIAS_POR_DEFECTO,
  validar,
  type Formulario,
} from './consulta'

interface Props {
  inicial: Formulario
  catalogo?: Catalogo
  /** El catálogo no ha podido cargarse: se usan los valores por defecto y se avisa. */
  catalogoNoDisponible?: boolean
  onEnviar: (consulta: Consulta) => void
  enviando?: boolean
}

const TODOS = '__todos__'
const HORAS = Array.from({ length: 24 }, (_, h) => h)

function etiquetaHora(h: number): string {
  return `${String(h).padStart(2, '0')}:00`
}

export function FormularioConsulta({ inicial, catalogo, catalogoNoDisponible, onEnviar, enviando }: Props) {
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
  const errores = useMemo(() => validar(f, maxDias), [f, maxDias])
  const hayErrores = Object.keys(errores).length > 0
  const consulta = useMemo(() => aConsulta(f), [f])
  const porHoras = esPorHoras(f.nivel)

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
    <Card className="sombra-tarjeta">
      <CardHeader>
        <CardTitle className="text-xl text-primario">Consulta</CardTitle>
        <CardDescription>
          Solo agregados: k = {catalogo?.k_minimo ?? 10}, ventanas alineadas al nivel y como mucho {maxDias} días por consulta.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={enviar} className="space-y-5" noValidate aria-label="Formulario de consulta">
          {catalogoNoDisponible && (
            <p role="status" className="flex items-start gap-2 rounded-md border border-aviso/30 bg-aviso/5 px-3 py-2 text-xs text-aviso">
              <TriangleAlert className="mt-0.5 size-3.5 shrink-0" aria-hidden />
              El catálogo no está disponible: se usan los niveles, barrios y límites por defecto.
            </p>
          )}

          <fieldset className="space-y-2">
            <legend className="mb-2 text-sm font-medium">Nivel de agregación</legend>
            <div role="radiogroup" aria-label="Nivel de agregación" className="grid gap-2">
              {NIVELES.map((nivel) => {
                const activo = f.nivel === nivel
                return (
                  <button
                    key={nivel}
                    type="button"
                    role="radio"
                    aria-checked={activo}
                    onClick={() => cambiar({ nivel })}
                    className={cn(
                      'rounded-lg border px-3 py-2 text-left transition-colors hover:bg-muted',
                      activo ? 'border-primario bg-primario/5 ring-1 ring-primario' : 'border-borde',
                    )}
                  >
                    <span className="block text-sm font-medium">{ETIQUETAS_NIVEL[nivel]}</span>
                    <span className="block text-xs text-texto-suave">{catalogo?.niveles?.[nivel]?.descripcion ?? DESCRIPCIONES_NIVEL_POR_DEFECTO[nivel]}</span>
                  </button>
                )
              })}
            </div>
          </fieldset>

          <fieldset>
            <legend className="mb-2 text-sm font-medium">Fuente</legend>
            <div role="radiogroup" aria-label="Fuente" className="inline-flex rounded-lg border p-0.5">
              {(catalogo?.fuentes?.length ? catalogo.fuentes : (['historico', 'tiempo_real'] as Fuente[])).map((fuente) => (
                <button
                  key={fuente}
                  type="button"
                  role="radio"
                  aria-checked={f.fuente === fuente}
                  onClick={() => cambiar({ fuente })}
                  className={cn(
                    'rounded-md px-3 py-1 text-sm font-medium transition-colors',
                    f.fuente === fuente ? 'bg-primario text-white shadow-sm' : 'text-texto-suave hover:text-foreground',
                  )}
                >
                  {ETIQUETAS_FUENTE[fuente]}
                </button>
              ))}
            </div>
          </fieldset>

          <fieldset className="space-y-3">
            <legend className="mb-2 text-sm font-medium">Ventana temporal</legend>
            <div className={cn('grid gap-3', porHoras ? 'grid-cols-[1fr_auto]' : 'grid-cols-1')}>
              <div className="space-y-1.5">
                <Label htmlFor={id('desde')}>Desde</Label>
                <Input id={id('desde')} type="date" value={f.fechaDesde} onChange={(e) => cambiar({ fechaDesde: e.target.value })} aria-invalid={tocado && !!errores.fechas ? true : undefined} />
              </div>
              {porHoras && (
                <div className="space-y-1.5">
                  <Label htmlFor={id('hora-desde')}>Hora</Label>
                  <Select value={String(f.horaDesde)} onValueChange={(v) => cambiar({ horaDesde: Number(v) })}>
                    <SelectTrigger id={id('hora-desde')} className="w-24" aria-label="Hora de inicio">
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
                </div>
              )}
              <div className="space-y-1.5">
                <Label htmlFor={id('hasta')}>Hasta (no incluido)</Label>
                <Input id={id('hasta')} type="date" value={f.fechaHasta} onChange={(e) => cambiar({ fechaHasta: e.target.value })} aria-invalid={tocado && !!(errores.fechas || errores.rango) ? true : undefined} />
              </div>
              {porHoras && (
                <div className="space-y-1.5">
                  <Label htmlFor={id('hora-hasta')}>Hora</Label>
                  <Select value={String(f.horaHasta)} onValueChange={(v) => cambiar({ horaHasta: Number(v) })}>
                    <SelectTrigger id={id('hora-hasta')} className="w-24" aria-label="Hora de fin">
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
                </div>
              )}
            </div>
            <p className="text-xs text-texto-suave">
              {porHoras
                ? 'Horas en punto; el fin no se incluye: de 08:00 a 12:00 cubre las horas 8, 9, 10 y 11. Un día completo va de las 00:00 a las 00:00 del día siguiente.'
                : 'Días completos; el fin no se incluye: para un solo día, indica el día siguiente como fin.'}
              {!hayErrores && (
                <>
                  {' '}
                  Ventana: <span className="font-medium text-foreground">{describirVentana(consulta)}</span>.
                </>
              )}
            </p>
            {tocado && (errores.fechas || errores.rango) && (
              <p role="alert" className="flex items-start gap-2 text-xs text-peligro">
                <TriangleAlert className="mt-0.5 size-3.5 shrink-0" aria-hidden />
                <span>{errores.fechas ?? errores.rango}</span>
              </p>
            )}
          </fieldset>

          {admiteZona(f.nivel) && (
            <div className="space-y-1.5">
              <Label htmlFor={id('zona')}>Zona de origen</Label>
              <BuscadorZona id={id('zona')} valor={f.zonaOrigen} onCambiar={(zona: Zona | null) => cambiar({ zonaOrigen: zona?._id ?? null })} />
            </div>
          )}

          {admiteBarrioOrigen(f.nivel) && (
            <div className="space-y-1.5">
              <Label htmlFor={id('barrio-origen')}>Barrio de origen</Label>
              <Select value={f.barrioOrigen ?? TODOS} onValueChange={(v) => cambiar({ barrioOrigen: v === TODOS ? null : v })}>
                <SelectTrigger id={id('barrio-origen')} className="w-full">
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
            </div>
          )}

          {admiteBarrioDestino(f.nivel) && (
            <div className="space-y-1.5">
              <Label htmlFor={id('barrio-destino')}>Barrio de destino</Label>
              <Select value={f.barrioDestino ?? TODOS} onValueChange={(v) => cambiar({ barrioDestino: v === TODOS ? null : v })}>
                <SelectTrigger id={id('barrio-destino')} className="w-full">
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
            </div>
          )}

          <fieldset>
            <legend className="mb-2 text-sm font-medium">Métricas</legend>
            <ul className="space-y-2">
              {metricasDisponibles.map((metrica) => {
                const siempre = metrica === 'n_viajes'
                const activa = siempre || f.metricas.includes(metrica)
                return (
                  <li key={metrica} className="flex items-start justify-between gap-3">
                    <Label htmlFor={id(`metrica-${metrica}`)} className="flex-col items-start gap-0.5 font-normal">
                      <span className="font-medium">{ETIQUETAS_METRICA[metrica] ?? metrica}</span>
                      <span className="text-xs text-texto-suave">{DESCRIPCIONES_METRICA[metrica] ?? ''}</span>
                    </Label>
                    <Switch
                      id={id(`metrica-${metrica}`)}
                      checked={activa}
                      disabled={siempre}
                      onCheckedChange={(v) => alternarMetrica(metrica, v)}
                      aria-label={`Métrica ${ETIQUETAS_METRICA[metrica] ?? metrica}`}
                    />
                  </li>
                )
              })}
            </ul>
          </fieldset>

          <Button type="submit" className="w-full" disabled={enviando || (tocado && hayErrores)}>
            {enviando ? <LoaderCircle className="animate-spin" aria-hidden /> : <Search aria-hidden />}
            {enviando ? 'Consultando…' : 'Consultar'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
