/**
 * Piezas del lienzo de arquitectura: dónde se sienta cada tarjeta, de qué color es su camino
 * y el texto de la ficha, escrito para leerlo en voz alta.
 */
import {
  Activity,
  Bot,
  Database,
  Flame,
  HardDrive,
  Inbox,
  LineChart,
  MessageSquareText,
  Radio,
  Server,
  ShieldCheck,
  Waypoints,
  Workflow,
  type LucideIcon,
} from 'lucide-react'

import type { Panel } from '@/api/tipos'

export const TARJETA = { ancho: 214, alto: 108 }
export const LIENZO = { ancho: 1280, alto: 780 }

export type Tono = 'coral' | 'verde' | 'violeta' | 'azul' | 'ambar' | 'cian'
export type Lado = 'arriba' | 'abajo' | 'izquierda' | 'derecha'

export interface Nodo {
  id: string
  x: number
  y: number
  titulo: string
  /** Nombre largo de la ficha, si la tarjeta usa uno más corto. */
  nombre?: string
  subtitulo: string
  tecnologia: string
  /** Pastilla corta de la tarjeta: qué tipo de dato toca. */
  datos: string
  tono: Tono
  icono: LucideIcon
  queEs: string[]
  queHace: string[]
  comoConecta: string[]
  /** Enlaces externos (claves de `GET /api/panel`). */
  enlaces?: { clave: keyof Panel['enlaces']; texto: string }[]
  /** Ruta interna del portal, si la pieza se maneja desde aquí. */
  ruta?: { to: string; texto: string }
}

export interface Arista {
  desde: string
  hasta: string
  etiqueta: string
  tono: Tono
  salida: Lado
  entrada: Lado
  desplazaSalida?: number
  desplazaEntrada?: number
  /** Punto de la curva (0–1) donde se sienta la etiqueta. */
  tEtiqueta?: number
}

