/**
 * Pestaña «Reglas E3»: las reglas de privacidad leídas del catálogo de la API de acceso (`GET /api/catalogo`)
 * en tarjetas, más una explicación en lenguaje claro de por qué se enmascara, qué es la supresión
 * complementaria y el ataque por diferencia (resumen de `docs/escenario_E3.md`).
 */
import { Ban, CalendarRange, Clock3, Layers3, Lock, ShieldCheck, Sigma } from 'lucide-react'
import type { ReactNode } from 'react'

import { useCatalogo } from '@/api/auditoria'
import type { Catalogo, Nivel } from '@/api/tipos'
import { formatearNumero } from '@/componentes/chat/formato'
import { EstadoCargando, EstadoError } from '@/componentes/shell'
import { Badge } from '@/componentes/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/componentes/ui/card'

import { CAMPOS_INDIVIDUALES, granularidadDe, NOMBRE_DIMENSION, NOMBRE_FUENTE, NOMBRE_METRICA, NOMBRE_NIVEL } from './etiquetas'

function Cifra({ icono, valor, etiqueta, detalle }: { icono: ReactNode; valor: ReactNode; etiqueta: string; detalle: string }) {
  return (
    <Card size="sm" className="sombra-tarjeta">
      <CardContent className="flex items-start gap-3">
        <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg bg-acento-suave text-primario" aria-hidden>
          {icono}
        </span>
        <div className="min-w-0">
          <p className="text-xs font-medium text-texto-suave uppercase">{etiqueta}</p>
          <p className="cifra text-2xl font-semibold text-primario">{valor}</p>
          <p className="text-xs text-texto-suave">{detalle}</p>
        </div>
      </CardContent>
    </Card>
  )
}

function Chips({ valores, className }: { valores: string[]; className?: string }) {
  return (
    <ul className={`flex flex-wrap gap-1.5 ${className ?? ''}`}>
      {valores.map((valor) => (
        <li key={valor}>
          <Badge variant="outline" className="h-6 bg-superficie px-2 font-normal">
            {valor}
          </Badge>
        </li>
      ))}
    </ul>
  )
}

