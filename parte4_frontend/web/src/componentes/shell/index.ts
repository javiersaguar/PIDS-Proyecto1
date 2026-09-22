/**
 * Punto de entrada del shell. Las páginas (F3, F4) importan de aquí:
 *
 *   import { EncabezadoPagina, EstadoCargando, EstadoError, EstadoVacio, EstadoNoDisponible } from '@/componentes/shell'
 */
export { AppShell } from './AppShell'
export { BarraLateral } from './BarraLateral'
export { Cabecera } from './Cabecera'
export { LogoTaxi, TaxiNuevaYork } from './LogoTaxi'
export { BotonTaxiAI } from './BotonTaxiAI'
export { PanelAsistente, ID_PANEL_ASISTENTE } from './PanelAsistente'
export { Pie, AVISO_E3 } from './Pie'
export { GuardiaSesion } from './GuardiaSesion'
export { EncabezadoPagina } from './EncabezadoPagina'
export { EstadoCargando, EstadoError, EstadoVacio, EstadoNoDisponible } from './Estados'
export { SECCIONES, seccionDe, type Seccion } from './navegacion'
export { CLAVE_PANEL, useEstadoServicios } from './servicios'
