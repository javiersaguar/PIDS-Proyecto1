# Entrenamiento y evaluación — PIDS 26/27, Project 1

Pipeline local y reproducible que sustituye al notebook de Colab `HAR_mediapipe.ipynb`:
de las tomas grabadas con el kit al informe para la memoria y al modelo listo para la demo.

```
tomas (JPG) ─► preprocesar.py ─► entrenar.py ─► informe.md + figuras + tablas
                (landmarks)       (evalúa)          │
                                                    └─► exportar_modelo.py ─► modelo para la demo
```

## Estructura

```
entrenamiento/
├── preprocesar.py        PASO 1  busca tomas, extrae landmarks (caché) y comprueba su calidad
├── entrenar.py           PASO 2  rejilla de experimentos + evaluación + informe
├── evaluar.py                    regenera tablas/figuras/informe sin reentrenar
├── exportar_modelo.py    PASO 3  modelo definitivo con todas las tomas, para la demo
├── entrenar_todo.py      PASOS 2+3 el plan completo (≤ 2 h en la RTX 5070) + comparativa + exportación
├── hgr/                  el paquete
│   ├── tomas.py            descubrir tomas y sus imágenes
│   ├── extraccion.py       MediaPipe en paralelo con caché por toma
│   ├── features.py         normalizaciones, espejo, aumentación, formato de entrada
│   ├── protocolos.py       particiones aleatorio / temporal / LOPO
│   ├── modelos.py          CNN del enunciado, CNN del repo, MLP, SVM, RF, kNN, regresión logística
│   ├── experimento.py      ejecución paralela y reproducible de la rejilla
│   ├── evaluacion.py       agregación, tablas, informe.md
│   ├── metricas.py         accuracy, F1, matrices de confusión, confusiones
│   ├── rendimiento.py      tamaño y latencia (Keras, scikit-learn, TFLite, MediaPipe)
│   ├── graficas.py         figuras PNG + PDF
│   ├── inferencia.py       ClasificadorGestos: el mismo preprocesado para la demo
│   └── exportacion.py      modelo final + comprobación de paridad
├── tests/                47 tests (unitarios y de extremo a extremo)
├── datos/                aquí se descomprimen las tomas de los compañeros   [no se versiona]
├── cache/                landmarks extraídos                                [no se versiona]
├── resultados/<nombre>/  un experimento por carpeta                         [no se versiona]
└── modelos/<nombre>/     modelos exportados                                 [no se versiona]
```

Se ejecuta con el entorno del proyecto (`C:\Users\Javier\PIDS_HandPose\.venv`, Python 3.12,
Keras 3 con backend PyTorch en GPU NVIDIA RTX 5070 Laptop con CUDA 12.8, sin TensorFlow por Smart App Control). Dependencias exactas en `requirements.txt`.

## Flujo de trabajo

Todos los comandos, desde `C:\Users\Javier\PIDS_HandPose\entrenamiento`:

### 0. Recoger las tomas

Descomprime el `.zip` de cada compañero dentro de `datos/`. Da igual si queda una carpeta
dentro de otra: las tomas se buscan de forma recursiva. Las tomas grabadas en este portátil con
el kit (`kit-grabacion/HAR_mediapipe/data/`) se encuentran solas.

### 1. Preprocesar y verificar

```
..\.venv\Scripts\python.exe preprocesar.py
```

Ejecútalo **cada vez que llegue una toma**: sólo procesa lo nuevo (el resto sale de la caché) y
avisa si algo no cuadra: gestos con menos de 100 imágenes, fotos negras, detección de la mano por
debajo del 90 % en algún gesto, lateralidad mezclada (¿cambió de mano?), tomas incompletas o un
participante con dos tomas. La tabla queda en `cache/verificacion_tomas.csv`.

### 2. Entrenar y evaluar: todo el plan en una orden

```
..\.venv\Scripts\python.exe entrenar_todo.py
```

Ejecuta, en orden de prioridad y con un **presupuesto de 115 minutos** (`--presupuesto-min` para cambiarlo):

