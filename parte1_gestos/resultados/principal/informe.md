# Informe del experimento `plan_20260917-0042_principal`

Generado a partir de `plan_20260917-0042_principal`. Entrenado el 2026-09-17T00:42:43 con Keras 3.15.1 (backend torch, dispositivo: cuda: NVIDIA GeForce RTX 5070 Laptop GPU, cpu), scikit-learn 1.9.0 y MediaPipe 0.10.35 (32 CPUs logicas).

**Configuracion:** modelos cnn_baseline, mlp, svm, random_forest, knn, logreg; normalizaciones ninguna, muneca, muneca_escala, muneca_escala_rot; protocolos temporal, lopo; semillas [0, 1, 2]; espejo=False; aumentacion=0 copias; hasta 200 epocas, paciencia 20, batch 32.

## 1. Dataset

3000 imagenes, 2931 con mano detectada (97.7%), 5 participantes, 5 tomas. Clases: `ok`, `paper`, `rock`, `rockandroll`, `scissors`, `thumbsup`.

| participante | tomas | imagenes | con_mano | tasa_deteccion |
|---|---|---|---|---|
| p1 | 1 | 600 | 572 | 95.3% |
| p2 | 1 | 600 | 585 | 97.5% |
| p3 | 1 | 600 | 588 | 98.0% |
| p4 | 1 | 600 | 599 | 99.8% |
| p5 | 1 | 600 | 587 | 97.8% |

Tasa de deteccion de mano (%) por participante y gesto. Las imagenes sin mano no se usan:

| participante | ok | paper | rock | rockandroll | scissors | thumbsup |
|---|---|---|---|---|---|---|
| p1 | 95 | 94 | 92 | 98 | 94 | 99 |
| p2 | 93 | 100 | 98 | 99 | 98 | 97 |
| p3 | 98 | 100 | 97 | 97 | 99 | 97 |
| p4 | 100 | 100 | 99 | 100 | 100 | 100 |
| p5 | 99 | 100 | 89 | 100 | 99 | 100 |

Gestos y comando del vehiculo tanque (Project 2) que activa cada uno:

| gesto | comando_tanque |
|---|---|
| ok | GIRAR |
| paper | PARAR |
| rock | RETROCEDER |
| rockandroll | DISPARAR |
| scissors | HACER FOTO |
| thumbsup | AVANZAR |

**Diversidad de la grabacion** (la presentacion pide distintos participantes, angulos y distancias). Rango del 5 al 95 % por participante: tamano de la mano en la imagen (muneca a nudillo del corazon, en unidades de alto de imagen; mas grande = mas cerca de la camara), su inclinacion respecto a la vertical y la posicion de la muneca en el encuadre. `mediapipe_left_%` es el % de fotogramas que MediaPipe etiqueta como mano izquierda: ronda el 50 % en todos aunque cada persona grabo con una mano, porque al girar la muneca se ve el dorso, y el dorso de una mano tiene en 2D la misma forma que la palma de la contraria. Esa etiqueta no es fiable aqui.

| participante | tamano_mano_p5_p95 | tamano_max_sobre_min | inclinacion_grados_p5_p95 | x_muneca_p5_p95 | y_muneca_p5_p95 | mediapipe_left_% |
|---|---|---|---|---|---|---|
| p1 | 0.10 - 0.26 | 2.5x | -77 - 73 | 0.24 - 0.85 | 0.42 - 0.84 | 48% |
| p2 | 0.14 - 0.41 | 2.9x | -75 - 74 | 0.28 - 0.85 | 0.58 - 0.94 | 48% |
| p3 | 0.17 - 0.29 | 1.7x | -68 - 73 | 0.23 - 0.88 | 0.47 - 0.83 | 41% |
| p4 | 0.16 - 0.30 | 1.9x | -58 - 69 | 0.11 - 0.78 | 0.51 - 0.97 | 44% |
| p5 | 0.11 - 0.24 | 2.1x | -66 - 65 | 0.14 - 0.70 | 0.43 - 0.99 | 49% |

