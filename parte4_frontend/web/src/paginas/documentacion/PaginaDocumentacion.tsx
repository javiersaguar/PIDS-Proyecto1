/**
 * Documentación (§6): qué es la plataforma y el escenario E3, el diagrama de arquitectura, cómo se protege cada
 * respuesta del asistente, la tabla de servicios con enlaces (de `GET /api/panel` o los valores por defecto del §3)
 * y el equipo. Página estática salvo los enlaces.
 */
import { BookOpen, ExternalLink, Filter, Lock, ShieldCheck, Sigma, Users } from 'lucide-react'
import type { ReactNode } from 'react'

import { useEnlaces } from '@/api/operaciones'
import type { Panel } from '@/api/tipos'
import { EncabezadoPagina } from '@/componentes/shell'
import { Badge } from '@/componentes/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/componentes/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/componentes/ui/table'

import { Diagrama } from './Diagrama'

const COMPONENTES = [
  { componente: 'Almacenamiento de objetos', tecnologia: 'SeaweedFS (S3)', funcion: 'Zona restringida crudo (viajes individuales) y referencia (zonas)', datos: 'Individuales' },
  { componente: 'Cola de eventos', tecnologia: 'Redpanda (API Kafka)', funcion: 'viajes-crudos (retención 24 h) y gestos (1 h)', datos: 'Individuales' },
  { componente: 'Procesado', tecnologia: 'Spark 4 (Scala), modo cluster', funcion: 'Validación, archivo y agregación protegida; lotes y streaming', datos: 'Individuales' },
  { componente: 'Base de datos', tecnologia: 'MongoDB', funcion: 'publico (solo agregados) y auditoria (solo inserción)', datos: 'Agregados' },
  { componente: 'Captura', tecnologia: 'FastAPI', funcion: 'Entrada HTTP de viajes y gestos', datos: 'Individuales (de paso)' },
  { componente: 'Acceso', tecnologia: 'FastAPI', funcion: 'Única puerta a los datos: filtro de privacidad y auditoría', datos: 'Agregados' },
  { componente: 'Orquestación', tecnologia: 'Airflow 3', funcion: 'Carga histórica: descarga → S3 → Spark → comprobación', datos: 'Individuales (solo ficheros)' },
  { componente: 'Monitorización', tecnologia: 'Prometheus + Grafana', funcion: 'Métricas técnicas y agregados protegidos', datos: 'Métricas' },
  { componente: 'Chatbots', tecnologia: 'Chainlit + Ollama (llama3.1:8b) · RAG', funcion: 'Conversación; solo usan la API de acceso', datos: 'Agregados' },
  { componente: 'Portal web', tecnologia: 'FastAPI (BFF) + React', funcion: 'Esta aplicación: sesión, proxy a la API de acceso y agente del chat', datos: 'Agregados' },
]

const PASOS_PROTECCION = [
  {
    icono: Filter,
    titulo: '1 · Filtro previo del asistente',
    texto:
      'Antes de llamar al modelo, el agente reconoce las peticiones de datos individuales (un viaje concreto, una hora con minutos, una matrícula, un destino por zona, paráfrasis e inyecciones) y las rechaza sin que el LLM llegue a verlas. Cuando hay un día, propone la consulta agregada más cercana con el botón «Consultar la alternativa». La decisión también se registra en la API.',
  },
  {
    icono: ShieldCheck,
    titulo: '2 · La API de acceso',
    texto:
      'Toda consulta (del asistente, del explorador o de cualquier cliente) pasa por POST /consultas: valida el nivel, la granularidad mínima (hora o día completos), el rango máximo de 31 días y los campos prohibidos; devuelve los grupos con menos de 10 viajes como «<10» sin cifras y nunca los suma. Cada decisión queda en auditoria.decisiones con su alternativa.',
  },
  {
    icono: Sigma,
    titulo: '3 · Barreras sobre las cifras',
    texto:
      'La respuesta del modelo se comprueba número a número contra los datos del propio turno: si contiene una cifra que no sale de ellos (inventada o deducida restando), se sustituye por la tabla de datos. Si todo está enmascarado, se responde sin el modelo. Al pie de cada respuesta va la fuente: histórico o tiempo real, solo agregados.',
  },
]

