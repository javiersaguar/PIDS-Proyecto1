# Parte 1 · Reconocimiento de gestos

Reconocimiento de 6 gestos de mano (`ok`, `paper`, `rock`, `rockandroll`, `scissors`, `thumbsup`)
con MediaPipe (21 puntos por mano) y clasificadores entrenados sobre esos puntos.

La parte 1 se ejecuta en **Windows** (la webcam no funciona bien dentro de WSL). Los resultados
principales, evaluando con una persona no vista (LOPO):

| Modelo | Accuracy LOPO |
|---|---|
| CNN de la presentación, sin normalizar | 90,9 % |
| CNN, normalización muñeca + escala + rotación | 95,8 % |
| MLP, normalización completa + aumentación con volteo | **96,5 %** |

Pendiente: incorporar aquí el código de entrenamiento, el notebook y la demo (sin datos ni modelos
pesados, que están excluidos en `.gitignore`).

La conexión con las partes 2 y 3 está en [`../integracion/`](../integracion/).
