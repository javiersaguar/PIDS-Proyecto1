# Informe del experimento `plan_20260917-0042_aumento`

Generado a partir de `plan_20260917-0042_aumento`. Entrenado el 2026-09-17T01:10:40 con Keras 3.15.1 (backend torch, dispositivo: cuda: NVIDIA GeForce RTX 5070 Laptop GPU, cpu), scikit-learn 1.9.0 y MediaPipe 0.10.35 (32 CPUs logicas).

**Configuracion:** modelos cnn_baseline, mlp, svm, logreg; normalizaciones ninguna, muneca_escala_rot; protocolos lopo; semillas [0, 1]; espejo=False; aumentacion=3 copias; hasta 200 epocas, paciencia 20, batch 32.

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

Protocolo de referencia: **LOPO** (el mas honesto de los ejecutados). Mejor configuracion: **`mlp` con normalizacion `muneca_escala_rot`**: accuracy **96.1%** (desviacion 2.4 pp), F1 macro 96.1%, balanced accuracy 96.1%. IC95 del repo: +/- 0.7 pp (optimista: supone fotogramas independientes).

Accuracy (%) en LOPO, media +/- desviacion:

| modelo | ninguna | muneca_escala_rot |
|---|---|---|
| cnn_baseline | 91.8 +/- 5.9 | 95.8 +/- 2.5 |
| mlp | 92.2 +/- 5.4 | 96.1 +/- 2.4 |
| svm | 89.0 +/- 6.7 | 94.6 +/- 2.6 |
| logreg | 90.8 +/- 3.3 | 88.8 +/- 4.8 |

## 4. Analisis por gesto y errores

### `mlp`, normalizacion `muneca_escala_rot` (LOPO)

| clase | precision | recall | f1 | soporte |
|---|---|---|---|---|
| ok | 95.4 | 95.8 | 95.6 | 970 |
| paper | 95.9 | 98.4 | 97.1 | 988 |
| rock | 94.4 | 95.1 | 94.7 | 950 |
| rockandroll | 98.5 | 97.2 | 97.8 | 988 |
| scissors | 97.1 | 93.6 | 95.3 | 980 |
| thumbsup | 95.6 | 96.8 | 96.2 | 986 |

Confusiones mas frecuentes:

| real | predicha | n | pct_de_la_clase_real |
|---|---|---|---|
| thumbsup | rock | 26 | 2.6% |
| rock | thumbsup | 23 | 2.4% |
| scissors | ok | 17 | 1.7% |
| scissors | thumbsup | 16 | 1.6% |
| ok | paper | 15 | 1.5% |
| ok | scissors | 14 | 1.4% |
| scissors | paper | 13 | 1.3% |
| paper | ok | 13 | 1.3% |
| rock | ok | 10 | 1.1% |
| scissors | rock | 9 | 0.9% |

Accuracy con cada participante no visto: p1 93.2%, p2 97.8%, p3 97.4%, p4 98.2%, p5 93.9%.

### `cnn_baseline`, normalizacion `ninguna` (LOPO)

| clase | precision | recall | f1 | soporte |
|---|---|---|---|---|
| ok | 93.2 | 89.7 | 91.4 | 970 |
| paper | 92.5 | 93.7 | 93.1 | 988 |
| rock | 87.8 | 95.1 | 91.3 | 950 |
| rockandroll | 96.0 | 91.7 | 93.8 | 988 |
| scissors | 95.4 | 83.1 | 88.8 | 980 |
| thumbsup | 87.3 | 97.6 | 92.1 | 986 |

Confusiones mas frecuentes:

| real | predicha | n | pct_de_la_clase_real |
|---|---|---|---|
| scissors | thumbsup | 78 | 8.0% |
| scissors | rock | 69 | 7.0% |
| ok | paper | 61 | 6.3% |
| paper | ok | 46 | 4.7% |
| rockandroll | thumbsup | 39 | 3.9% |
| rock | thumbsup | 23 | 2.4% |
| rockandroll | rock | 23 | 2.3% |
| rock | scissors | 17 | 1.8% |
| thumbsup | rock | 15 | 1.5% |
| ok | rock | 14 | 1.4% |

Accuracy con cada participante no visto: p1 89.9%, p2 95.2%, p3 94.9%, p4 96.7%, p5 82.2%.