**Avisos:**

- toma con estado "interrumpida" (gestos_p1_20260914-163103): se IGNORA por defecto (usa --incluir-incompletas para incluirla)
- toma con estado "en_curso" (gestos_p1_20260914-163127): se IGNORA por defecto (usa --incluir-incompletas para incluirla)
- toma con estado "en_curso" (gestos_p2_20260914-163325): se IGNORA por defecto (usa --incluir-incompletas para incluirla)
- toma con estado "en_curso" (gestos_p3_20260914-163405): se IGNORA por defecto (usa --incluir-incompletas para incluirla)

## 2. Resultado principal

Protocolo de referencia: **LOPO** (el mas honesto de los ejecutados). Mejor configuracion: **`mlp` con normalizacion `muneca_escala_rot`**: accuracy **96.2%** (desviacion 2.0 pp), F1 macro 96.1%, balanced accuracy 96.1%. IC95 del repo: +/- 0.7 pp (optimista: supone fotogramas independientes).

Accuracy (%) en LOPO, media +/- desviacion:

| modelo | ninguna | muneca | muneca_escala | muneca_escala_rot |
|---|---|---|---|---|
| cnn_baseline | 90.9 +/- 5.2 | 94.8 +/- 1.8 | 94.8 +/- 1.5 | 95.8 +/- 2.2 |
| mlp | 90.3 +/- 5.6 | 94.4 +/- 2.9 | 95.2 +/- 1.6 | 96.2 +/- 2.0 |
| svm | 87.1 +/- 7.7 | 90.2 +/- 4.9 | 94.0 +/- 2.2 | 94.7 +/- 2.9 |
| random_forest | 82.6 +/- 9.2 | 84.0 +/- 7.4 | 90.6 +/- 3.9 | 93.4 +/- 4.5 |
| knn | 68.0 +/- 12.1 | 76.7 +/- 10.5 | 88.0 +/- 5.0 | 91.0 +/- 5.0 |
| logreg | 90.4 +/- 4.0 | 91.1 +/- 3.0 | 92.2 +/- 3.0 | 88.5 +/- 5.0 |

## 3. Cuanto engana un mal protocolo de evaluacion

Misma configuracion (mejor normalizacion de cada modelo en LOPO), evaluada con cada protocolo. La brecha, en puntos porcentuales, es el optimismo que se habria reportado sin separar participantes.

| modelo | normalizacion | temporal | lopo | brecha_temporal_menos_lopo_pp |
|---|---|---|---|---|
| cnn_baseline | muneca_escala_rot | 94.3 | 95.8 | -1.5 |
| mlp | muneca_escala_rot | 95.5 | 96.2 | -0.7 |
| svm | muneca_escala_rot | 92.9 | 94.7 | -1.8 |
| random_forest | muneca_escala_rot | 92.6 | 93.4 | -0.9 |
| knn | muneca_escala_rot | 90.4 | 91.0 | -0.6 |
| logreg | muneca_escala | 92.8 | 92.2 | +0.7 |

## 4. Analisis por gesto y errores

### `mlp`, normalizacion `muneca_escala_rot` (LOPO)

| clase | precision | recall | f1 | soporte |
|---|---|---|---|---|
| ok | 96.2 | 95.4 | 95.8 | 1455 |
| paper | 95.1 | 98.6 | 96.8 | 1482 |
| rock | 94.8 | 95.2 | 95.0 | 1425 |
| rockandroll | 98.9 | 97.0 | 98.0 | 1482 |
| scissors | 97.0 | 93.4 | 95.2 | 1470 |
| thumbsup | 95.2 | 97.5 | 96.4 | 1479 |

Confusiones mas frecuentes:

| real | predicha | n | pct_de_la_clase_real |
|---|---|---|---|
| rock | thumbsup | 34 | 2.4% |
| scissors | thumbsup | 29 | 2.0% |
| thumbsup | rock | 29 | 2.0% |
| ok | paper | 28 | 1.9% |
| scissors | paper | 25 | 1.7% |
| ok | scissors | 22 | 1.5% |
| scissors | ok | 19 | 1.3% |
| rockandroll | rock | 15 | 1.0% |
| rock | ok | 14 | 1.0% |
| scissors | rock | 14 | 1.0% |

Accuracy con cada participante no visto: p1 94.2%, p2 97.6%, p3 97.5%, p4 97.8%, p5 93.8%.

### `cnn_baseline`, normalizacion `ninguna` (LOPO)

| clase | precision | recall | f1 | soporte |
|---|---|---|---|---|
| ok | 89.6 | 89.9 | 89.7 | 1455 |
| paper | 92.7 | 92.7 | 92.7 | 1482 |
| rock | 87.9 | 91.2 | 89.5 | 1425 |
| rockandroll | 94.7 | 91.3 | 93.0 | 1482 |
| scissors | 94.2 | 83.7 | 88.7 | 1470 |
| thumbsup | 87.5 | 96.9 | 92.0 | 1479 |

Confusiones mas frecuentes:

| real | predicha | n | pct_de_la_clase_real |
|---|---|---|---|
| scissors | rock | 104 | 7.1% |
| scissors | thumbsup | 101 | 6.9% |
| ok | paper | 88 | 6.0% |
| paper | ok | 87 | 5.9% |
| rockandroll | thumbsup | 65 | 4.4% |
| rock | ok | 38 | 2.7% |
| rock | thumbsup | 38 | 2.7% |
| rock | scissors | 27 | 1.9% |
| thumbsup | rock | 26 | 1.8% |
| ok | rockandroll | 24 | 1.6% |

Accuracy con cada participante no visto: p1 87.8%, p2 94.9%, p3 93.3%, p4 95.4%, p5 83.3%.

### `cnn_baseline`, normalizacion `muneca_escala_rot` (LOPO)

| clase | precision | recall | f1 | soporte |
|---|---|---|---|---|
| ok | 95.5 | 95.0 | 95.2 | 1455 |
| paper | 95.5 | 97.8 | 96.6 | 1482 |
| rock | 94.3 | 93.7 | 94.0 | 1425 |
| rockandroll | 98.2 | 96.8 | 97.5 | 1482 |
| scissors | 96.2 | 95.1 | 95.7 | 1470 |
| thumbsup | 95.1 | 96.3 | 95.7 | 1479 |

Confusiones mas frecuentes:

| real | predicha | n | pct_de_la_clase_real |
|---|---|---|---|
| rock | thumbsup | 53 | 3.7% |
| thumbsup | rock | 40 | 2.7% |
| ok | paper | 29 | 2.0% |
| scissors | ok | 20 | 1.4% |
| scissors | paper | 20 | 1.4% |
| paper | ok | 20 | 1.3% |
| ok | scissors | 19 | 1.3% |
| rock | ok | 16 | 1.1% |
| rockandroll | scissors | 15 | 1.0% |
| ok | rock | 14 | 1.0% |

Accuracy con cada participante no visto: p1 94.3%, p2 96.8%, p3 97.7%, p4 97.5%, p5 92.6%.

## 5. Coste computacional

Medido al terminar el entrenamiento, modelo a modelo en un proceso aparte con la CPU libre, con batch 1 y un solo hilo (como en la demo, y mas cercano a una Raspberry Pi o un movil). `latencia_ms` es la llamada directa desde Python (Keras o scikit-learn). Mediana de 300 a 1000 repeticiones.