function TarjetasDelCatalogo({ catalogo }: { catalogo: Catalogo }) {
  const niveles = Object.entries(catalogo.niveles) as [Nivel, Catalogo['niveles'][Nivel]][]
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Cifra
          icono={<Lock className="size-4" />}
          etiqueta="k mínimo"
          valor={`k = ${formatearNumero(catalogo.k_minimo)}`}
          detalle="Un grupo con menos viajes se publica sin cifras («<10») y nunca se suma a un total."
        />
        <Cifra
          icono={<CalendarRange className="size-4" />}
          etiqueta="Rango máximo"
          valor={`${formatearNumero(catalogo.max_dias_por_consulta)} días`}
          detalle="Por consulta: evita descargar en masa los agregados finos."
        />
        <Cifra
          icono={<Layers3 className="size-4" />}
          etiqueta="Niveles publicados"
          valor={niveles.length}
          detalle="Solo estas combinaciones de dimensiones existen en MongoDB."
        />
        <Cifra
          icono={<Sigma className="size-4" />}
          etiqueta="Métricas"
          valor={catalogo.metricas.length}
          detalle="Recuentos y medias redondeadas a dos decimales."
        />
      </div>

      <section aria-labelledby="niveles-titulo" className="space-y-3">
        <h3 id="niveles-titulo" className="text-base">
          Los tres niveles de agregación
        </h3>
        <div className="grid gap-3 lg:grid-cols-3">
          {niveles.map(([nivel, definicion]) => (
            <Card key={nivel} size="sm" className="sombra-tarjeta">
              <CardHeader>
                <CardTitle className="flex items-center justify-between gap-2">
                  <span>{NOMBRE_NIVEL[nivel] ?? nivel}</span>
                  <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] font-normal text-texto-suave">{nivel}</code>
                </CardTitle>
                <CardDescription>{definicion.descripcion}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2 text-xs">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-texto-suave">Dimensiones:</span>
                  {definicion.dimensiones.map((d) => (
                    <Badge key={d} variant="secondary" className="h-5 font-normal">
                      {NOMBRE_DIMENSION[d] ?? d}
                    </Badge>
                  ))}
                </div>
                <p className="flex items-center gap-1.5 text-texto-suave">
                  <Clock3 className="size-3.5" aria-hidden />
                  Granularidad mínima: <span className="font-medium text-foreground">{granularidadDe(definicion.dimensiones)}</span>
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <div className="grid gap-3 lg:grid-cols-2">
        <Card size="sm" className="sombra-tarjeta">
          <CardHeader>
            <CardTitle>Métricas publicadas</CardTitle>
            <CardDescription>Lo único que se puede pedir de cada grupo; las medias van redondeadas a 2 decimales.</CardDescription>
          </CardHeader>
          <CardContent>
            <Chips valores={catalogo.metricas.map((m) => `${NOMBRE_METRICA[m] ?? m} (${m})`)} />
          </CardContent>
        </Card>
        <Card size="sm" className="sombra-tarjeta">
          <CardHeader>
            <CardTitle>Fuentes</CardTitle>
            <CardDescription>Las mismas reglas para el histórico y para el tiempo real.</CardDescription>
          </CardHeader>
          <CardContent>
            <Chips valores={catalogo.fuentes.map((f) => NOMBRE_FUENTE[f] ?? f)} />
          </CardContent>
        </Card>
        <Card size="sm" className="sombra-tarjeta lg:col-span-2">
          <CardHeader>
            <CardTitle>Barrios ({catalogo.barrios.length})</CardTitle>
            <CardDescription>Los barrios (boroughs) por los que se puede filtrar el origen y, en los flujos, el destino.</CardDescription>
          </CardHeader>
          <CardContent>
            <Chips valores={catalogo.barrios} />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function Explicacion() {
  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <Card size="sm" className="sombra-tarjeta">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Ban className="size-4 text-peligro" aria-hidden />
            Campos individuales prohibidos
          </CardTitle>
          <CardDescription>
            De <code className="font-mono text-[11px]">config/privacidad.json</code>: pedir cualquiera de ellos rechaza la consulta y la
            API propone una alternativa agregada. También se rechazan los instantes con minutos (la granularidad mínima es la hora) y
            el destino por zona (solo existe por barrio y día).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Chips valores={CAMPOS_INDIVIDUALES} />
        </CardContent>
      </Card>

      <Card size="sm" className="sombra-tarjeta">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lock className="size-4 text-enmascarado" aria-hidden />
            Por qué se enmascara
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 leading-relaxed">
          <p>
            Un grupo con pocos viajes (una zona a una hora concreta con tres viajes, por ejemplo) es casi un viaje individual: quien sepa
            que alguien cogió un taxi allí a esa hora puede reconocerlo. Por eso los grupos con menos de <strong>k = 10</strong> viajes se
            publican con <code className="font-mono text-[11px]">suprimido: true</code> y <strong>sin cifras</strong>; la API los devuelve como{' '}
            <span className="font-medium text-enmascarado">«&lt;10»</span> y nunca los suma a ningún total.
          </p>
          <p className="text-texto-suave">
            Se publican vacíos, en vez de no publicarse, para poder distinguir «no hubo viajes» de «hubo muy pocos y no se muestran», que es
            lo que pide E3: informar de la decisión de privacidad.
          </p>
        </CardContent>
      </Card>

      <Card size="sm" className="sombra-tarjeta">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sigma className="size-4 text-primario" aria-hidden />
            El ataque por diferencia
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 leading-relaxed">
          <p>
            Ocultar la cifra de un grupo pequeño no basta si se puede <strong>deducir restando</strong>: los grupos de un día y barrio
            suman el total de ese día y barrio, que también se publica.
          </p>
          <pre className="cifra overflow-x-auto rounded-lg bg-muted px-3 py-2 text-xs">
            grupo oculto = total del día y barrio − suma de los grupos visibles
          </pre>
          <p className="text-texto-suave">
            Medido contra la plataforma real con 9 516 consultas permitidas sobre los 366 días de 2020: antes de mitigar, 431 grupos
            ocultos se despejaban con valor exacto (sobre todo días de Staten Island con todos los grupos suprimidos).
          </p>
        </CardContent>
      </Card>

      <Card size="sm" className="sombra-tarjeta">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="size-4 text-ok" aria-hidden />
            La mitigación: supresión complementaria
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 leading-relaxed">
          <ol className="list-decimal space-y-1 pl-5">
            <li>
              En cada partición (día, barrio) expuesta se suprime además el <strong>grupo visible más pequeño</strong>: como tiene 10 o
              más viajes, la suma oculta ya no se puede repartir.
            </li>
            <li>Si la partición no tiene ningún grupo visible, se oculta su total del día y barrio.</li>
            <li>La marca que distingue un suprimido complementario de uno pequeño no se publica.</li>
          </ol>
          <p className="text-texto-suave">
            Cuesta menos del 0,04 % de los viajes publicados y, repetido el ataque, ningún grupo se despeja. Se aplica en la carga
            histórica; el tiempo real sigue expuesto mientras dura el día (riesgo conocido, en la documentación).
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

export function ReglasE3() {
  const catalogo = useCatalogo()
  return (
    <div className="space-y-6">
      {catalogo.isPending ? (
        <EstadoCargando variante="tarjeta" lineas={5} etiqueta="Cargando el catálogo de la API de acceso…" />
      ) : catalogo.isError ? (
        <EstadoError
          titulo="No se ha podido leer el catálogo de la API de acceso"
          error={catalogo.error}
          alReintentar={() => void catalogo.refetch()}
          reintentando={catalogo.isFetching}
        />
      ) : (
        <TarjetasDelCatalogo catalogo={catalogo.data} />
      )}
      <section aria-labelledby="explicacion-titulo" className="space-y-3">
        <h3 id="explicacion-titulo" className="text-base">
          Cómo funciona la protección
        </h3>
        <Explicacion />
      </section>
    </div>
  )
}