### `cnn_baseline`, normalizacion `muneca_escala_rot` (LOPO)

| clase | precision | recall | f1 | soporte |
|---|---|---|---|---|
| ok | 95.1 | 95.4 | 95.2 | 970 |
| paper | 96.1 | 97.1 | 96.6 | 988 |
| rock | 94.3 | 93.9 | 94.1 | 950 |
| rockandroll | 97.4 | 97.0 | 97.2 | 988 |
| scissors | 97.3 | 94.3 | 95.8 | 980 |
| thumbsup | 94.8 | 97.2 | 95.9 | 986 |

Confusiones mas frecuentes:

| real | predicha | n | pct_de_la_clase_real |
|---|---|---|---|
| rock | thumbsup | 36 | 3.8% |
| thumbsup | rock | 17 | 1.7% |
| ok | paper | 16 | 1.6% |
| scissors | ok | 16 | 1.6% |
| paper | ok | 15 | 1.5% |
| scissors | rock | 13 | 1.3% |
| ok | rock | 12 | 1.2% |
| ok | scissors | 12 | 1.2% |
| scissors | rockandroll | 12 | 1.2% |
| rock | ok | 11 | 1.2% |

Accuracy con cada participante no visto: p1 93.2%, p2 96.8%, p3 97.7%, p4 98.2%, p5 92.9%.

## 5b. Invarianza mano izquierda / derecha

Nadie grabo con la otra mano, asi que se simula: cada muestra de test se refleja horizontalmente (la misma pose hecha con la mano opuesta) y se intercambia la etiqueta Left/Right de MediaPipe. Una caida grande significa que el modelo depende de con que mano se haga el gesto. Configuracion de este experimento: espejo=False, aumentacion con volteo=False.

| modelo | normalizacion | accuracy | accuracy_espejado | caida_pp |
|---|---|---|---|---|
| mlp | muneca_escala_rot | 96.1 | 96.2 | -0.1 |
| cnn_baseline | muneca_escala_rot | 95.8 | 95.9 | -0.1 |
| svm | muneca_escala_rot | 94.6 | 95.0 | -0.4 |
| logreg | ninguna | 90.8 | 90.8 | -0.0 |

## 6. Tabla completa

| protocolo | normalizacion | modelo | accuracy | accuracy_espejado | dispersion | accuracy_min | f1_macro | balanced_accuracy | ic95_repo | n_pliegues | n_semillas | n_test | epocas | tiempo_entrenamiento_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lopo | ninguna | cnn_baseline | 91.8 | 91.9 | 5.9 | 82.2 | 91.5 | 91.7 | 1.0 | 5 | 2 | 2931 | 33 | 146.7 |
| lopo | ninguna | mlp | 92.2 | 91.2 | 5.4 | 85.8 | 92.0 | 92.1 | 1.0 | 5 | 2 | 2931 | 66 | 263.1 |
| lopo | ninguna | svm | 89.0 | 87.0 | 6.7 | 81.3 | 88.7 | 88.9 | 1.1 | 5 | 2 | 2931 |  | 1.8 |
| lopo | ninguna | logreg | 90.8 | 90.8 | 3.3 | 87.0 | 90.7 | 90.7 | 1.0 | 5 | 2 | 2931 |  | 0.3 |
| lopo | muneca_escala_rot | cnn_baseline | 95.8 | 95.9 | 2.5 | 92.9 | 95.7 | 95.7 | 0.7 | 5 | 2 | 2931 | 26 | 109.8 |
| lopo | muneca_escala_rot | mlp | 96.1 | 96.2 | 2.4 | 93.2 | 96.1 | 96.1 | 0.7 | 5 | 2 | 2931 | 30 | 110.1 |
| lopo | muneca_escala_rot | svm | 94.6 | 95.0 | 2.6 | 91.8 | 94.6 | 94.6 | 0.8 | 5 | 2 | 2931 |  | 1.3 |
| lopo | muneca_escala_rot | logreg | 88.8 | 88.3 | 4.8 | 82.1 | 88.4 | 88.5 | 1.1 | 5 | 2 | 2931 |  | 0.3 |

Cifras de accuracy en %; dispersion y IC en puntos porcentuales. Tablas en `tablas/`.

## 7. Figuras

- [`normalizaciones_lopo`](figuras/normalizaciones_lopo.png) (tambien en PDF)
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
