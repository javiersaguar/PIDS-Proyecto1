# Viajes para la captura en directo

Un CSV comprimido por día (`AAAA-MM-DD.csv.gz`) con los viajes reales de un mes de 2020, ordenados por
recogida. Los reproduce la captura en directo (botón «Capturar datos» del grafo del portal o `make capturar`).
No se suben al repositorio: se generan con

```bash
make captura-preparar            # diciembre de 2020 (MES=2020-03 para otro): descarga y parte el mes
```

El portal los lee de aquí (volumen de solo lectura). Detalle en `parte2_plataforma/simulador/directo.py`.
