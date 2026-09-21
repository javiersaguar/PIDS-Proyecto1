/**
 * Componentes y ayudas de datos (F3). Las páginas (y F4) importan de aquí:
 *
 *   import { TablaAgregados, TarjetaKpi, ChipResultado, ChipEnmascarado, Frescura } from '@/componentes/datos'
 *   import { formatearEntero, formatearImporte, formatearFecha } from '@/componentes/datos/formato'
 */
export { Antiguedad } from './Antiguedad'
export { ChipEnmascarado, ChipResultado } from './ChipResultado'
export { Frescura } from './Frescura'
export { TablaAgregados, type Orden } from './TablaAgregados'
export { TarjetaKpi, type EstadoKpi } from './TarjetaKpi'
export { useAhora, useSegundosDesde } from './useAhora'
export * from './agregados'
export * from './formato'
