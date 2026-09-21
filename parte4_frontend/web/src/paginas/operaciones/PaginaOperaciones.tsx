/**
 * Operaciones (§6): lanzar una carga histórica (mes o muestra) y ver las ejecuciones de Airflow; iniciar o parar el
 * simulador de tiempo real con su barra de progreso. Ninguna de las dos tarjetas toca datos individuales: la carga
 * la hace Spark dentro de la red de datos y el simulador solo reenvía el CSV de muestra a la API de captura.
 */
import { EncabezadoPagina } from '@/componentes/shell'

import { CargaHistorica } from './CargaHistorica'
import { Simulador } from './Simulador'

export default function PaginaOperaciones() {
  return (
    <>
      <EncabezadoPagina
        titulo="Operaciones"
        descripcion="Cargas históricas en Airflow y simulador de viajes en tiempo real. Las acciones las ejecuta el BFF con las credenciales del servidor; el navegador no ve ninguna clave."
      />
      <div className="grid gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <CargaHistorica />
        <Simulador />
      </div>
    </>
  )
}
