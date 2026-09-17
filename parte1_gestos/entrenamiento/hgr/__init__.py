"""hgr - Hand Gesture Recognition. Pipeline local y reproducible (PIDS 26/27, Project 1).

Flujo:  tomas (JPG)  ->  extraccion (landmarks MediaPipe, cacheados)
        ->  features (normalizacion, espejo, aumentacion)
        ->  protocolos (aleatorio / temporal / lopo)  ->  modelos
        ->  metricas, rendimiento, graficas, informe  ->  exportacion para la demo
"""

__version__ = '1.0.0'
