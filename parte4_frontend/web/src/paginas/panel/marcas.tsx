/**
 * Marcas de la tabla: los mismos iconos y colores que el lienzo de documentación, en PNG.
 */
import { cn } from '@/lib/utils'

interface Marca {
  archivo: string
}

const REGLAS: { prueba: RegExp; marca: Marca }[] = [
  { prueba: /grafana/i, marca: { archivo: 'grafana.png' } },
  { prueba: /spark/i, marca: { archivo: 'spark.png' } },
  { prueba: /airflow/i, marca: { archivo: 'airflow.png' } },
  { prueba: /prometheus/i, marca: { archivo: 'prometheus.png' } },
  { prueba: /captura/i, marca: { archivo: 'captura.png' } },
  { prueba: /rag/i, marca: { archivo: 'rag.png' } },
  { prueba: /chat|bot|ollama/i, marca: { archivo: 'chatbot.png' } },
  { prueba: /acceso/i, marca: { archivo: 'acceso.png' } },
  { prueba: /mongo/i, marca: { archivo: 'mongo.png' } },
  { prueba: /panda|kafka/i, marca: { archivo: 'redpanda.png' } },
  { prueba: /s3|seaweed|almacen/i, marca: { archivo: 's3.png' } },
]

const POR_DEFECTO: Marca = { archivo: 'defecto.png' }

function marcaDe(textos: readonly (string | undefined)[]): Marca {
  const texto = textos.filter(Boolean).join(' ')
  return REGLAS.find((regla) => regla.prueba.test(texto))?.marca ?? POR_DEFECTO
}

function rutaMarca(archivo: string): string {
  const base = import.meta.env.BASE_URL || '/'
  return `${base.endsWith('/') ? base : `${base}/`}panel/marcas/${archivo}`
}

export function MarcaServicio({ textos, className }: { textos: readonly (string | undefined)[]; className?: string }) {
  const { archivo } = marcaDe(textos)
  return <img src={rutaMarca(archivo)} alt="" width={32} height={32} className={cn('size-8 shrink-0 rounded-lg', className)} />
}