export const NODOS: Nodo[] = [
  {
    id: 'airflow',
    x: 16,
    y: 16,
    titulo: 'Airflow',
    subtitulo: 'El histórico, mes a mes',
    tecnologia: 'Airflow 3',
    datos: 'Ficheros',
    tono: 'ambar',
    icono: Workflow,
    queEs: [
      'Es el que hace los deberes del archivo, mes a mes. No cuenta los viajes. Solo dice el orden: primero esto, luego esto. Si un paso falla, se para y no sigue.',
    ],
    queHace: [
      'Cada mes baja de internet la lista de viajes de los taxis de Nueva York y la guarda en el archivador. Ese archivador es S3. Después avisa a Spark para que lea la lista y la convierta en totales. Al final comprueba, por la misma puerta que usamos nosotros, que el mes ha quedado bien publicado.',
      'Si solo quieres una prueba, no baja el mes entero. Usa un fichero corto, de mil viajes.',
    ],
    comoConecta: [
      'No mira los viajes que están llegando ahora. Solo trabaja con ficheros del pasado.',
      'Si te preguntan: Airflow no enseña viajes a nadie. Deja el fichero guardado, y la comprobación final pasa por la puerta de salida, igual que esta web.',
    ],
    enlaces: [{ clave: 'airflow', texto: 'Abrir Airflow' }],
  },
  {
    id: 's3',
    x: 310,
    y: 16,
    titulo: 'S3',
    nombre: 'Almacenamiento S3',
    subtitulo: 'Archivo de viajes',
    tecnologia: 'SeaweedFS',
    datos: 'Viajes',
    tono: 'coral',
    icono: HardDrive,
    queEs: [
      'Es el archivador. Tiene dos cajones. Uno está cerrado con llave y guarda cada viaje. El otro solo tiene el mapa de barrios de Nueva York. Ese mapa no dice quién iba en el taxi.',
    ],
    queHace: [
      'Airflow mete aquí el fichero del mes. Spark lo abre, separa los viajes que están bien de los que están mal, y guarda las dos listas. En la de los malos apunta por qué se descartaron.',
    ],
    comoConecta: [
      'La llave del cajón cerrado la tienen Airflow y Spark. Esta web, el chat y los paneles no pueden abrirlo.',
      'Si te preguntan: un viaje suelto vive aquí, y también un rato en la cola. Lo que nosotros consultamos ya no es ese viaje. Son totales.',
    ],
  },
  {
    id: 'simulador',
    x: 748,
    y: 16,
    titulo: 'Simulador',
    subtitulo: 'Hace como si fuera ahora',
    tecnologia: 'Proveedor de prueba',
    datos: 'Entrada',
    tono: 'verde',
    icono: Radio,
    queEs: [
      'Es un juego de pruebas. Hace como si los taxis circularan ahora, pero en realidad vuelve a enviar viajes de verdad del año 2020.',
    ],
    queHace: [
      'Coge un fichero que ya conocemos y se lo manda a la puerta de entrada, al ritmo que elijas en Operaciones. La hora del viaje sigue siendo de 2020. Cuando decimos «ahora», queremos decir «acabamos de tratarlo».',
    ],
    comoConecta: [
      'Solo habla con la puerta de entrada. No puede abrir el archivador ni la base de datos.',
      'Si te preguntan: si lo paras, dejan de entrar viajes de prueba. No se lleva ningún secreto, porque nunca vio los totales.',
    ],
    ruta: { to: '/operaciones', texto: 'Ir a Operaciones' },
  },
  {
    id: 'captura',
    x: 1048,
    y: 16,
    titulo: 'Captura',
    nombre: 'API de captura',
    subtitulo: 'Entran los viajes',
    tecnologia: 'FastAPI',
    datos: 'De paso',
    tono: 'verde',
    icono: Inbox,
    queEs: [
      'Es la puerta de entrada. Alguien llama, enseña una clave y deja un viaje. Esta puerta no se queda el viaje: lo pasa a la cola y sigue.',
    ],
    queHace: [
      'Por aquí entran los viajes, como mucho de mil en mil, y también los gestos de la mano: piedra, papel, tijera y los demás. Sin la clave, la puerta no abre. Tampoco apunta la carrera en ningún diario. Si miras los registros, el viaje no aparece.',
    ],
    comoConecta: [
      'El simulador llama a esta puerta. Ella deja el viaje en la cola y ya está.',
      'Si te preguntan: aquí se puede dejar un viaje, no pedirlo. Leer lo que ya pasó, no se puede.',
    ],
    enlaces: [{ clave: 'api_captura', texto: 'Abrir la API de captura' }],
  },
  {
    id: 'redpanda',
    x: 1048,
    y: 168,
    titulo: 'Redpanda',
    subtitulo: 'La sala de espera',
    tecnologia: 'API de Kafka',
    datos: 'Viajes',
    tono: 'verde',
    icono: Waypoints,
    queEs: [
      'Es la cola de lo que acaba de llegar. Como en un supermercado: si la caja va lenta, la gente espera sin perder el sitio.',
    ],
    queHace: [
      'Hay dos colas. La de los viajes guarda cada uno un día y después lo tira. La de los gestos los guarda una hora. Si Spark se cae y vuelve a encenderse, recuerda por dónde iba y sigue. No empieza de cero.',
    ],
    comoConecta: [
      'Solo escriben en la cola la puerta de entrada, y solo lee Spark. Nadie más puede asomarse.',
      'Si te preguntan: un viaje no se queda para siempre aquí. Al día siguiente desaparece. Lo que queda para consultar son los totales.',
    ],
  },
  {
    id: 'spark',
    x: 508,
    y: 168,
    titulo: 'Spark',
    subtitulo: 'De viajes a totales',
    tecnologia: 'Spark 4 · Scala',
    datos: 'Viajes',
    tono: 'violeta',
    icono: Flame,
    queEs: [
      'Es quien hace las cuentas. Coge viajes sueltos, que no se pueden enseñar, y los convierte en totales, que sí.',
    ],
    queHace: [
      'Tiene dos trabajos. Uno lee el archivo del mes, de golpe. El otro escucha la cola y, más o menos cada medio minuto, actualiza los totales de lo que acaba de llegar.',
      'Los dos hacen lo mismo. Tiran lo que viene mal y se quedan con lo que viene bien. Luego agrupan de tres maneras: cuántos taxis salieron de una zona en una hora, cuántos salieron de un barrio en un día, y cuántos fueron de un barrio a otro.',
      'Si en un grupo hay menos de 10 viajes, no ponemos el número. Ponemos «menos de 10», para no señalar a poca gente. En el archivo del mes, además, tapamos algún total de más si con una resta se pudiera adivinar un grupo escondido.',
    ],
    comoConecta: [
      'Lee el archivador y la cola. En la base de datos solo escribe totales, nunca la lista de viajes.',
      'Si te preguntan: Spark es el único que ve el viaje entero. Cuando termina, ya no se puede reconstruir una carrera. Tampoco decimos, hora a hora, a qué barrio iba alguien. Así no se pueden seguir sus pasos.',
    ],
    enlaces: [{ clave: 'spark', texto: 'Abrir Spark' }],
  },
  {
    id: 'prometheus',
    x: 16,
    y: 330,
    titulo: 'Prometheus',
    subtitulo: 'Toma el pulso',
    tecnologia: 'Cada 15 segundos',
    datos: 'Métricas',
    tono: 'cian',
    icono: Activity,
    queEs: [
      'Es el enfermero. Cada pocos segundos pregunta a todos: ¿seguís despiertos? No mira los viajes.',
    ],
    queHace: [
      'Pregunta a las puertas, a la cola, al archivador y a Spark. Anota si responden y cuánto trabajo han hecho. También mira cuánto tiempo hace que Spark escribió el último total, para saber si lo que llega en vivo se ha quedado parado.',
    ],
    comoConecta: [
      'Esos apuntes los dibuja Grafana. Esta web los usa para decir si un servicio está bien o se ha caído.',
      'Si te preguntan: miramos si la máquina funciona, no quién iba en el taxi.',
    ],
  },
  {
    id: 'mongo',
    x: 508,
    y: 330,
    titulo: 'MongoDB',
    subtitulo: 'Totales publicados',
    tecnologia: 'publico · auditoría',
    datos: 'Totales',
    tono: 'azul',
    icono: Database,
    queEs: [
      'Es la estantería de lo que ya se puede mirar. Tiene dos baldas. En una solo hay totales. En la otra hay un cuaderno de las preguntas que se han hecho. Ese cuaderno se puede seguir escribiendo, no borrar.',
    ],
    queHace: [
      'Los totales están contados de tres formas: por hora y zona, por día y barrio, y de un barrio a otro. Si un grupo es muy pequeño, el papel dice «oculto» y no trae el número. El cuaderno apunta si la pregunta se aceptó o se rechazó, y qué otra pregunta se ofreció.',
    ],
    comoConecta: [
      'Spark escribe los totales. La puerta de salida es quien los lee para nosotros. Para ver el cuaderno, esta web usa una llave que no abre la balda de los totales.',
      'Si te preguntan: aunque alguien encontrara la contraseña, en la estantería no hay viajes. Hay sumas. Y las páginas del cuaderno no se pueden cambiar: solo se añaden.',
    ],
  },
  {
    id: 'acceso',
    x: 508,
    y: 492,
    titulo: 'API de acceso',
    subtitulo: 'Única puerta de salida',
    tecnologia: 'FastAPI · k = 10',
    datos: 'Totales',
    tono: 'azul',
    icono: ShieldCheck,
    queEs: [
      'Es la única puerta de salida. Esta web, el chat y los paneles tienen que llamar aquí. Nadie abre la estantería por su cuenta.',
    ],
    queHace: [
      'Mira cada pregunta antes de contestar. Tiene que pedir totales, de una hora entera o de un día entero, y como mucho de un mes. Si pides un viaje, una matrícula o una hora con minutos, dice que no y te propone otra pregunta que sí se puede responder.',
      'Los grupos de menos de 10 viajes salen como «menos de 10». No los suma con otros, porque al sumarlos se descubriría el número escondido. Cada sí y cada no queda escrito en el cuaderno.',
    ],
    comoConecta: [
      'Lee los totales y escribe en el cuaderno. Esta web entra con su nombre, y el chat con el suyo, para saber quién preguntó.',
      'Si te preguntan: da igual cómo esté escrita la frase. Esta puerta no entrega un viaje. Y el programa que redacta no puede inventarse un número que ella no le haya dado.',
    ],
    enlaces: [{ clave: 'api_acceso', texto: 'Abrir la API de acceso' }],
  },
  {
    id: 'grafana',
    x: 16,
    y: 656,
    titulo: 'Grafana',
    subtitulo: 'Paneles y alertas',
    tecnologia: 'Prometheus',
    datos: 'Métricas',
    tono: 'cian',
    icono: LineChart,
    queEs: [
      'Son los dibujos del enfermero: unos paneles que dicen si todo va bien. No tienen llave del archivador ni de la cola.',
    ],
    queHace: [
      'Enseñan tres cosas. Si los datos están frescos. Si algún servicio se ha caído. Y si hay mucha gente pidiendo cosas que la puerta rechaza. Esas alarmas se ven aquí. No llega un correo.',
    ],
    comoConecta: [
      'Los números le llegan de Prometheus. Si en un panel sale un total de viajes, ese total ya pasó por la puerta de salida.',
      'Si te preguntan: aquí se ve si el sistema respira, no el camino de una persona.',
    ],
    enlaces: [{ clave: 'grafana', texto: 'Abrir Grafana' }],
  },
  {
    id: 'portal',
    x: 268,
    y: 656,
    titulo: 'Portal web',
    subtitulo: 'Esta aplicación',
    tecnologia: 'React · BFF',
    datos: 'Totales',
    tono: 'azul',
    icono: Server,
    queEs: [
      'Es esta página. Tú hablas con ella. Ella habla con los demás, y no te enseña las llaves.',
    ],
    queHace: [
      'Cuando pides un total, se lo pide a la puerta de salida y te enseña lo que vuelve. Cuando miras el cuaderno de preguntas, usa una llave que solo abre ese cuaderno. Cuando lanzas la carga de un mes, se lo pide a Airflow sin enseñarte su contraseña. El chat, antes de pensar, tira las peticiones de un viaje concreto.',
    ],
    comoConecta: [
      'No está en la habitación del archivador ni de la cola. No puede abrirlos.',
      'Si te preguntan: aunque esta página fallara, lo máximo que puede pedir es lo que la puerta de salida ya está dispuesta a dar.',
    ],
  },
  {
    id: 'chatbots',
    x: 760,
    y: 656,
    titulo: 'Chatbots',
    subtitulo: 'Hablan de los totales',
    tecnologia: 'Chainlit',
    datos: 'Totales',
    tono: 'cian',
    icono: MessageSquareText,
    queEs: [
      'Es el asistente con el que se puede hablar. Hay dos ventanas. Una piensa en este ordenador. La otra, además, busca en los apuntes del proyecto.',
    ],
    queHace: [
      'No sabe pedir un viaje. Solo sabe pedir totales a la puerta de salida. Antes de pensar, mira si le estás pidiendo algo de una persona: un viaje, una matrícula, una hora con minutos. Si es así, ni siquiera se lo cuenta. Si en la pregunta hay un día, te propone la cuenta más parecida que sí se puede hacer. Cuando responde, miramos cada número. Si no estaba en los datos de esa conversación, lo quitamos.',
      'La ventana que busca en los apuntes solo guarda totales que ya salieron por la puerta, y la documentación. Nunca guarda la lista de viajes.',
    ],
    comoConecta: [
      'Usa la misma puerta que esta web. Los gestos de la mano le llegan como un aviso. No está mirando la cola.',
      'Si te preguntan: quien escribe la frase es el programa. Quien decide qué números existen es la puerta. Si todo está oculto, contestamos sin pedirle que invente.',
    ],
    enlaces: [
      { clave: 'chatbot', texto: 'Abrir con Ollama' },
      { clave: 'chatbot_rag', texto: 'Abrir con documentación' },
    ],
  },
  {
    id: 'ollama',
    x: 1048,
    y: 656,
    titulo: 'Ollama',
    subtitulo: 'Redacta aquí',
    tecnologia: 'llama3.1 · 8B',
    datos: 'Modelo',
    tono: 'violeta',
    icono: Bot,
    queEs: [
      'Es el programa que redacta, y vive en este ordenador. No guarda viajes. No abre cajones. Solo recibe el resumen que ya hemos filtrado y lo cuenta con palabras.',
    ],
    queHace: [
      'Le damos la tabla de totales de esa pregunta y le pedimos que la explique. Si la tabla está vacía porque todo era demasiado pequeño, no le pedimos que se invente cifras.',
    ],
    comoConecta: [
      'Lo usan el asistente de este ordenador y el chat de esta web. La otra ventana, cuando usa un programa de fuera, revisa antes que no se vaya ningún dato que no haya salido por la puerta.',
      'Si te preguntan: si se inventa un número, lo borramos. Ese número no estaba en la tabla.',
    ],
  },
]

