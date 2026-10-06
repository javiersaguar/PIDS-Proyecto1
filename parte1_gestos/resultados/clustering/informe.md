# Clustering del dataset de gestos

2931 manos detectadas (de 3000 imágenes), 42 valores por mano (x, y de los 21 puntos). Agrupadas **sin etiquetas**
con k-means (k = 6, como gestos; k = 5, como personas) y Ward (k = 6), y comparadas después con las etiquetas.

| Representación | ARI gesto (k-means) | Pureza gesto | ARI gesto (Ward) | ARI persona (k = 5) | NMI mano izq./der. | Silueta por gesto | Silueta por persona |
|---|---|---|---|---|---|---|---|
| sin normalizar | 0,05 | 27,8 % | 0,07 | 0,05 | 0,12 | -0,00 | -0,03 |
| normalizada | 0,22 | 37,6 % | 0,24 | 0,01 | 0,09 | 0,10 | -0,04 |
| normalizada + espejo | 0,36 | 49,9 % | 0,43 | 0,03 | 0,00 | 0,18 | -0,07 |

ARI: 0 = grupos al azar respecto a esa etiqueta, 1 = idénticos. Pureza: acierto del mejor emparejamiento uno a
uno entre grupos y gestos. Silueta por etiqueta: cuánto se separan los gestos (o las personas) tal cual vienen
etiquetados, de −1 a 1.

## Según el número de grupos k (k-means)

Pureza por mayoría: % de manos cuyo grupo tiene su mismo gesto como mayoritario (un gesto puede ocupar varios
grupos). Silueta: separación de los grupos, de −1 a 1.

| k | pureza sin normalizar | pureza normalizada | pureza normalizada + espejo | silueta sin normalizar | silueta normalizada | silueta normalizada + espejo |
|---|---|---|---|---|---|---|
| 2 | 18,2 % | 17,2 % | 29,0 % | 0,35 | 0,36 | 0,39 |
| 3 | 26,9 % | 25,4 % | 41,0 % | 0,32 | 0,29 | 0,34 |
| 4 | 28,2 % | 25,5 % | 41,0 % | 0,27 | 0,29 | 0,35 |
| 5 | 30,2 % | 33,2 % | 47,2 % | 0,26 | 0,27 | 0,33 |
| 6 | 29,4 % | 38,3 % | 50,1 % | 0,22 | 0,28 | 0,33 |
| 7 | 30,9 % | 39,6 % | 66,3 % | 0,21 | 0,29 | 0,39 |
| 8 | 30,6 % | 48,3 % | 60,9 % | 0,22 | 0,33 | 0,39 |
| 9 | 31,5 % | 54,6 % | 64,3 % | 0,21 | 0,33 | 0,40 |
| 10 | 32,4 % | 62,7 % | 68,6 % | 0,21 | 0,35 | 0,41 |
| 11 | 32,5 % | 67,2 % | 82,2 % | 0,21 | 0,36 | 0,37 |
| 12 | 32,5 % | 66,2 % | 83,2 % | 0,21 | 0,36 | 0,36 |
| 13 | 33,3 % | 65,9 % | 86,3 % | 0,20 | 0,37 | 0,38 |
| 14 | 35,1 % | 67,5 % | 85,4 % | 0,19 | 0,36 | 0,37 |
| 15 | 36,8 % | 75,0 % | 89,4 % | 0,19 | 0,35 | 0,37 |
| 16 | 36,2 % | 82,1 % | 89,6 % | 0,19 | 0,33 | 0,38 |
| 17 | 36,6 % | 75,3 % | 90,5 % | 0,19 | 0,36 | 0,38 |
| 18 | 37,2 % | 75,2 % | 89,1 % | 0,18 | 0,35 | 0,36 |
| 19 | 40,5 % | 83,0 % | 91,0 % | 0,19 | 0,34 | 0,38 |
| 20 | 38,8 % | 84,5 % | 90,8 % | 0,19 | 0,34 | 0,35 |