const SERVICIOS: { clave: keyof Panel['enlaces']; nombre: string; para: string }[] = [
  { clave: 'grafana', nombre: 'Grafana', para: 'Paneles de métricas técnicas y alertas (consultas rechazadas, frescura, servicios caídos)' },
  { clave: 'airflow', nombre: 'Airflow', para: 'DAG pids_carga_historica: descarga del mes, S3, Spark y comprobación' },
  { clave: 'spark', nombre: 'Spark (máster)', para: 'Estado del clúster y de los trabajos TiempoReal y CargaHistorica' },
  { clave: 'api_acceso', nombre: 'API de acceso · /docs', para: 'OpenAPI de la única puerta a los datos (POST /consultas, GET /catalogo, GET /zonas)' },
  { clave: 'api_captura', nombre: 'API de captura · /docs', para: 'OpenAPI de la entrada de viajes y gestos (POST /viajes, POST /gestos)' },
  { clave: 'chatbot', nombre: 'Chatbot Chainlit (Ollama)', para: 'La interfaz original del asistente de la parte 3, en el puerto 8010' },
  { clave: 'chatbot_rag', nombre: 'Chatbot Chainlit (RAG)', para: 'La variante con recuperación de documentación, en el puerto 8011' },
]

const EQUIPO = [
  { nombre: 'Javier Saguar', responsabilidad: 'Spark (Scala): histórico y tiempo real; parte 1 (gestos)' },
  { nombre: 'Alejandro Cuevas', responsabilidad: 'Almacenamiento, cola y despliegue (Compose, S3, MongoDB, Redpanda)' },
  { nombre: 'Mónica Fernández', responsabilidad: 'APIs y reglas de privacidad' },
  { nombre: 'Pedro José Orrego', responsabilidad: 'Airflow, Prometheus, Grafana y métricas de calidad' },
  { nombre: 'Daniel Naval', responsabilidad: 'Chatbot, casos de uso e integración con los gestos' },
]

function Seccion({ id, icono, titulo, descripcion, children }: { id: string; icono: ReactNode; titulo: string; descripcion?: string; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="space-y-3">
      <div className="flex items-start gap-2">
        <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md bg-acento-suave text-primario" aria-hidden>
          {icono}
        </span>
        <div>
          <h2 id={id} className="text-xl">
            {titulo}
          </h2>
          {descripcion && <p className="text-texto-suave">{descripcion}</p>}
        </div>
      </div>
      {children}
    </section>
  )
}

function ChipDatos({ datos }: { datos: string }) {
  const individual = datos.startsWith('Individuales')
  const agregado = datos === 'Agregados'
  return (
    <Badge
      variant="outline"
      className={
        individual ? 'h-5 border-peligro/30 bg-peligro/10 font-medium text-peligro' : agregado ? 'h-5 border-ok/30 bg-ok/10 font-medium text-ok' : 'h-5 font-medium text-texto-suave'
      }
    >
      {datos}
    </Badge>
  )
}

