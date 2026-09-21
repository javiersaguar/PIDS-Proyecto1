/**
 * Genera las marcas PNG de la tabla del panel: el mismo icono de trazo que la documentación,
 * sobre el mismo fondo de color, rasterizado para la tabla.
 */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const aqui = dirname(fileURLToPath(import.meta.url))
const iconos = join(aqui, '..', 'node_modules', 'lucide-react', 'dist', 'esm', 'icons')
const salida = join(aqui, '..', 'public', 'panel', 'marcas')

const MARCAS = [
  { archivo: 'acceso', icono: 'shield-check', fondo: '#eaf2ff', trazo: '#2f62c4' },
  { archivo: 'captura', icono: 'inbox', fondo: '#e8faf2', trazo: '#17875a' },
  { archivo: 'spark', icono: 'flame', fondo: '#f3eeff', trazo: '#6d4eae' },
  { archivo: 'airflow', icono: 'workflow', fondo: '#fff6e4', trazo: '#b7791f' },
  { archivo: 'grafana', icono: 'line-chart', fondo: '#eaf2ff', trazo: '#2f62c4' },
  { archivo: 'prometheus', icono: 'activity', fondo: '#e7f8f8', trazo: '#0e7c7c' },
  { archivo: 'chatbot', icono: 'bot', fondo: '#f3eeff', trazo: '#6d4eae' },
  { archivo: 'rag', icono: 'book-open', fondo: '#e8faf2', trazo: '#17875a' },
  { archivo: 'mongo', icono: 'database', fondo: '#eaf2ff', trazo: '#2f62c4' },
  { archivo: 'redpanda', icono: 'waypoints', fondo: '#e8faf2', trazo: '#17875a' },
  { archivo: 's3', icono: 'hard-drive', fondo: '#fff1ea', trazo: '#c45c32' },
  { archivo: 'defecto', icono: 'server', fondo: '#f1f5f9', trazo: '#475569' },
]

function atributos(props) {
  return Object.entries(props)
    .filter(([clave]) => clave !== 'key')
    .map(([clave, valor]) => `${clave}="${valor}"`)
    .join(' ')
}

async function figuras(nombre, vistos = new Set()) {
  if (vistos.has(nombre)) throw new Error(`ciclo en ${nombre}`)
  vistos.add(nombre)
  const texto = readFileSync(join(iconos, `${nombre}.mjs`), 'utf8')
  const reexporta = texto.match(/export \{ default \} from '\.\/([^']+)\.mjs'/)
  if (reexporta) return figuras(reexporta[1], vistos)
  const modulo = await import(pathToFileURL(join(iconos, `${nombre}.mjs`)).href)
  return modulo.__iconData.node.map(([etiqueta, props]) => `<${etiqueta} ${atributos(props)}/>`).join('')
}

async function svgDe(marca) {
  const interior = await figuras(marca.icono)
  return `<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <rect width="128" height="128" rx="28" fill="${marca.fondo}"/>
  <g transform="translate(32 32) scale(2.6667)" fill="none" stroke="${marca.trazo}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    ${interior}
  </g>
</svg>`
}

mkdirSync(salida, { recursive: true })
const celdas = (await Promise.all(MARCAS.map(async (marca) => `<div class="celda">${await svgDe(marca)}</div>`))).join('')
const html = `<!doctype html><html><head><style>
  html,body{margin:0;background:#fff}
  .fila{display:flex;width:${MARCAS.length * 128}px;height:128px}
  .celda{width:128px;height:128px}
</style></head><body><div class="fila">${celdas}</div></body></html>`
writeFileSync(join(salida, '_tira.html'), html)
writeFileSync(join(salida, '_orden.txt'), MARCAS.map((m) => m.archivo).join('\n'))
console.log(`tira ${MARCAS.length * 128}x128`)
