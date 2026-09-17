# Comparativa del plan de entrenamiento

Accuracy en LOPO (participante no visto), media sobre participantes y semillas, y con la mano opuesta simulada (test reflejado). Ordenado de mejor a peor.

| experimento | modelo | normalizacion | espejo | aumentar | voltear | lopo_% | desv_pp | lopo_mano_opuesta_% | semillas |
|---|---|---|---|---|---|---|---|---|---|
| volteo | mlp | muneca_escala_rot | False | 3 | True | 96.5 | 1.6 | 96.6 | 2 |
| principal | mlp | muneca_escala_rot | False | 0 | False | 96.2 | 2.0 | 96.4 | 3 |
| volteo | cnn_baseline | muneca_escala_rot | False | 3 | True | 96.2 | 2.3 | 96.2 | 2 |
| aumento | mlp | muneca_escala_rot | False | 3 | False | 96.1 | 2.4 | 96.2 | 2 |
| espejo | mlp | muneca_escala_rot | True | 0 | False | 95.9 | 2.7 | 95.9 | 3 |
| espejo | cnn_baseline | muneca_escala_rot | True | 0 | False | 95.9 | 2.3 | 95.9 | 3 |
| principal | cnn_baseline | muneca_escala_rot | False | 0 | False | 95.8 | 2.2 | 96.0 | 3 |
| aumento | cnn_baseline | muneca_escala_rot | False | 3 | False | 95.8 | 2.5 | 95.9 | 2 |
| volteo | svm | muneca_escala_rot | False | 3 | True | 95.4 | 2.4 | 95.4 | 2 |
| principal | mlp | muneca_escala | False | 0 | False | 95.2 | 1.6 | 94.7 | 3 |
| espejo | mlp | muneca_escala | True | 0 | False | 94.8 | 2.0 | 94.8 | 3 |
| principal | cnn_baseline | muneca_escala | False | 0 | False | 94.8 | 1.5 | 94.9 | 3 |
| principal | cnn_baseline | muneca | False | 0 | False | 94.8 | 1.8 | 94.1 | 3 |
| principal | svm | muneca_escala_rot | False | 0 | False | 94.7 | 2.9 | 94.8 | 3 |
| espejo | svm | muneca_escala_rot | True | 0 | False | 94.7 | 2.5 | 94.8 | 3 |
| espejo | svm | muneca_escala | True | 0 | False | 94.6 | 1.9 | 94.6 | 3 |
| aumento | svm | muneca_escala_rot | False | 3 | False | 94.6 | 2.6 | 95.0 | 2 |
| espejo | cnn_baseline | muneca_escala | True | 0 | False | 94.6 | 1.3 | 94.6 | 3 |
| principal | mlp | muneca | False | 0 | False | 94.4 | 2.9 | 94.4 | 3 |
| principal | svm | muneca_escala | False | 0 | False | 94.0 | 2.2 | 94.2 | 3 |
| principal | random_forest | muneca_escala_rot | False | 0 | False | 93.4 | 4.5 | 94.4 | 3 |
| espejo | logreg | muneca_escala_rot | True | 0 | False | 92.7 | 3.2 | 92.7 | 1 |
| espejo | logreg | muneca_escala | True | 0 | False | 92.3 | 5.0 | 92.3 | 1 |
| aumento | mlp | ninguna | False | 3 | False | 92.2 | 5.4 | 91.2 | 2 |
| principal | logreg | muneca_escala | False | 0 | False | 92.2 | 3.0 | 91.5 | 1 |
| aumento | cnn_baseline | ninguna | False | 3 | False | 91.8 | 5.9 | 91.9 | 2 |
| principal | logreg | muneca | False | 0 | False | 91.1 | 3.0 | 91.2 | 1 |
| principal | knn | muneca_escala_rot | False | 0 | False | 91.0 | 5.0 | 90.3 | 1 |
| principal | cnn_baseline | ninguna | False | 0 | False | 90.9 | 5.2 | 91.3 | 3 |
| aumento | logreg | ninguna | False | 3 | False | 90.8 | 3.3 | 90.8 | 2 |
| principal | random_forest | muneca_escala | False | 0 | False | 90.6 | 3.9 | 90.8 | 3 |
| principal | logreg | ninguna | False | 0 | False | 90.4 | 4.0 | 90.1 | 1 |
| principal | mlp | ninguna | False | 0 | False | 90.3 | 5.6 | 90.1 | 3 |
| principal | svm | muneca | False | 0 | False | 90.2 | 4.9 | 89.5 | 3 |
| volteo | logreg | muneca_escala_rot | False | 3 | True | 89.3 | 4.1 | 89.6 | 2 |
| aumento | svm | ninguna | False | 3 | False | 89.0 | 6.7 | 87.0 | 2 |
| aumento | logreg | muneca_escala_rot | False | 3 | False | 88.8 | 4.8 | 88.3 | 2 |
| principal | logreg | muneca_escala_rot | False | 0 | False | 88.5 | 5.0 | 88.8 | 1 |
| principal | knn | muneca_escala | False | 0 | False | 88.0 | 5.0 | 88.8 | 1 |
| principal | svm | ninguna | False | 0 | False | 87.1 | 7.7 | 84.8 | 3 |
| principal | random_forest | muneca | False | 0 | False | 84.0 | 7.4 | 82.5 | 3 |
| principal | random_forest | ninguna | False | 0 | False | 82.6 | 9.2 | 82.4 | 3 |
| principal | knn | muneca | False | 0 | False | 76.7 | 10.5 | 75.3 | 1 |
| principal | knn | ninguna | False | 0 | False | 68.0 | 12.1 | 66.2 | 1 |

Informes completos de cada experimento:

- `principal`: C:\Users\Javier\PIDS_HandPose\entrenamiento\resultados\plan_20260917-0042_principal\informe.md
- `espejo`: C:\Users\Javier\PIDS_HandPose\entrenamiento\resultados\plan_20260917-0042_espejo\informe.md
- `aumento`: C:\Users\Javier\PIDS_HandPose\entrenamiento\resultados\plan_20260917-0042_aumento\informe.md
- `volteo`: C:\Users\Javier\PIDS_HandPose\entrenamiento\resultados\plan_20260917-0042_volteo\informe.md