export default function PaginaDocumentacion() {
  const { enlaces, delPanel } = useEnlaces()

  return (
    <>
      <EncabezadoPagina
        titulo="Documentación"
        descripcion="Qué es la plataforma, cómo está montada, cómo se protege cada respuesta y dónde están las demás herramientas."
      />
      <div className="space-y-8">
        <Seccion id="doc-plataforma" icono={<BookOpen className="size-4" />} titulo="La plataforma y el escenario E3">
          <div className="grid gap-3 lg:grid-cols-2">
            <Card className="sombra-tarjeta">
              <CardContent className="space-y-2 leading-relaxed">
                <p>
                  Plataforma de datos de una empresa de taxis construida sobre los viajes de taxi amarillo de Nueva York de 2020 (23,7
                  millones de viajes). Los datos entran por dos caminos: la <strong>carga histórica</strong>, que Airflow descarga de la
                  TLC y Spark procesa por lotes, y el <strong>tiempo real</strong>, que llega a la API de captura, pasa por Redpanda y Spark
                  agrega en streaming cada 30 segundos. Lo que resulta se publica en MongoDB en tres niveles (por hora y zona, por día y
                  barrio, y flujos entre barrios) y se consulta desde este portal, el explorador, el asistente conversacional y Grafana.
                </p>
              </CardContent>
            </Card>
            <Card className="sombra-tarjeta border-l-4 border-l-enmascarado">
              <CardContent className="space-y-2 leading-relaxed">
                <p>
                  <strong>E3, privacidad total:</strong> el dataset podría identificar movimientos de personas concretas, así que ningún
                  dato individual puede exponerse. Los viajes individuales solo existen en una zona restringida (S3 y la cola de eventos)
                  a la que solo acceden la ingesta y Spark. Lo consultable son <strong>agregados</strong> con los grupos de menos de 10
                  viajes ocultos, y la única puerta es una API que rechaza cualquier consulta individual, propone una alternativa y lo
                  registra todo. El portal solo enseña lo que esa API devuelve y las decisiones de la auditoría, que no contienen viajes.
                </p>
              </CardContent>
            </Card>
          </div>
        </Seccion>

        <Seccion
          id="doc-arquitectura"
          icono={<Sigma className="size-4" />}
          titulo="Arquitectura"
          descripcion="Dos redes Docker: «datos» (S3, Redpanda, MongoDB y quien los usa) y «servicios» (APIs, chatbots, Grafana). Los chatbots y Grafana no están en la red de datos."
        >
          <Card className="sombra-tarjeta">
            <CardContent>
              <Diagrama />
            </CardContent>
          </Card>
          <Card className="sombra-tarjeta">
            <CardHeader>
              <CardTitle>Componentes</CardTitle>
              <CardDescription>Qué hace cada pieza y qué datos llega a ver.</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow className="bg-superficie-alterna/60 hover:bg-superficie-alterna/60">
                    <TableHead scope="col">Componente</TableHead>
                    <TableHead scope="col">Tecnología</TableHead>
                    <TableHead scope="col">Función</TableHead>
                    <TableHead scope="col">Qué datos ve</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {COMPONENTES.map((fila) => (
                    <TableRow key={fila.componente}>
                      <TableCell className="font-medium">{fila.componente}</TableCell>
                      <TableCell className="text-texto-suave">{fila.tecnologia}</TableCell>
                      <TableCell className="whitespace-normal">{fila.funcion}</TableCell>
                      <TableCell>
                        <ChipDatos datos={fila.datos} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </Seccion>

        <Seccion
          id="doc-proteccion"
          icono={<Lock className="size-4" />}
          titulo="Cómo se protege cada respuesta"
          descripcion="Tres barreras independientes; las dos últimas no dependen de cómo esté escrita la pregunta."
        >
          <ol className="grid gap-3 lg:grid-cols-3">
            {PASOS_PROTECCION.map(({ icono: Icono, titulo, texto }) => (
              <li key={titulo}>
                <Card size="sm" className="h-full sombra-tarjeta">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Icono className="size-4 text-acento" aria-hidden />
                      {titulo}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="leading-relaxed text-texto-suave">{texto}</CardContent>
                </Card>
              </li>
            ))}
          </ol>
        </Seccion>

        <Seccion
          id="doc-servicios"
          icono={<ExternalLink className="size-4" />}
          titulo="Servicios y herramientas"
          descripcion={
            delPanel
              ? 'Enlaces configurados en el BFF (ENLACES_*). Se abren en una pestaña nueva; cada uno pide sus propias credenciales.'
              : 'El BFF no ha devuelto la configuración de enlaces: se muestran los puertos publicados por defecto en este equipo.'
          }
        >
          <Card className="sombra-tarjeta">
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow className="bg-superficie-alterna/60 hover:bg-superficie-alterna/60">
                    <TableHead scope="col">Servicio</TableHead>
                    <TableHead scope="col">Para qué</TableHead>
                    <TableHead scope="col">Dirección</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {SERVICIOS.map((servicio) => (
                    <TableRow key={servicio.clave}>
                      <TableCell className="font-medium">
                        <a
                          href={enlaces[servicio.clave]}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1.5 text-primario underline-offset-2 hover:underline"
                        >
                          {servicio.nombre}
                          <ExternalLink className="size-3.5 text-texto-suave" aria-hidden />
                        </a>
                      </TableCell>
                      <TableCell className="whitespace-normal text-texto-suave">{servicio.para}</TableCell>
                      <TableCell className="font-mono text-xs text-texto-suave">{enlaces[servicio.clave]}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </Seccion>

        <Seccion
          id="doc-equipo"
          icono={<Users className="size-4" />}
          titulo="Equipo"
          descripcion="PIDS 26/27 · Proyecto 1. Cada persona trabaja en su rama y lleva los cambios a main con un pull request."
        >
          <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5" aria-label="Equipo">
            {EQUIPO.map((persona) => (
              <li key={persona.nombre}>
                <Card size="sm" className="h-full sombra-tarjeta">
                  <CardContent className="space-y-1">
                    <p className="font-semibold text-primario">{persona.nombre}</p>
                    <p className="text-xs leading-relaxed text-texto-suave">{persona.responsabilidad}</p>
                  </CardContent>
                </Card>
              </li>
            ))}
          </ul>
        </Seccion>
      </div>
    </>
  )
}