| Experimento | Qué cubre de la presentación | Rejilla |
|---|---|---|
| `principal` | **mínimo** (entrenar, evaluar, discutir) + mejora 1 (SVM/MLP/ligeros y trade-off de tiempo y tamaño) + mejora 3 (normalizaciones) | cnn_baseline, mlp, svm, random_forest, knn, logreg × 4 normalizaciones × temporal y LOPO × 3 semillas |
| `espejo` | mejora 6 (invarianza izquierda/derecha) reflejando según la lateralidad de MediaPipe | cnn_baseline, mlp, svm, logreg × 2 normalizaciones × LOPO × 3 semillas |
| `aumento` | mejora 3 (aumentación: giros, zoom, desplazamiento, ruido) | ídem × sin normalizar y normalización completa × LOPO × 2 semillas |
| `volteo` | mejoras 3 y 6: aumentación que también voltea | ídem × normalización completa × LOPO × 2 semillas |
| exportación | el mejor modelo en LOPO (y la mejor CNN) listos para la demo | — |

Antes de cada experimento estima su duración con los tiempos medidos en los anteriores; si no cabe,
lo reduce a una semilla o lo salta, y lo dice en el log (`[RECORTE]`). Nunca corta uno a medias. Deja:
- `resultados/plan_<fecha>_<experimento>/` (un informe por experimento),
- `resultados/plan_<fecha>_comparativa.md` (todos juntos, ordenados por accuracy LOPO),
- `resultados/plan_<fecha>.log`,
- los modelos en `modelos/plan_<fecha>_<modelo>_<normalizacion>/`.

Las redes entrenan en la **GPU NVIDIA** (8 procesos, `--workers-gpu`) y scikit-learn en CPU (12 procesos).
Para vigilar la GPU: `nvidia-smi -l 2`.

**Qué se ha quitado de la rejilla por redundante** (sigue disponible a mano con `entrenar.py`):
- `cnn_repo`: es la CNN1 del notebook, que ya entrena `HAR_mediapipe_local.ipynb`.
- Protocolo `aleatorio`: la presentación pide "una partición adecuada"; `temporal` es la del grabador
  de la asignatura, LOPO es la honesta, y la diferencia entre ambas ya muestra el optimismo.
- Duración de las redes: hasta 200 épocas con paciencia 20, en vez de 300 y 50. Con las tomas reales la
  mejor época llega de media en la 23 (LOPO) y la 53 (temporal); con paciencia 50 se gastaba la mayor
  parte del tiempo entrenando épocas que no mejoraban.

Experimentos sueltos:

```
..\.venv\Scripts\python.exe entrenar.py --rapido --nombre prueba
..\.venv\Scripts\python.exe entrenar.py --nombre principal
..\.venv\Scripts\python.exe entrenar.py --nombre espejo --normalizaciones muneca_escala_rot --protocolos lopo --espejo
..\.venv\Scripts\python.exe entrenar.py --nombre aumento --aumentar 3
..\.venv\Scripts\python.exe entrenar.py --nombre completa_con_todo --modelos todos --protocolos todos
```

Resultado de cada experimento en `resultados/<nombre>/`:

| Fichero | Contenido |
|---|---|
| `informe.md` | **Todo el análisis en una página**: dataset (con la tabla gesto → comando del tanque y las pruebas de diversidad de distancias y ángulos), resultado principal, brecha entre protocolos, métricas por gesto, confusiones, accuracy por participante, coste computacional, invarianza izquierda/derecha y tabla completa |
| `figuras/` | PNG (200 dpi) y PDF vectorial de cada figura |
| `tablas/` | cada tabla en CSV |
| `resultados_pliegues.csv` | una fila por trabajo, con accuracy normal y con la mano opuesta simulada, tiempo y dispositivo (GPU/CPU) |
| `predicciones.csv.gz` | cada predicción de test, para cualquier análisis posterior |
| `config.json` | configuración, versiones de las librerías y resumen del dataset |

