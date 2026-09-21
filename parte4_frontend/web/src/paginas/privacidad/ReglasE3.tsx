/**
 * Pestaña «Reglas E3»: las reglas de `GET /api/catalogo` en cuatro tarjetas
 * (qué se publica, cuándo se oculta una cifra, por qué no basta y qué se rechaza).
 * El texto va en lenguaje llano, con un ejemplo corto, y en dos columnas para no dejar hueco a la derecha.
 */
import { Ban, EyeOff, Layers, type LucideIcon, Scale } from 'lucide-react'
import type { ReactNode } from 'react'

import { useCatalogo } from '@/api/auditoria'
import type { Catalogo, Fuente, Metrica, Nivel } from '@/api/tipos'
import { formatearNumero } from '@/componentes/chat/formato'
import { EstadoCargando, EstadoError } from '@/componentes/shell'
import { cn } from '@/lib/utils'

import { NOMBRE_METRICA, NOMBRE_NIVEL } from './etiquetas'

function unir(partes: string[]): string {
  if (partes.length <= 1) return partes[0] ?? ''
  return `${partes.slice(0, -1).join(', ')} y ${partes[partes.length - 1]}`
}

const FRASE_NIVEL: Record<Nivel, string> = {
  hora_zona: 'por hora y zona de origen (los taxis que salieron de un mismo sitio durante esa hora)',
  dia_barrio: 'por día y barrio de origen (los de un barrio durante un día entero)',
  od_dia_barrio: 'por flujos entre barrios en un mismo día (cuántos fueron de un barrio a otro)',
}

const FRASE_METRICA: Record<Metrica, string> = {
  n_viajes: 'cuántos viajes hubo',
  distancia_media: 'la distancia media',
  importe_medio: 'el importe medio',
  propina_media: 'la propina media',
  pct_pago_tarjeta: 'el porcentaje de pago con tarjeta',
}

const FRASE_FUENTE: Record<Fuente, string> = {
  historico: 'el histórico',
  tiempo_real: 'el tiempo real',
}

function fraseNiveles(catalogo: Catalogo | null): string {
  const claves = catalogo ? (Object.keys(catalogo.niveles) as Nivel[]) : (Object.keys(FRASE_NIVEL) as Nivel[])
  const frases = claves.map((nivel) => FRASE_NIVEL[nivel] ?? (NOMBRE_NIVEL[nivel] ?? nivel).toLowerCase())
  return unir(frases)
}

function fraseMetricas(catalogo: Catalogo | null): string {
  const metricas = catalogo?.metricas ?? (Object.keys(FRASE_METRICA) as Metrica[])
  const frases = metricas.map((metrica) => FRASE_METRICA[metrica] ?? NOMBRE_METRICA[metrica] ?? metrica)
  if (!frases.length) return 'recuentos y medias, redondeadas'
  return unir(frases)
}

function fraseFuentes(catalogo: Catalogo | null): string {
  const fuentes = catalogo?.fuentes ?? (Object.keys(FRASE_FUENTE) as Fuente[])
  const frases = fuentes.map((fuente) => FRASE_FUENTE[fuente] ?? fuente)
  if (!frases.length) return 'el histórico y el tiempo real'
  return unir(frases)
}

function Tarjeta({
  titulo,
  icono: Icono,
  tono,
  children,
  ejemplo,
}: {
  titulo: string
  icono: LucideIcon
  tono: string
  children: ReactNode
  ejemplo: string
}) {
  return (
    <section className="flex h-full flex-col rounded-2xl border border-borde bg-white px-4 py-3 sombra-tarjeta">
      <div className="flex items-center gap-2">
        <span className={cn('flex size-7 shrink-0 items-center justify-center rounded-lg', tono)} aria-hidden>
          <Icono className="size-3.5" strokeWidth={2.25} />
        </span>
        <h2 className="text-sm leading-tight">{titulo}</h2>
      </div>
      <div className="mt-2 space-y-1.5 text-sm leading-snug text-slate-600">{children}</div>
      <p className="mt-auto pt-2 text-sm leading-snug text-slate-700">
        <span className="font-medium text-primario">Por ejemplo. </span>
        {ejemplo}
      </p>
    </section>
  )
}