| modelo | familia | parametros | kb_disco | kb_tflite | kb_tflite_cuant | latencia_ms | latencia_tflite_ms |
|---|---|---|---|---|---|---|---|
| cnn_baseline | red neuronal | 23126 | 303.3 |  |  | 1.231 |  |
| knn | clasico |  | 303.8 |  |  | 10.315 |  |
| logreg | clasico |  | 3.4 |  |  | 0.136 |  |
| mlp | red neuronal | 5030 | 86.1 |  |  | 0.841 |  |
| random_forest | clasico |  | 7545.6 |  |  | 6.260 |  |
| svm | clasico |  | 199.8 |  |  | 0.164 |  |
| extractor_mediapipe | extractor |  | 7635.8 |  |  | 16.073 |  |

El extractor de MediaPipe tarda **16.1 ms** por fotograma (1280x720). Con el mejor clasificador (0.841 ms) el techo teorico es ~59 fotogramas por segundo en este portatil, sin contar captura ni dibujo: la latencia la domina el extractor, no el clasificador.

## 5b. Invarianza mano izquierda / derecha

Nadie grabo con la otra mano, asi que se simula: cada muestra de test se refleja horizontalmente (la misma pose hecha con la mano opuesta) y se intercambia la etiqueta Left/Right de MediaPipe. Una caida grande significa que el modelo depende de con que mano se haga el gesto. Configuracion de este experimento: espejo=False, aumentacion con volteo=False.

| modelo | normalizacion | accuracy | accuracy_espejado | caida_pp |
|---|---|---|---|---|
| mlp | muneca_escala_rot | 96.2 | 96.4 | -0.2 |
| cnn_baseline | muneca_escala_rot | 95.8 | 96.0 | -0.2 |
| svm | muneca_escala_rot | 94.7 | 94.8 | -0.1 |
| random_forest | muneca_escala_rot | 93.4 | 94.4 | -1.0 |
| logreg | muneca_escala | 92.2 | 91.5 | +0.7 |
| knn | muneca_escala_rot | 91.0 | 90.3 | +0.7 |

## 6. Tabla completa

