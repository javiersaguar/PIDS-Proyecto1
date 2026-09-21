/**
 * Operaciones: dos acciones, cada una con su título y su explicación.
 * Cargar los viajes de un mes de 2020, o simular que los taxis circulan ahora.
 * Sin cabecera de página: el nombre de la sección ya está en la barra lateral.
 */
import { CargaHistorica } from './CargaHistorica'
import { Simulador } from './Simulador'

export default function PaginaOperaciones() {
  return (
    <>
      <h1 className="sr-only">Operaciones</h1>
      <div className="flex flex-col gap-5">
        <CargaHistorica />
        <Simulador />
      </div>
    </>
  )
}
