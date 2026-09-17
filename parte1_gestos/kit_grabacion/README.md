# Grabación del dataset de gestos — PIDS 26/27, Project 1

Kit para grabar tu toma del dataset de reconocimiento de gestos de mano.
Somos **5 participantes** y cada uno graba **una toma**: 6 gestos × 100 imágenes.
Tardarás unos **25 minutos** en total (10 de instalación la primera vez, ~12 de grabación).

Adaptado de [`efhes/IE-workspace`](https://github.com/efhes/IE-workspace) para
funcionar en **Windows nativo con la webcam del portátil**, sin Raspberry Pi y sin WSL.

---

## 1. Los 6 gestos

Se graba **una sola mano**. Usa **la misma mano** durante toda tu toma.

| Clase | Gesto | Cómo se hace |
|---|---|---|
| `ok` | 👌 OK | Pulgar e índice formando un círculo cerrado; los otros tres dedos **extendidos y separados** hacia arriba |
| `paper` | ✋ Papel | Mano completamente abierta, cinco dedos extendidos y **separados entre sí**, palma hacia la cámara |
| `rock` | ✊ Piedra | Puño cerrado, palma hacia la cámara, **pulgar recogido por delante** de los dedos |
| `rockandroll` | 🤘 Cuernos | Índice y meñique extendidos; corazón y anular doblados con el pulgar encima |
| `scissors` | ✌️ Tijera | Índice y corazón extendidos en V **bien abierta**; el resto cerrado |
| `thumbsup` | 👍 Pulgar arriba | Puño cerrado con el **pulgar extendido hacia arriba**, bien separado del puño |

> **Ojo con estos dos pares**, son los que el modelo confundirá si se hacen con desgana:
> - `rock` vs `thumbsup`: se diferencian **sólo en el pulgar**. En `rock` recógelo del todo; en `thumbsup` sepáralo bien y apúntalo claramente hacia arriba.
> - `scissors` vs `rockandroll`: abre bien la V de `scissors` y asegúrate de que en `rockandroll` el corazón y el anular quedan claramente doblados.

---

## 2. Tu identificador de participante

Javier os asigna uno a cada uno: **`p1`, `p2`, `p3`, `p4` o `p5`**. Apúntatelo: el
grabador te lo pregunta al arrancar.

Es importante que **cada persona use el suyo y sólo el suyo**. No se puede perder
ninguna grabación (cada toma va a una carpeta nueva con fecha y hora), pero si dos
personas usan el mismo identificador, al entrenar parecerán la misma persona y se
estropea la evaluación por participantes.

---

## 3. Instalación (sólo la primera vez)

**Necesitas Python 3.12.** No vale el 3.13 (aún no hay versión estable de MediaPipe).
Compruébalo con `py -0p`. Si no lo tienes: <https://www.python.org/downloads/release/python-3129/>
(marca **"Add python.exe to PATH"** al instalar).

Abre PowerShell y ejecuta, una línea cada vez:

```powershell
git clone https://github.com/javiersaguar/PIDS-Grabaci-n-Dataset.git
cd PIDS-Grabaci-n-Dataset
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

La última tarda unos minutos (descarga ~150 MB). **Si ya tenías el kit instalado de antes**, actualízalo con `git pull` y vuelve a ejecutar esa última línea: cambió la versión de MediaPipe. Si no tienes `git`, descarga el
ZIP desde el botón verde **Code → Download ZIP** y descomprímelo.

---

## 4. Grabar

### Opción A — doble clic (recomendada)

Doble clic en **`grabar_dataset.bat`**. Te pregunta:

```
  Tu identificador de participante (p1, p2, p3, p4 o p5): p3
  Mano con la que vas a grabar (izquierda / derecha): derecha
```

### Opción B — desde PowerShell, dentro de la carpeta del proyecto

```powershell
.\grabar_dataset.bat --participante p3 --mano derecha
```

### Prueba antes de la toma buena (opcional pero útil)

```powershell
.\grabar_dataset.bat --participante p3 --prueba
```

Graba sólo 5 imágenes por gesto (~40 s en total) en `data\_pruebas\`, que **no cuenta
para el dataset**. Sirve para comprobar que la cámara, la luz y la detección van bien.

### El proceso

La primera vez **puede tardar hasta 2 minutos** en abrirse la ventana de vídeo
mientras carga las librerías. **No lo lances dos veces**: dos grabadores abiertos se
pelean por la cámara.

Después, **para cada uno de los 6 gestos**:

1. La ventana muestra en verde **`Class to be recorded: <gesto>`**.
2. Coloca la mano haciendo ese gesto y **comprueba que se dibujan los puntos y líneas de colores sobre tu mano**. Si no aparecen, MediaPipe no te está detectando (ver *Problemas*). **No pulses nada hasta ver los landmarks.**
3. Haz clic en la **ventana de vídeo** (no en el terminal) y pulsa **`s`**. Verás `Recording in progress...` en rojo y un contador `Stored images: N/100`.
4. Se captura **1 imagen por segundo durante 100 segundos**. Durante ese tiempo, **muévete** (ver reglas abajo).
5. Al llegar a 100 pasa al siguiente gesto.

Al terminar aparece `Recording finished (completa)`: pulsa `q` y en el terminal verás
un resumen con la carpeta de tu toma.

| Tecla | En la pantalla de espera (verde) | Durante la grabación (rojo) |
|---|---|---|
| `s` | empieza a grabar ese gesto | — |
| `q` | **aborta toda la toma** | corta ese gesto y pasa al siguiente (queda incompleto) |

### Reglas de calidad — esto es lo que hace que el modelo sirva para algo

Durante los 100 segundos de cada gesto, **no te quedes quieto**. Si no te mueves, las
100 imágenes son prácticamente el mismo fotograma repetido: el modelo memoriza tu
postura exacta y luego falla con cualquier otra persona. Varía **despacio y de forma
continua**:

- **Distancia**: acércate hasta ~30 cm de la cámara y aléjate hasta ~1 m, ida y vuelta, varias veces.
- **Ángulo**: gira la muñeca a izquierda y derecha, inclina la mano adelante y atrás.
- **Posición en el encuadre**: mueve la mano por las distintas zonas de la imagen (centro, arriba, abajo, izquierda, derecha).
- **Mantén el gesto reconocible** todo el rato: mover no es deformar.

Y además:

- **Sólo tu mano en cuadro.** El sistema detecta una única mano; si sale otra persona detrás, puede engancharse a la suya.
- **Luz por delante, no por detrás.** Con una ventana a la espalda la mano sale a contraluz y MediaPipe falla.
- **Fondo lo más liso posible** (una pared).
- **Manga corta o remangado**, y sin guantes.

Si algo sale mal (gesto equivocado, te interrumpen...), pulsa `q` y **vuelve a lanzar
la grabación**: se crea una carpeta nueva y la anterior no se toca. Cuando tengas una
toma buena, borra la mala.

---

## 5. Dónde queda guardado

Cada vez que grabas se crea **una carpeta nueva** con tu identificador, la fecha y la hora:

```
HAR_mediapipe\data\gestos_p3_20260914-153012\
├── metadata.json    quién, qué mano, cuándo, y si la toma está completa
├── train\           70 imágenes por gesto
│   ├── ok\               ok_00001.jpg ... ok_00070.jpg
│   ├── paper\  rock\  rockandroll\  scissors\  thumbsup\
└── test\            30 imágenes por gesto
    ├── ok\               ok_00071.jpg ... ok_00100.jpg
    └── ...
```

Son **600 imágenes JPG de 1280×720**, unos **120 MB**. La ruta exacta y el estado de la
toma salen en el resumen final del terminal:

```
========================================================================
 TOMA COMPLETA
========================================================================
 Participante : p3   (mano: derecha)
 Carpeta      : C:\...\HAR_mediapipe\data\gestos_p3_20260914-153012
   ok           100 / 100
   ...
```

El estado puede ser **`completa`** (enviar), **`incompleta`** (algún gesto cortado con `q`)
o **`interrumpida`** (abortada). Sólo se envían las **completas**.

### Comprueba antes de enviar

Abre 3 o 4 imágenes al azar de carpetas distintas y confirma que se ve tu mano, que no
están negras y que el gesto es el que dice la carpeta.

---

## 6. Cómo enviar tu toma

**No subas las imágenes a GitHub** (están en el `.gitignore` a propósito: 120 MB por
persona reventarían el repositorio).

1. Clic derecho sobre **tu carpeta `gestos_pX_...` completa** → **Enviar a → Carpeta comprimida**.
2. **No cambies el nombre** de la carpeta ni del `.zip`: el identificador y la fecha van en él.
3. Sube el `.zip` (~110 MB) a Google Drive / WeTransfer y pasa el enlace a Javier.

---

## 7. Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| La ventana se ve **completamente negra** | El **obturador físico** de la webcam está cerrado, o el interruptor de cámara del portátil (suele ser `Fn` + `F9`/`F10`, busca el icono de cámara tachada). Es el fallo más común. |
| La ventana **tarda en aparecer** | Normal la primera vez (hasta 2 min cargando TensorFlow/MediaPipe). **Espera; no lo relances.** |
| `Una directiva de Control de aplicaciones bloqueó este archivo` (WinError 4551) o el arranque se queda colgado | **Smart App Control** de Windows está bloqueando una librería. Comprueba que instalaste con el `requirements.txt` actual (`mediapipe==0.10.35`: la 1.0.x se bloquea) y que el `.venv` es el de esta carpeta, sin TensorFlow. Si aun así falla, graba en otro portátil. No hace falta desactivar ninguna protección. |
| `[ERROR] No se pudo abrir la camara` | Otra aplicación la está usando. Cierra **Teams, Zoom, Discord, Chrome** y vuelve a lanzarlo. |
| `[ERROR] No encuentro el entorno virtual .venv` | No hiciste la instalación, o la hiciste desde otra carpeta. Repítela **dentro** de la carpeta del proyecto. |
| `identificador de participante no valido` | Escribe sólo letras minúsculas y números, sin espacios: `p3`, no `P 3` ni `p_3`. |
| **No se dibujan los landmarks** sobre la mano | Poca luz, contraluz, mano demasiado lejos o fondo muy cargado. Acércate a ~50 cm, enciende una luz frontal y ponte contra una pared lisa. |
| Pulsas `s` y **no pasa nada** | El foco está en el terminal. Haz clic en la **ventana de vídeo** y vuelve a pulsar. |
| `'py' no se reconoce` | Python no está en el PATH. Reinstálalo marcando *"Add python.exe to PATH"*, o usa `python -m venv .venv`. |
| El vídeo va **a tirones** | En portátiles modestos MediaPipe puede no llegar a 30 fps a 720p. No afecta a la grabación, que va por reloj (1 imagen/segundo). |

---

## 8. Qué hay en este repositorio

```
.
├── grabar_dataset.bat              lanzador (doble clic)
├── requirements.txt                dependencias del kit de grabación
├── common\
│   ├── cameras.py                  acceso a la webcam
│   ├── gui.py                      textos y teclado
│   └── evaluation.py
└── HAR_mediapipe\
    ├── models\hand_landmarker.task modelo de MediaPipe (7.8 MB)
    └── src\
        ├── record_dataset.py       el script de grabación
        ├── config.py               clases, rutas y detector
        └── landmarksLib.py         extracción y dibujo de los 21 landmarks
```

El código de `common\` y `HAR_mediapipe\src\` viene del repositorio de la asignatura,
con parches para que funcione en Windows (el original usa `tty`/`termios`, que sólo
existen en Linux, e imprime emojis que rompen la consola de Windows) y para que las
tomas no se sobreescriban. Los cambios están documentados en comentarios `[PARCHE]` y
`[CAMBIO v2]` dentro de cada fichero.