`evaluar.py --experimento <nombre>` rehace tablas, figuras e informe sin reentrenar.
Un experimento existente **nunca se sobreescribe**: usa otro `--nombre`.

### 3. Exportar el modelo para la demo

`entrenar_todo.py` ya lo hace. A mano, con la configuración que prefieras:

```
..\.venv\Scripts\python.exe exportar_modelo.py --modelo cnn_baseline --normalizacion muneca_escala_rot --experimento plan_<fecha>_principal --nombre cnn_final
```

Queda en `modelos/<nombre>/` con `modelo.keras` (o `modelo.joblib`), `etiquetas.json` (clases en orden
de salida), `preprocesado.json`, `ficha.json` y las curvas. TFLite solo se genera si hay TensorFlow, que
en este portátil no se puede usar (Smart App Control).

### 4. Demo en tiempo real (pasos 12-13 de la presentación)

`work/HAR_mediapipe/src/demo-gestures-PIDS.py` es la copia de `demo-custom-dataset.py` que pide la
presentación, con las clases en orden alfabético y `None` al final, y muestra el comando del tanque.
Desde `C:\Users\Javier\PIDS_HandPose`:

```
.venv\Scripts\python.exe work\HAR_mediapipe\src\demo-gestures-PIDS.py
.venv\Scripts\python.exe work\HAR_mediapipe\src\demo-gestures-PIDS.py --modelo entrenamiento\modelos\<exportado>
```

La primera usa el modelo que guarda el notebook; la segunda, uno exportado por el pipeline (con su
normalización). `q` para salir. Con `--imagenes <carpeta> --sin-ventana` se prueba sobre fotos, sin cámara.

### Tests