| protocolo | normalizacion | modelo | accuracy | accuracy_espejado | dispersion | accuracy_min | f1_macro | balanced_accuracy | ic95_repo | n_pliegues | n_semillas | n_test | epocas | tiempo_entrenamiento_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| temporal | ninguna | cnn_baseline | 92.7 | 92.9 | 0.7 | 92.7 | 92.7 | 92.7 | 1.7 | 1 | 3 | 878 | 96 | 147.8 |
| temporal | ninguna | mlp | 93.4 | 91.5 | 0.3 | 93.4 | 93.4 | 93.4 | 1.6 | 1 | 3 | 878 | 145 | 184.9 |
| temporal | ninguna | svm | 91.0 | 87.1 | 0.1 | 91.0 | 91.0 | 91.0 | 1.9 | 1 | 3 | 878 |  | 0.5 |
| temporal | ninguna | random_forest | 83.3 | 82.8 | 0.2 | 83.3 | 83.4 | 83.3 | 2.5 | 1 | 3 | 878 |  | 1.8 |
| temporal | ninguna | knn | 72.2 | 69.2 |  | 72.2 | 72.5 | 72.2 | 3.0 | 1 | 1 | 878 |  | 0.2 |
| temporal | ninguna | logreg | 91.9 | 90.4 |  | 91.9 | 91.8 | 91.8 | 1.8 | 1 | 1 | 878 |  | 0.2 |
| temporal | muneca | cnn_baseline | 93.4 | 93.4 | 0.3 | 93.4 | 93.3 | 93.3 | 1.6 | 1 | 3 | 878 | 38 | 39.5 |
| temporal | muneca | mlp | 94.2 | 94.0 | 0.3 | 94.2 | 94.1 | 94.1 | 1.5 | 1 | 3 | 878 | 110 | 102.2 |
| temporal | muneca | svm | 91.2 | 92.9 | 0.2 | 91.2 | 91.1 | 91.2 | 1.9 | 1 | 3 | 878 |  | 0.9 |
| temporal | muneca | random_forest | 87.9 | 84.3 | 0.2 | 87.9 | 87.8 | 87.8 | 2.2 | 1 | 3 | 878 |  | 3.9 |
| temporal | muneca | knn | 85.0 | 78.5 |  | 85.0 | 85.0 | 84.9 | 2.4 | 1 | 1 | 878 |  | 0.0 |
| temporal | muneca | logreg | 92.6 | 91.1 |  | 92.6 | 92.5 | 92.5 | 1.7 | 1 | 1 | 878 |  | 0.4 |
| temporal | muneca_escala | cnn_baseline | 93.9 | 93.7 | 0.3 | 93.9 | 93.9 | 93.9 | 1.6 | 1 | 3 | 878 | 35 | 36.2 |
| temporal | muneca_escala | mlp | 94.4 | 94.3 | 0.4 | 94.4 | 94.3 | 94.3 | 1.5 | 1 | 3 | 878 | 72 | 66.9 |
| temporal | muneca_escala | svm | 93.8 | 93.4 | 0.1 | 93.8 | 93.7 | 93.7 | 1.6 | 1 | 3 | 878 |  | 0.8 |
| temporal | muneca_escala | random_forest | 91.3 | 90.7 | 0.4 | 91.3 | 91.2 | 91.2 | 1.9 | 1 | 3 | 878 |  | 4.4 |
| temporal | muneca_escala | knn | 91.9 | 89.2 |  | 91.9 | 91.8 | 91.8 | 1.8 | 1 | 1 | 878 |  | 0.0 |
| temporal | muneca_escala | logreg | 92.8 | 90.9 |  | 92.8 | 92.7 | 92.7 | 1.7 | 1 | 1 | 878 |  | 0.3 |
| temporal | muneca_escala_rot | cnn_baseline | 94.3 | 94.8 | 0.5 | 94.3 | 94.3 | 94.3 | 1.5 | 1 | 3 | 878 | 33 | 34.2 |
| temporal | muneca_escala_rot | mlp | 95.5 | 95.6 | 0.5 | 95.5 | 95.5 | 95.5 | 1.4 | 1 | 3 | 878 | 49 | 45.9 |
| temporal | muneca_escala_rot | svm | 92.9 | 94.1 | 0.2 | 92.9 | 92.9 | 92.9 | 1.7 | 1 | 3 | 878 |  | 0.9 |
| temporal | muneca_escala_rot | random_forest | 92.6 | 93.7 | 0.2 | 92.6 | 92.4 | 92.5 | 1.7 | 1 | 3 | 878 |  | 4.2 |
| temporal | muneca_escala_rot | knn | 90.4 | 90.8 |  | 90.4 | 90.3 | 90.3 | 1.9 | 1 | 1 | 878 |  | 0.0 |
| temporal | muneca_escala_rot | logreg | 90.1 | 88.5 |  | 90.1 | 89.9 | 89.9 | 2.0 | 1 | 1 | 878 |  | 0.3 |
| lopo | ninguna | cnn_baseline | 90.9 | 91.3 | 5.2 | 83.3 | 90.7 | 90.9 | 1.0 | 5 | 3 | 2931 | 63 | 82.4 |
| lopo | ninguna | mlp | 90.3 | 90.1 | 5.6 | 83.4 | 90.0 | 90.2 | 1.1 | 5 | 3 | 2931 | 117 | 134.7 |
| lopo | ninguna | svm | 87.1 | 84.8 | 7.7 | 76.9 | 86.5 | 87.0 | 1.2 | 5 | 3 | 2931 |  | 1.0 |
| lopo | ninguna | random_forest | 82.6 | 82.4 | 9.2 | 69.0 | 82.1 | 82.6 | 1.4 | 5 | 3 | 2931 |  | 3.4 |
| lopo | ninguna | knn | 68.0 | 66.2 | 12.1 | 52.3 | 67.3 | 68.0 | 1.7 | 5 | 1 | 2931 |  | 0.0 |
| lopo | ninguna | logreg | 90.4 | 90.1 | 4.0 | 86.4 | 90.3 | 90.3 | 1.1 | 5 | 1 | 2931 |  | 0.2 |
| lopo | muneca | cnn_baseline | 94.8 | 94.1 | 1.8 | 91.7 | 94.7 | 94.7 | 0.8 | 5 | 3 | 2931 | 45 | 53.6 |
| lopo | muneca | mlp | 94.4 | 94.4 | 2.9 | 89.6 | 94.3 | 94.4 | 0.8 | 5 | 3 | 2931 | 73 | 78.4 |
| lopo | muneca | svm | 90.2 | 89.5 | 4.9 | 83.0 | 90.2 | 90.2 | 1.1 | 5 | 3 | 2931 |  | 1.3 |
| lopo | muneca | random_forest | 84.0 | 82.5 | 7.4 | 75.3 | 83.6 | 84.0 | 1.3 | 5 | 3 | 2931 |  | 4.7 |
| lopo | muneca | knn | 76.7 | 75.3 | 10.5 | 64.3 | 75.8 | 76.7 | 1.5 | 5 | 1 | 2931 |  | 0.0 |
| lopo | muneca | logreg | 91.1 | 91.2 | 3.0 | 86.9 | 91.0 | 91.0 | 1.0 | 5 | 1 | 2931 |  | 0.5 |
| lopo | muneca_escala | cnn_baseline | 94.8 | 94.9 | 1.5 | 92.2 | 94.7 | 94.7 | 0.8 | 5 | 3 | 2931 | 37 | 44.3 |
| lopo | muneca_escala | mlp | 95.2 | 94.7 | 1.6 | 92.5 | 95.1 | 95.1 | 0.8 | 5 | 3 | 2931 | 64 | 68.7 |
| lopo | muneca_escala | svm | 94.0 | 94.2 | 2.2 | 90.3 | 94.0 | 94.0 | 0.9 | 5 | 3 | 2931 |  | 1.0 |
| lopo | muneca_escala | random_forest | 90.6 | 90.8 | 3.9 | 86.2 | 90.5 | 90.6 | 1.1 | 5 | 3 | 2931 |  | 5.3 |
| lopo | muneca_escala | knn | 88.0 | 88.8 | 5.0 | 81.6 | 87.9 | 87.9 | 1.2 | 5 | 1 | 2931 |  | 0.0 |
| lopo | muneca_escala | logreg | 92.2 | 91.5 | 3.0 | 89.0 | 92.0 | 92.1 | 1.0 | 5 | 1 | 2931 |  | 0.3 |
| lopo | muneca_escala_rot | cnn_baseline | 95.8 | 96.0 | 2.2 | 92.6 | 95.7 | 95.7 | 0.7 | 5 | 3 | 2931 | 33 | 39.4 |
| lopo | muneca_escala_rot | mlp | 96.2 | 96.4 | 2.0 | 93.8 | 96.1 | 96.1 | 0.7 | 5 | 3 | 2931 | 47 | 46.1 |
| lopo | muneca_escala_rot | svm | 94.7 | 94.8 | 2.9 | 91.1 | 94.7 | 94.7 | 0.8 | 5 | 3 | 2931 |  | 1.0 |
| lopo | muneca_escala_rot | random_forest | 93.4 | 94.4 | 4.5 | 86.9 | 93.3 | 93.3 | 0.9 | 5 | 3 | 2931 |  | 4.3 |
| lopo | muneca_escala_rot | knn | 91.0 | 90.3 | 5.0 | 83.8 | 91.0 | 90.9 | 1.0 | 5 | 1 | 2931 |  | 0.0 |
| lopo | muneca_escala_rot | logreg | 88.5 | 88.8 | 5.0 | 81.9 | 88.2 | 88.3 | 1.2 | 5 | 1 | 2931 |  | 0.4 |

