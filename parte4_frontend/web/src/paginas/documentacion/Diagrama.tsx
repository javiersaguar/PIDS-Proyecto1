/**
 * Diagrama estático de la arquitectura (SVG propio, sin dependencias): captura → Redpanda → Spark → MongoDB →
 * API de acceso → portal y chatbots; Airflow → S3 → Spark; Prometheus → Grafana. Distingue la zona restringida
 * (viajes individuales) de la zona de agregados, que es lo único consultable.
 */
const ANCHO = 170
const ALTO = 56
/** Columnas (x de cada nodo); el hueco entre la 3 y la 4 es mayor para las etiquetas de las flechas. */
const COL = [20, 240, 460, 680, 940, 1160]
const FILA = { alta: 40, media: 95, baja: 150, abajo: 300 }
const centroY = (y: number) => y + ALTO / 2

type Clase = 'individual' | 'agregado' | 'neutro'

interface Nodo {
  id: string
  x: number
  y: number
  titulo: string
  sub: string
  clase: Clase
}

const NODOS: Nodo[] = [
  { id: 'simulador', x: COL[0], y: FILA.alta, titulo: 'Simulador / proveedor', sub: 'viajes en tiempo real', clase: 'neutro' },
  { id: 'captura', x: COL[1], y: FILA.alta, titulo: 'API de captura', sub: 'FastAPI · POST /viajes', clase: 'individual' },
  { id: 'redpanda', x: COL[2], y: FILA.alta, titulo: 'Redpanda', sub: 'viajes-crudos · retención 24 h', clase: 'individual' },
  { id: 'airflow', x: COL[0], y: FILA.baja, titulo: 'Airflow', sub: 'descarga el mes de la TLC', clase: 'neutro' },
  { id: 's3', x: COL[1], y: FILA.baja, titulo: 'S3 «crudo»', sub: 'SeaweedFS · Parquet mensual', clase: 'individual' },
  { id: 'spark', x: COL[2], y: FILA.baja, titulo: 'Spark', sub: 'TiempoReal · CargaHistorica', clase: 'individual' },
  { id: 'mongo', x: COL[3], y: FILA.media, titulo: 'MongoDB', sub: 'publico · auditoria', clase: 'agregado' },
  { id: 'acceso', x: COL[4], y: FILA.media, titulo: 'API de acceso', sub: 'filtro de privacidad · k = 10', clase: 'agregado' },
  { id: 'portal', x: COL[5], y: FILA.alta, titulo: 'Portal web (BFF)', sub: 'este sitio · puerto 8020', clase: 'agregado' },
  { id: 'chatbots', x: COL[5], y: FILA.baja, titulo: 'Chatbots Chainlit', sub: 'Ollama :8010 · RAG :8011', clase: 'agregado' },
  { id: 'ollama', x: COL[5], y: FILA.abajo, titulo: 'Ollama', sub: 'LLM local en GPU', clase: 'neutro' },
  { id: 'prometheus', x: COL[1], y: FILA.abajo, titulo: 'Prometheus', sub: 'sondea cada 15 s', clase: 'neutro' },
  { id: 'grafana', x: COL[2], y: FILA.abajo, titulo: 'Grafana', sub: 'paneles y alertas', clase: 'neutro' },
]

interface Flecha {
  d: string
  etiqueta?: string
  x?: number
  y?: number
  anclaje?: 'middle' | 'start'
  discontinua?: boolean
}

const yAlta = centroY(FILA.alta)
const yMedia = centroY(FILA.media)
const yBaja = centroY(FILA.baja)
const yAbajo = centroY(FILA.abajo)
const derecha = (col: number) => COL[col] + ANCHO
const centroX = (col: number) => COL[col] + ANCHO / 2

const FLECHAS: Flecha[] = [
  { d: `M${derecha(0)},${yAlta} L${COL[1] - 2},${yAlta}` },
  { d: `M${derecha(1)},${yAlta} L${COL[2] - 2},${yAlta}` },
  { d: `M${centroX(2)},${FILA.alta + ALTO} L${centroX(2)},${FILA.baja - 2}`, etiqueta: 'Structured Streaming', x: centroX(2) + 8, y: 126, anclaje: 'start' },
  { d: `M${derecha(0)},${yBaja} L${COL[1] - 2},${yBaja}` },
  { d: `M${derecha(1)},${yBaja} L${COL[2] - 2},${yBaja}` },
  { d: `M${derecha(2)},${yBaja} L${derecha(2) + 25},${yBaja} L${derecha(2) + 25},${yMedia} L${COL[3] - 2},${yMedia}`, etiqueta: 'agregados protegidos', x: derecha(2) + 25, y: 226 },
  { d: `M${COL[2] + 40},${FILA.baja + ALTO} L${COL[2] + 40},234 L${derecha(1) - 20},234 L${derecha(1) - 20},${FILA.baja + ALTO + 2}`, etiqueta: 'válidos y rechazos', x: (COL[2] + 40 + derecha(1) - 20) / 2, y: 248, discontinua: true },
  { d: `M${derecha(3)},${yMedia - 10} L${COL[4] - 2},${yMedia - 10}`, etiqueta: 'POST /consultas', x: (derecha(3) + COL[4]) / 2, y: yMedia - 18 },
  { d: `M${COL[4]},${yMedia + 15} L${derecha(3) + 2},${yMedia + 15}`, etiqueta: 'auditoría', x: (derecha(3) + COL[4]) / 2, y: yMedia + 29, discontinua: true },
  { d: `M${derecha(4)},${yMedia - 13} L${derecha(4) + 25},${yMedia - 13} L${derecha(4) + 25},${yAlta} L${COL[5] - 2},${yAlta}` },
  { d: `M${derecha(4)},${yMedia + 13} L${derecha(4) + 25},${yMedia + 13} L${derecha(4) + 25},${yBaja} L${COL[5] - 2},${yBaja}` },
  { d: `M${centroX(5)},${FILA.baja + ALTO} L${centroX(5)},${FILA.abajo - 2}` },
  { d: `M${derecha(1)},${yAbajo} L${COL[2] - 2},${yAbajo}` },
  { d: `M${centroX(1)},${FILA.abajo} L${centroX(1)},262`, etiqueta: 'métricas de APIs, Redpanda, S3 y Spark', x: centroX(1) + 8, y: 282, anclaje: 'start', discontinua: true },
]

