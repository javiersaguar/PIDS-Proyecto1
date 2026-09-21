/**
 * Buscador de zona de origen (solo en el nivel `hora_zona`): un cuadro de texto con sugerencias de
 * `GET /api/zonas?texto=` (por nombre). Al elegir una zona se guarda su id; si se borra o se edita el texto, se
 * quita el filtro. Con un id que llega de la URL, resuelve el nombre con la lista completa de zonas.
 */
import { LoaderCircle, MapPin, X } from 'lucide-react'
import { useId, useMemo, useState, type KeyboardEvent } from 'react'

import { useZonas } from '@/api/consultas'
import type { Zona } from '@/api/tipos'
import { useValorRetardado } from '@/componentes/datos/useValorRetardado'
import { Input } from '@/componentes/ui/input'
import { cn } from '@/lib/utils'

interface Props {
  id: string
  valor: number | null
  onCambiar: (zona: Zona | null) => void
  disabled?: boolean
  /** Sin la línea de barrio e id: cabe en la barra horizontal de filtros. */
  compacto?: boolean
}

const MAXIMO_SUGERENCIAS = 12

export function BuscadorZona({ id, valor, onCambiar, disabled, compacto }: Props) {
  const [texto, setTexto] = useState('')
  const [editando, setEditando] = useState(false)
  const [abierto, setAbierto] = useState(false)
  const [activa, setActiva] = useState(0)
  const idLista = useId()

  const textoRetardado = useValorRetardado(texto.trim(), 250)
  const sugerencias = useZonas(textoRetardado, { habilitado: editando && textoRetardado.length > 0 })
  const todas = useZonas('', { habilitado: valor !== null })

  const seleccionada = useMemo(() => (valor === null ? null : (todas.data ?? []).find((z) => z._id === valor) ?? null), [todas.data, valor])
  const opciones = useMemo(() => (sugerencias.data ?? []).slice(0, MAXIMO_SUGERENCIAS), [sugerencias.data])

  // Lo que se ve en el cuadro: el nombre de la zona elegida, o lo que el usuario está escribiendo.
  const mostrado = editando ? texto : seleccionada ? seleccionada.nombre : valor !== null ? `Zona ${valor}` : ''
  const listaVisible = abierto && editando && textoRetardado.length > 0

  const elegir = (zona: Zona) => {
    onCambiar(zona)
    setEditando(false)
    setTexto('')
    setAbierto(false)
  }

  const limpiar = () => {
    onCambiar(null)
    setEditando(false)
    setTexto('')
    setAbierto(false)
  }

  const alTeclear = (evento: KeyboardEvent<HTMLInputElement>) => {
    if (evento.key === 'ArrowDown') {
      evento.preventDefault()
      setAbierto(true)
      setActiva((a) => Math.min(a + 1, Math.max(opciones.length - 1, 0)))
    } else if (evento.key === 'ArrowUp') {
      evento.preventDefault()
      setActiva((a) => Math.max(a - 1, 0))
    } else if (evento.key === 'Enter' && listaVisible && opciones[activa]) {
      evento.preventDefault()
      elegir(opciones[activa])
    } else if (evento.key === 'Escape') {
      setAbierto(false)
    }
  }

  return (
    <div className="relative">
      <div className="relative">
        <MapPin className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-texto-suave" aria-hidden />
        <Input
          id={id}
          role="combobox"
          aria-expanded={listaVisible}
          aria-controls={idLista}
          aria-autocomplete="list"
          aria-activedescendant={listaVisible && opciones[activa] ? `${idLista}-${opciones[activa]._id}` : undefined}
          autoComplete="off"
          placeholder={compacto ? 'Buscar zona…' : 'Todas las zonas · escribe para buscar (JFK, Times Sq…)'}
          className="h-8 pr-8 pl-8"
          value={mostrado}
          disabled={disabled}
          onChange={(e) => {
            setTexto(e.target.value)
            setEditando(true)
            setAbierto(true)
            setActiva(0)
            if (valor !== null) onCambiar(null)
          }}
          onFocus={() => {
            if (editando && texto) setAbierto(true)
          }}
          onBlur={() => {
            // Se retrasa para que el clic en una opción llegue antes de cerrar la lista.
            setTimeout(() => setAbierto(false), 120)
          }}
          onKeyDown={alTeclear}
        />
        {(valor !== null || texto) && !disabled && (
          <button
            type="button"
            onClick={limpiar}
            className="absolute top-1/2 right-2 -translate-y-1/2 rounded-sm text-texto-suave hover:text-foreground"
            aria-label="Quitar la zona"
          >
            <X className="size-4" aria-hidden />
          </button>
        )}
      </div>
      {seleccionada && !editando && !compacto && (
        <p className="mt-1 text-xs text-texto-suave">
          {seleccionada.barrio} · zona #{seleccionada._id}
          {seleccionada.tipo_servicio ? ` · ${seleccionada.tipo_servicio}` : ''}
        </p>
      )}
      {listaVisible && (
        <ul
          id={idLista}
          role="listbox"
          aria-label="Zonas sugeridas"
          className="absolute z-30 mt-1 max-h-64 w-full overflow-auto rounded-lg border bg-popover p-1 text-sm shadow-md"
        >
          {sugerencias.isPending || sugerencias.isFetching ? (
            <li className="flex items-center gap-2 px-2 py-1.5 text-texto-suave" aria-live="polite">
              <LoaderCircle className="size-3.5 animate-spin" aria-hidden /> Buscando…
            </li>
          ) : sugerencias.isError ? (
            <li className="px-2 py-1.5 text-peligro">No se han podido cargar las zonas.</li>
          ) : opciones.length === 0 ? (
            <li className="px-2 py-1.5 text-texto-suave">Ninguna zona contiene «{textoRetardado}».</li>
          ) : (
            opciones.map((zona, indice) => (
              <li
                key={zona._id}
                id={`${idLista}-${zona._id}`}
                role="option"
                aria-selected={indice === activa}
                className={cn('flex cursor-pointer items-center justify-between gap-2 rounded-md px-2 py-1.5', indice === activa && 'bg-accent text-accent-foreground')}
                onMouseDown={(e) => e.preventDefault()}
                onMouseEnter={() => setActiva(indice)}
                onClick={() => elegir(zona)}
              >
                <span className="truncate">{zona.nombre}</span>
                <span className="shrink-0 text-xs text-texto-suave">
                  {zona.barrio} · #{zona._id}
                </span>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  )
}