Cifras de accuracy en %; dispersion y IC en puntos porcentuales. Tablas en `tablas/`.

## 7. Figuras

- [`protocolos_ninguna`](figuras/protocolos_ninguna.png) (tambien en PDF)
- [`protocolos_muneca`](figuras/protocolos_muneca.png) (tambien en PDF)
- [`protocolos_muneca_escala`](figuras/protocolos_muneca_escala.png) (tambien en PDF)
- [`protocolos_muneca_escala_rot`](figuras/protocolos_muneca_escala_rot.png) (tambien en PDF)
- [`normalizaciones_lopo`](figuras/normalizaciones_lopo.png) (tambien en PDF)
- [`tradeoff_latencia`](figuras/tradeoff_latencia.png) (tambien en PDF)
- [`tradeoff_tamano`](figuras/tradeoff_tamano.png) (tambien en PDF)
- [`confusion_mlp_muneca_escala_rot_temporal`](figuras/confusion_mlp_muneca_escala_rot_temporal.png) (tambien en PDF)
- [`confusion_cnn_baseline_ninguna_temporal`](figuras/confusion_cnn_baseline_ninguna_temporal.png) (tambien en PDF)
- [`confusion_cnn_baseline_muneca_escala_rot_temporal`](figuras/confusion_cnn_baseline_muneca_escala_rot_temporal.png) (tambien en PDF)
- [`confusion_mlp_muneca_escala_rot_lopo`](figuras/confusion_mlp_muneca_escala_rot_lopo.png) (tambien en PDF)
- [`confusion_cnn_baseline_ninguna_lopo`](figuras/confusion_cnn_baseline_ninguna_lopo.png) (tambien en PDF)
- [`confusion_cnn_baseline_muneca_escala_rot_lopo`](figuras/confusion_cnn_baseline_muneca_escala_rot_lopo.png) (tambien en PDF)
- [`participantes_mlp_muneca_escala_rot`](figuras/participantes_mlp_muneca_escala_rot.png) (tambien en PDF)
- [`participantes_cnn_baseline_ninguna`](figuras/participantes_cnn_baseline_ninguna.png) (tambien en PDF)
- [`participantes_cnn_baseline_muneca_escala_rot`](figuras/participantes_cnn_baseline_muneca_escala_rot.png) (tambien en PDF)
- [`f1_por_clase_lopo`](figuras/f1_por_clase_lopo.png) (tambien en PDF)
- [`curvas_cnn_baseline_muneca_escala_rot_lopo`](figuras/curvas_cnn_baseline_muneca_escala_rot_lopo.png) (tambien en PDF)
- [`curvas_mlp_muneca_escala_rot_lopo`](figuras/curvas_mlp_muneca_escala_rot_lopo.png) (tambien en PDF)
- [`diversidad_dataset`](figuras/diversidad_dataset.png) (tambien en PDF)
- [`errores_mlp_muneca_escala_rot_lopo`](figuras/errores_mlp_muneca_escala_rot_lopo.png) (tambien en PDF)

## Notas metodologicas

- **Validacion separada del test.** El early stopping usa los ultimos fotogramas de cada toma y gesto dentro de la parte de entrenamiento. El notebook del repo validaba con el test.
- **Mismo train para todos los modelos.** Los clasicos no usan la validacion; asi la comparacion es justa.
- **Imagenes sin mano detectada** se excluyen de entrenamiento y test (ver tasas en la seccion 1).
- **Reproducibilidad.** Semillas fijas, determinismo de TensorFlow activado, oneDNN desactivado y un hilo por trabajo: el resultado de cada trabajo depende solo de su semilla.
- **Temporal = la particion del grabador** (primeros 70 fotogramas a train, ultimos 30 a test). Los fotogramas se capturan a 1 Hz de una misma sesion continua: train y test estan muy correlacionados.