const CLASE_RECT: Record<Clase, string> = {
  individual: 'fill-superficie stroke-peligro/50',
  agregado: 'fill-superficie stroke-ok/60',
  neutro: 'fill-superficie stroke-borde',
}

export function Diagrama() {
  const zonaRestringida = { x: COL[1] - 15, ancho: derecha(2) - COL[1] + 30 }
  const zonaAgregados = { x: COL[3] - 15, ancho: derecha(5) - COL[3] + 30 }
  return (
    <figure className="overflow-x-auto">
      <svg
        viewBox={`0 0 ${derecha(5) + 20} 380`}
        role="img"
        aria-labelledby="diagrama-titulo diagrama-descripcion"
        className="h-auto w-full min-w-[900px]"
      >
        <title id="diagrama-titulo">Arquitectura de la plataforma</title>
        <desc id="diagrama-descripcion">
          Los viajes individuales entran por la API de captura o por Airflow, pasan por Redpanda o S3 y Spark los agrega. MongoDB solo
          recibe agregados, que la API de acceso sirve con el filtro de privacidad al portal y a los chatbots. Prometheus y Grafana
          observan el conjunto.
        </desc>
        <defs>
          <marker id="punta" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" className="fill-texto-suave" />
          </marker>
        </defs>

        {/* Zonas */}
        <rect x={zonaRestringida.x} y={18} width={zonaRestringida.ancho} height={240} rx={12} className="fill-peligro/5 stroke-peligro/30" strokeDasharray="6 4" />
        <text x={zonaRestringida.x + 10} y={32} className="fill-peligro font-semibold" style={{ fontSize: 11 }}>
          ZONA RESTRINGIDA · viajes individuales (red «datos»)
        </text>
        <rect x={zonaAgregados.x} y={18} width={zonaAgregados.ancho} height={240} rx={12} className="fill-ok/5 stroke-ok/30" strokeDasharray="6 4" />
        <text x={zonaAgregados.x + 10} y={32} className="fill-ok font-semibold" style={{ fontSize: 11 }}>
          SOLO AGREGADOS · k = 10, grupos pequeños enmascarados
        </text>
        <text x={COL[0]} y={yAbajo + 4} className="fill-texto-suave font-semibold" style={{ fontSize: 11 }}>
          OBSERVABILIDAD
        </text>

        {/* Flechas */}
        {FLECHAS.map((flecha) => (
          <g key={flecha.d}>
            <path
              d={flecha.d}
              fill="none"
              className="stroke-texto-suave"
              strokeWidth={1.5}
              strokeDasharray={flecha.discontinua ? '4 3' : undefined}
              markerEnd="url(#punta)"
            />
            {flecha.etiqueta && (
              <text x={flecha.x} y={flecha.y} className="fill-texto-suave" style={{ fontSize: 10 }} textAnchor={flecha.anclaje ?? 'middle'}>
                {flecha.etiqueta}
              </text>
            )}
          </g>
        ))}

        {/* Nodos */}
        {NODOS.map((nodo) => (
          <g key={nodo.id}>
            <rect x={nodo.x} y={nodo.y} width={ANCHO} height={ALTO} rx={8} className={CLASE_RECT[nodo.clase]} strokeWidth={1.5} />
            {nodo.clase !== 'neutro' && (
              <rect x={nodo.x} y={nodo.y} width={4} height={ALTO} rx={2} className={nodo.clase === 'individual' ? 'fill-peligro' : 'fill-ok'} />
            )}
            <text x={nodo.x + 14} y={nodo.y + 24} className="fill-primario font-semibold" style={{ fontSize: 13 }}>
              {nodo.titulo}
            </text>
            <text x={nodo.x + 14} y={nodo.y + 42} className="fill-texto-suave" style={{ fontSize: 10.5 }}>
              {nodo.sub}
            </text>
          </g>
        ))}
      </svg>
      <figcaption className="mt-2 text-xs text-texto-suave">
        Además de lo que muestra el diagrama, el BFF del portal consulta Prometheus (estado y frescura), Airflow (cargas históricas), lee{' '}
        <code className="font-mono">auditoria</code> en MongoDB con el usuario <code className="font-mono">pids_auditor</code> (que no puede leer
        nada más) y ejecuta el agente del asistente con Ollama. El navegador solo llega al puerto 8020.
      </figcaption>
    </figure>
  )
}
