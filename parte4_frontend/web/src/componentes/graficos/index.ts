/**
 * Gráficos del portal (F3). Las páginas importan de aquí:
 *
 *   import { GraficoBarras, GraficoLineas, MatrizFlujos, Semaforo, nivelFrescura } from '@/componentes/graficos'
 */
export { GraficoBarras, type Barra } from './GraficoBarras'
export { GraficoLineas, type PuntoLinea, type Serie } from './GraficoLineas'
export { MatrizFlujos, type CeldaFlujo } from './MatrizFlujos'
export { Semaforo } from './Semaforo'
export { TooltipGrafico } from './TooltipGrafico'
export { nivelFrescura, TEXTO_FRESCURA, UMBRALES_FRESCURA, type NivelFrescura } from './frescura'
export { COLOR_ENMASCARADO, COLOR_PRINCIPAL, COLORES_SERIES, colorSerie } from './comun'