export const ARISTAS: Arista[] = [
  { desde: 'airflow', hasta: 's3', etiqueta: 'Histórico', tono: 'ambar', salida: 'derecha', entrada: 'izquierda' },
  { desde: 's3', hasta: 'spark', etiqueta: 'Lote', tono: 'coral', salida: 'abajo', entrada: 'arriba', desplazaEntrada: -48, tEtiqueta: 0.55 },
  { desde: 'simulador', hasta: 'captura', etiqueta: 'En vivo', tono: 'verde', salida: 'derecha', entrada: 'izquierda' },
  { desde: 'captura', hasta: 'redpanda', etiqueta: 'Cola', tono: 'verde', salida: 'abajo', entrada: 'arriba' },
  { desde: 'redpanda', hasta: 'spark', etiqueta: 'Cada 30 s', tono: 'verde', salida: 'izquierda', entrada: 'derecha' },
  { desde: 'spark', hasta: 'mongo', etiqueta: 'Agregados', tono: 'violeta', salida: 'abajo', entrada: 'arriba' },
  { desde: 'mongo', hasta: 'acceso', etiqueta: 'Consulta', tono: 'azul', salida: 'abajo', entrada: 'arriba' },
  { desde: 'acceso', hasta: 'portal', etiqueta: 'Portal', tono: 'azul', salida: 'abajo', entrada: 'arriba', desplazaSalida: -46, tEtiqueta: 0.42 },
  { desde: 'acceso', hasta: 'chatbots', etiqueta: 'Asistente', tono: 'cian', salida: 'abajo', entrada: 'arriba', desplazaSalida: 46, tEtiqueta: 0.42 },
  { desde: 'chatbots', hasta: 'ollama', etiqueta: 'Redacta', tono: 'violeta', salida: 'derecha', entrada: 'izquierda' },
  { desde: 'prometheus', hasta: 'grafana', etiqueta: 'Paneles', tono: 'cian', salida: 'abajo', entrada: 'arriba' },
]