```
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Los de extremo a extremo usan el dataset de ejemplo del repositorio de la asignatura
(`upstream/HAR_mediapipe/data/new_dataset`) repartido entre 5 participantes ficticios, en una
carpeta con tildes, y tardan alrededor de un minuto. **Sus cifras de accuracy no significan nada**
(en realidad es una sola persona): comprueban la mecánica, no el rendimiento.

---

## Decisiones técnicas

### 1. Extraer los landmarks una vez y guardarlos

MediaPipe es lo caro (16 ms por imagen). Se extrae una vez por toma, en paralelo, y se guarda en
`cache/landmarks/<toma>.csv` con una huella de las imágenes, el modelo y el umbral: si nada cambia,
no se repite. Se guardan x, y, z normalizadas a la imagen, los *world landmarks* en metros y la
lateralidad, para poder probar otras entradas sin volver a procesar. Las imágenes sin mano se
conservan marcadas, para informar de la tasa de detección, y se excluyen al entrenar. El detector
usa los mismos parámetros que el grabador y la demo (`num_hands=1`, confianza 0,5).

### 2. Corregir el aspecto antes de cualquier geometría

MediaPipe divide x entre el **ancho** e y entre el **alto**. En 1280×720 una unidad de x mide 1,78
veces una de y, así que girar o medir distancias sobre esas coordenadas deforma la mano. Se
trabaja en unidades de alto de imagen (x·ancho/alto, y). Hay un test que demuestra que, sin esta
corrección, la normalización de rotación deja de ser invariante.

### 3. Normalizaciones, y los fallos que corrigen

| Nombre | Qué hace | Por qué |
|---|---|---|
| `ninguna` | coordenadas crudas de MediaPipe | Lo que hace **de verdad** el notebook: `norm_type = "None"` y la condición `norm_type == "L0"` nunca se cumple. La posición de la mano en el encuadre pasa a ser una *feature*. |
| `muneca` | todo relativo a la muñeca, **incluida** la muñeca | `normalize_from_0_landmark` del repo empieza el bucle en `k=2` y deja `x0, y0` en coordenadas absolutas. |
| `muneca_escala` | ÷ distancia muñeca → nudillo del corazón (0 → 9) | Quita la distancia a la cámara. Esa longitud apenas cambia entre gestos porque la palma no se deforma. |
| `muneca_escala_rot` | + giro para que ese vector apunte arriba | Quita la inclinación en el plano. Coste: dos gestos que sólo difirieran en orientación (pulgar arriba / abajo) serían inseparables. En nuestras clases no pasa. |

Todas las invarianzas están comprobadas numéricamente en `tests/test_features.py`: una mano
desplazada, escalada ×2,7 o girada 150° produce exactamente la misma entrada.

### 4. Tres protocolos de evaluación, y el de referencia es LOPO

| Protocolo | Train / test | Qué mide |
|---|---|---|
| `aleatorio` | 70/30 al azar sobre todos los fotogramas | Techo optimista. Fotogramas casi idénticos, a 1 s de distancia, caen a ambos lados. |
| `temporal` | primeros 70 / últimos 30 de cada toma y gesto | La partición del grabador de la asignatura: mismas personas en train y test. |
| `lopo` | entrena con 4 personas, evalúa con la 5ª, cinco veces | Lo que importa en la demo: reconocer a alguien **que el modelo no ha visto nunca**. |

El mejor modelo se elige **siempre** con LOPO. El informe incluye la brecha entre protocolos: es el
optimismo que se habría reportado sin separar participantes, y es un argumento central de la memoria.

### 5. La validación nunca sale del test

El early stopping necesita un conjunto de validación. El notebook usaba **el propio test**
(`validation_data=(x_test, ...)` con `restore_best_weights=True`), así que el test elegía el
modelo y su accuracy estaba sesgada. Aquí la validación son los últimos fotogramas de cada toma y
gesto **dentro de la parte de entrenamiento**. Son los últimos y no fotogramas al azar para que la
validación no esté llena de gemelos de fotogramas de train.

### 6. Comparación justa

Todos los modelos se entrenan con **el mismo conjunto de train**; la validación sólo la usan las
redes para parar. Las redes usan los hiperparámetros del notebook (AdamW lr=1e-3, weight_decay=1e-4,
batch 32) salvo la duración: hasta 200 épocas con paciencia 20 (ver el apartado 2 del flujo) y los modelos clásicos, valores por defecto razonables
**sin ajustarlos sobre el test**.

### 7. Los modelos

- `cnn_baseline`: la CNN **del enunciado**, con dos Conv2D de 16 filtros y kernel 5×1 (23 126 parámetros).
- `cnn_repo`: la CNN1 que construye **de verdad** el notebook. Tiene **una** sola Conv2D (la segunda está comentada) y Dropout 0,3 (21 830 parámetros). La del enunciado y la del código no coinciden. Fuera de la rejilla por defecto: ya la entrena el notebook (`--modelos todos` la incluye).
- `mlp`, `svm`, `random_forest`, `knn`, `logreg`: alternativas para el análisis de trade-off. Si la regresión logística se acerca a la CNN, el problema es casi linealmente separable tras normalizar, y es un resultado en sí mismo.

No se usa la clase `NO_GESTURE` del notebook: son **filas de 42 ceros idénticas** metidas en train y
en test, trivialmente separables, que inflan la accuracy. En la demo, «ningún gesto» se resuelve
mejor con un umbral sobre la confianza.

### 8. Cómo se resumen las cifras

Dentro de cada pliegue se promedia sobre semillas. Entre pliegues se da media y desviación típica:
en LOPO esa desviación es la **variabilidad entre personas**, la incertidumbre que de verdad importa.
El IC al 95 % de `common/evaluation.py` se incluye para comparar con el enunciado, avisando de que
supone muestras independientes. No lo son: son 100 fotogramas seguidos de la misma persona.

### 9. Reproducibilidad
 
Semillas fijas (Python, NumPy, Keras/PyTorch), cuBLAS determinista (`CUBLAS_WORKSPACE_CONFIG=:4096:8`),
algoritmos deterministas de PyTorch activados y un hilo por trabajo. Cada trabajo depende sólo de su semilla, no del orden ni del número de procesos en paralelo. Un test lo verifica: el mismo trabajo en dos procesos distintos da predicciones idénticas.
 
### 10. Coste computacional medido con la CPU libre
 
Tamaño y latencia se miden **al terminar** el entrenamiento, modelo a modelo, en un proceso aparte
con batch 1 y un hilo, que es lo representativo de la demo y de una Raspberry Pi o un móvil. Medirlo
mientras los demás procesos entrenan inflaba las latencias entre 10 y 20 veces. Dado que Smart App Control
bloquea las librerías de TensorFlow en Windows 11 nativo, el formato de despliegue principal es `.keras`
con inferencia PyTorch y `.joblib` para modelos clásicos (TFLite queda disponible condicionalmente si TF está instalado).
Se mide además el extractor de MediaPipe, porque la latencia real de la demo es extractor + clasificador, y domina el extractor.

### 11. Del entrenamiento a la demo sin desajustes

El demo del repo tenía la lista de clases escrita a mano (6 nombres para un modelo de 7 salidas) y
un preprocesado independiente del entrenamiento. El modelo exportado viaja con sus clases y su
preprocesado, `ClasificadorGestos` usa **las mismas funciones** que el entrenamiento, y la exportación
**falla** si las predicciones de la carpeta exportada no coinciden con las del modelo entrenado.

### 12. Robustez en Windows

Rutas con tildes o eñes (`C:\Users\José`): `cv2.imread`/`cv2.imwrite` y el `model_asset_path` de
MediaPipe fallan con ellas, así que se lee con `np.fromfile` + `cv2.imdecode` y el modelo de MediaPipe
se carga desde memoria. Nada se sobreescribe: tomas, experimentos y modelos exportados van siempre a
carpetas nuevas.

### 13. Invarianza izquierda/derecha: cómo se evalúa sin grabar con la otra mano

Nadie grabó con la otra mano, así que cada muestra de test se **refleja horizontalmente** (la misma pose
hecha con la mano contraria) y se intercambia la etiqueta Left/Right que daría MediaPipe. Todos los
experimentos informan de la accuracy normal y de esta (`accuracy_espejado`); una caída grande indica que
el modelo depende de con qué mano se haga el gesto.

Hallazgo importante: la etiqueta Left/Right de MediaPipe **no es fiable con estas tomas**. Sale ~50 % en cada
persona y gesto, y cambia unas 19 veces en cada secuencia de 100 fotogramas, con confianza media de 0,98.
Causa probable: al girar la muñeca se ve el dorso, y el dorso de una mano tiene en 2D la misma forma que la
palma de la contraria. Por eso se comparan las dos estrategias: `--espejo` (reflejar según esa etiqueta) y
`--voltear` (aprender las dos lateralidades con datos, sin depender de la etiqueta).

### 14. Gestos y comandos del tanque

La presentación exige que los gestos cubran comandos del vehículo del Project 2. La correspondencia está
en `hgr/constantes.py` (`COMANDOS_TANQUE`), aparece en cada informe y la demo la muestra en pantalla:
paper → PARAR, thumbsup → AVANZAR, rock → RETROCEDER, ok → GIRAR, rockandroll → DISPARAR,
scissors → HACER FOTO.

### 15. Diversidad del dataset, con números

La presentación pide variedad de participantes, ángulos y distancias. Cada informe incluye, por
participante, el rango del tamaño de la mano en la imagen (distancia a la cámara), su inclinación y la
posición de la muñeca en el encuadre, y la figura `diversidad_dataset`.

### 16. La GPU en este problema

Las redes son diminutas (23 126 parámetros la CNN) y la entrada son 42 números, así que el tiempo por paso
lo domina Python, no el cálculo: una época sola tarda lo mismo en la RTX 5070 que en la CPU (~314 ms con
2100 muestras). La GPU aporta al repartirse entre varios entrenamientos a la vez (8 procesos, ~75 % de
uso), no por acelerar cada uno. Es un dato útil para la discusión de despliegue: para inferencia, un
modelo así no necesita GPU.
