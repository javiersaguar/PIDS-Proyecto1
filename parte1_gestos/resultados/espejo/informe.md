# Informe del experimento `plan_20260917-0042_espejo`

Generado a partir de `plan_20260917-0042_espejo`. Entrenado el 2026-09-17T01:04:43 con Keras 3.15.1 (backend torch, dispositivo: cuda: NVIDIA GeForce RTX 5070 Laptop GPU, cpu), scikit-learn 1.9.0 y MediaPipe 0.10.35 (32 CPUs logicas).

**Configuracion:** modelos cnn_baseline, mlp, svm, logreg; normalizaciones muneca_escala, muneca_escala_rot; protocolos lopo; semillas [0, 1, 2]; espejo=True; aumentacion=0 copias; hasta 200 epocas, paciencia 20, batch 32.

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

Protocolo de referencia: **LOPO** (el mas honesto de los ejecutados). Mejor configuracion: **`mlp` con normalizacion `muneca_escala_rot`**: accuracy **95.9%** (desviacion 2.7 pp), F1 macro 95.9%, balanced accuracy 95.9%. IC95 del repo: +/- 0.7 pp (optimista: supone fotogramas independientes).

Accuracy (%) en LOPO, media +/- desviacion:

| modelo | muneca_escala | muneca_escala_rot |
|---|---|---|
| cnn_baseline | 94.6 +/- 1.3 | 95.9 +/- 2.3 |
| mlp | 94.8 +/- 2.0 | 95.9 +/- 2.7 |
| svm | 94.6 +/- 1.9 | 94.7 +/- 2.5 |
| logreg | 92.3 +/- 5.0 | 92.7 +/- 3.2 |

## 4. Analisis por gesto y errores

### `mlp`, normalizacion `muneca_escala_rot` (LOPO)

| clase | precision | recall | f1 | soporte |
|---|---|---|---|---|
| ok | 95.4 | 95.5 | 95.4 | 1455 |
| paper | 94.8 | 96.1 | 95.4 | 1482 |
| rock | 93.2 | 95.8 | 94.5 | 1425 |
| rockandroll | 98.9 | 97.0 | 98.0 | 1482 |
| scissors | 97.2 | 94.9 | 96.0 | 1470 |
| thumbsup | 96.1 | 96.3 | 96.2 | 1479 |

Confusiones mas frecuentes:

| real | predicha | n | pct_de_la_clase_real |
|---|---|---|---|
| thumbsup | rock | 50 | 3.4% |
| paper | ok | 44 | 3.0% |
| rock | thumbsup | 29 | 2.0% |
| ok | paper | 29 | 2.0% |
| scissors | paper | 27 | 1.8% |
| ok | rock | 17 | 1.2% |
| scissors | thumbsup | 15 | 1.0% |
| rockandroll | rock | 15 | 1.0% |
| scissors | rock | 14 | 1.0% |
| rock | paper | 13 | 0.9% |

Accuracy con cada participante no visto: p1 92.2%, p2 97.3%, p3 97.7%, p4 98.3%, p5 94.0%.

### `cnn_baseline`, normalizacion `muneca_escala_rot` (LOPO)

| clase | precision | recall | f1 | soporte |
|---|---|---|---|---|
| ok | 96.6 | 95.4 | 96.0 | 1455 |
| paper | 95.1 | 96.6 | 95.8 | 1482 |
| rock | 93.4 | 95.4 | 94.4 | 1425 |
| rockandroll | 98.4 | 97.3 | 97.8 | 1482 |
| scissors | 95.6 | 95.0 | 95.3 | 1470 |
| thumbsup | 96.5 | 95.9 | 96.2 | 1479 |

Confusiones mas frecuentes:

| real | predicha | n | pct_de_la_clase_real |
|---|---|---|---|
| thumbsup | rock | 48 | 3.2% |
| rock | thumbsup | 34 | 2.4% |
| ok | paper | 29 | 2.0% |
| paper | scissors | 28 | 1.9% |
| scissors | paper | 25 | 1.7% |
| paper | ok | 19 | 1.3% |
| scissors | rock | 16 | 1.1% |
| ok | rock | 15 | 1.0% |
| scissors | ok | 15 | 1.0% |
| ok | scissors | 14 | 1.0% |

Accuracy con cada participante no visto: p1 92.9%, p2 96.6%, p3 97.7%, p4 98.2%, p5 94.0%.

## 5b. Invarianza mano izquierda / derecha

Nadie grabo con la otra mano, asi que se simula: cada muestra de test se refleja horizontalmente (la misma pose hecha con la mano opuesta) y se intercambia la etiqueta Left/Right de MediaPipe. Una caida grande significa que el modelo depende de con que mano se haga el gesto. Configuracion de este experimento: espejo=True, aumentacion con volteo=False.

| modelo | normalizacion | accuracy | accuracy_espejado | caida_pp |
|---|---|---|---|---|
| mlp | muneca_escala_rot | 95.9 | 95.9 | +0.0 |
| cnn_baseline | muneca_escala_rot | 95.9 | 95.9 | +0.0 |
| svm | muneca_escala_rot | 94.7 | 94.8 | -0.1 |
| logreg | muneca_escala_rot | 92.7 | 92.7 | -0.1 |

## 6. Tabla completa

| protocolo | normalizacion | modelo | accuracy | accuracy_espejado | dispersion | accuracy_min | f1_macro | balanced_accuracy | ic95_repo | n_pliegues | n_semillas | n_test | epocas | tiempo_entrenamiento_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lopo | muneca_escala | cnn_baseline | 94.6 | 94.6 | 1.3 | 92.3 | 94.5 | 94.5 | 0.8 | 5 | 3 | 2931 | 30 | 36.7 |
| lopo | muneca_escala | mlp | 94.8 | 94.8 | 2.0 | 92.4 | 94.7 | 94.8 | 0.8 | 5 | 3 | 2931 | 49 | 52.6 |
| lopo | muneca_escala | svm | 94.6 | 94.6 | 1.9 | 91.7 | 94.6 | 94.6 | 0.8 | 5 | 3 | 2931 |  | 0.4 |
| lopo | muneca_escala | logreg | 92.3 | 92.3 | 5.0 | 85.1 | 92.2 | 92.2 | 1.0 | 5 | 1 | 2931 |  | 0.2 |
| lopo | muneca_escala_rot | cnn_baseline | 95.9 | 95.9 | 2.3 | 92.9 | 95.9 | 95.9 | 0.7 | 5 | 3 | 2931 | 32 | 37.1 |
| lopo | muneca_escala_rot | mlp | 95.9 | 95.9 | 2.7 | 92.2 | 95.9 | 95.9 | 0.7 | 5 | 3 | 2931 | 49 | 51.0 |
| lopo | muneca_escala_rot | svm | 94.7 | 94.8 | 2.5 | 92.4 | 94.7 | 94.6 | 0.8 | 5 | 3 | 2931 |  | 0.2 |
| lopo | muneca_escala_rot | logreg | 92.7 | 92.7 | 3.2 | 88.1 | 92.6 | 92.6 | 0.9 | 5 | 1 | 2931 |  | 0.1 |

Cifras de accuracy en %; dispersion y IC en puntos porcentuales. Tablas en `tablas/`.

## 7. Figuras

- [`normalizaciones_lopo`](figuras/normalizaciones_lopo.png) (tambien en PDF)
- [`confusion_mlp_muneca_escala_rot_lopo`](figuras/confusion_mlp_muneca_escala_rot_lopo.png) (tambien en PDF)
- [`confusion_cnn_baseline_muneca_escala_rot_lopo`](figuras/confusion_cnn_baseline_muneca_escala_rot_lopo.png) (tambien en PDF)
- [`participantes_mlp_muneca_escala_rot`](figuras/participantes_mlp_muneca_escala_rot.png) (tambien en PDF)
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