export const TONOS: Record<Tono, { fondo: string; texto: string; pastilla: string; linea: string }> = {
  coral: { fondo: 'bg-[#fff1ea]', texto: 'text-[#c45c32]', pastilla: 'bg-[#fff1ea] text-[#c45c32]', linea: '#e8926a' },
  verde: { fondo: 'bg-[#e8faf2]', texto: 'text-[#17875a]', pastilla: 'bg-[#e8faf2] text-[#17875a]', linea: '#3dbe8b' },
  violeta: { fondo: 'bg-[#f3eeff]', texto: 'text-[#6d4eae]', pastilla: 'bg-[#f3eeff] text-[#6d4eae]', linea: '#a78bfa' },
  azul: { fondo: 'bg-[#eaf2ff]', texto: 'text-[#2f62c4]', pastilla: 'bg-[#eaf2ff] text-[#2f62c4]', linea: '#60a5fa' },
  ambar: { fondo: 'bg-[#fff6e4]', texto: 'text-[#b7791f]', pastilla: 'bg-[#fff6e4] text-[#b7791f]', linea: '#f0b429' },
  cian: { fondo: 'bg-[#e7f8f8]', texto: 'text-[#0e7c7c]', pastilla: 'bg-[#e7f8f8] text-[#0e7c7c]', linea: '#2eb8b8' },
}