function Texto({ catalogo }: { catalogo: Catalogo | null }) {
  const k = catalogo ? formatearNumero(catalogo.k_minimo) : '10'
  const dias = catalogo ? formatearNumero(catalogo.max_dias_por_consulta) : '31'
  return (
    <div className="grid items-stretch gap-3 lg:grid-cols-2">
      <Tarjeta titulo="Qué se publica" icono={Layers} tono="bg-acento-suave text-acento" ejemplo="«¿Cuántos taxis salieron de Manhattan ese día?» sí. «¿Quién cogió el de las 15:12?» no.">
        <p>No contamos un viaje suelto. Contamos el montón, como decir cuántos hay en la clase y no el nombre de cada niño.</p>
        <p>
          Los montones se hacen así: {fraseNiveles(catalogo)}. De cada montón se puede preguntar {fraseMetricas(catalogo)}. Las medias
          se redondean para que no quede un céntimo exacto. Pasa igual con {fraseFuentes(catalogo)}.
        </p>
      </Tarjeta>
      <Tarjeta
        titulo="Cuándo se oculta una cifra"
        icono={EyeOff}
        tono="bg-enmascarado-suave text-enmascarado"
        ejemplo={`Siete viajes a las 4 no se ven como 7: se ven como «<${k}», y esos siete no entran en ninguna suma.`}
      >
        <p>
          Si el montón es muy pequeño, tapamos el número. Con pocos viajes se podría adivinar quién iba, igual que en un grupo de tres
          se nota quién falta.
        </p>
        <p>
          Si un grupo tiene menos de {k} viajes, ponemos «&lt;{k}» y no lo sumamos a ningún total. El grupo se deja en la lista, vacío,
          para distinguir «no hubo viajes» de «hubo tan pocos que no se muestran».
        </p>
      </Tarjeta>
      <Tarjeta
        titulo="Por qué no basta con ocultarla"
        icono={Scale}
        tono="bg-aviso/10 text-aviso"
        ejemplo="Había 100. Se ven 40, 35 y 18. 100 − 93 = 7, así que también tapamos el 18."
      >
        <p>
          Tapar el pequeño no basta. Si sabes el total y ves el resto, la resta dice el que faltaba: como una hucha de la que ya
          conoces cuánto había.
        </p>
        <p>
          Los grupos de un día y un barrio suman el total de ese día y barrio, que también se publica. Por eso se tapa también el
          grupo visible más pequeño. Si no queda ninguno a la vista, se tapa el total. A ese tapar de más se le llama supresión
          complementaria, y hace que la resta ya no dé un número exacto.
        </p>
      </Tarjeta>
      <Tarjeta
        titulo="Qué se rechaza"
        icono={Ban}
        tono="bg-peligro/10 text-peligro"
        ejemplo="«A las 3:12» no se contesta. En su lugar proponemos «de las 3 a las 4»."
      >
        <p>Si preguntas por una sola persona, no contestamos. Te proponemos la pregunta de montón más parecida.</p>
        <p>
          Una matrícula, una tarifa suelta, una hora con minutos o el destino de una zona no se responden. Lo más fino que se puede
          pedir es una hora completa, o el día entero cuando el montón es por día. Cada consulta abarca como máximo {dias} días.
        </p>
      </Tarjeta>
    </div>
  )
}

export function ReglasE3() {
  const catalogo = useCatalogo()
  if (catalogo.isPending) {
    return <EstadoCargando variante="tarjeta" lineas={5} etiqueta="Cargando las reglas de la API de acceso…" />
  }
  return (
    <div className="space-y-4">
      {catalogo.isError && (
        <EstadoError
          titulo="No se ha podido leer el catálogo de la API de acceso"
          error={catalogo.error}
          alReintentar={() => void catalogo.refetch()}
          reintentando={catalogo.isFetching}
        />
      )}
      <Texto catalogo={catalogo.data ?? null} />
    </div>
  )
}
