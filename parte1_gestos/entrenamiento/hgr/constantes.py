"""Rutas por defecto y constantes del problema."""
from pathlib import Path

RAIZ_ENTRENAMIENTO = Path(__file__).resolve().parent.parent
RAIZ_PROYECTO = RAIZ_ENTRENAMIENTO.parent

# Donde se buscan tomas por defecto: las que se descomprimen en entrenamiento/datos/
# y las grabadas en este mismo equipo con el kit.
RAICES_DATOS_POR_DEFECTO = [
    RAIZ_ENTRENAMIENTO / 'datos',
    RAIZ_PROYECTO / 'kit-grabacion' / 'HAR_mediapipe' / 'data',
]
DIR_CACHE = RAIZ_ENTRENAMIENTO / 'cache'
DIR_RESULTADOS = RAIZ_ENTRENAMIENTO / 'resultados'
DIR_MODELOS = RAIZ_ENTRENAMIENTO / 'modelos'
MODELO_MEDIAPIPE = RAIZ_PROYECTO / 'kit-grabacion' / 'HAR_mediapipe' / 'models' / 'hand_landmarker.task'

# Topologia de MediaPipe Hands
N_LANDMARKS = 21
MUNECA = 0
MCP_CORAZON = 9          # nudillo del dedo corazon: referencia de escala y orientacion

CLASES_ESPERADAS = ['ok', 'paper', 'rock', 'rockandroll', 'scissors', 'thumbsup']
IMAGENES_POR_CLASE = 100

# La presentacion exige que los gestos cubran comandos del vehiculo tanque del Project 2
# (ejemplos: hacer foto, avanzar, retroceder, izquierda, derecha, parar, disparar).
# PROPUESTA (se cambia aqui y lo recogen el informe y la demo):
COMANDOS_TANQUE = {
    'paper': 'PARAR',            # palma abierta: el gesto universal de "alto"
    'thumbsup': 'AVANZAR',
    'rock': 'RETROCEDER',        # puno: "recoger"
    'ok': 'GIRAR',
    'rockandroll': 'DISPARAR',
    'scissors': 'HACER FOTO',    # la "V" tipica de las fotos
}

NORMALIZACIONES = ['ninguna', 'muneca', 'muneca_escala', 'muneca_escala_rot']
PROTOCOLOS = ['aleatorio', 'temporal', 'lopo']
# Por defecto no se usa 'aleatorio': la presentacion pide "una particion adecuada", la del grabador
# de la asignatura es 'temporal' y la honesta es 'lopo'. El optimismo de una particion que mezcla
# fotogramas casi identicos ya se ve comparando temporal con lopo. Sigue disponible.
PROTOCOLOS_POR_DEFECTO = ['temporal', 'lopo']
# Orden de "honestidad" de la estimacion: se usa para elegir el protocolo de referencia
PROTOCOLO_MAS_HONESTO = ['lopo', 'temporal', 'aleatorio']

COLS_X = ['x%d' % i for i in range(N_LANDMARKS)]
COLS_Y = ['y%d' % i for i in range(N_LANDMARKS)]
COLS_Z = ['z%d' % i for i in range(N_LANDMARKS)]
COLS_LANDMARKS = [c + str(i) for i in range(N_LANDMARKS) for c in ('x', 'y', 'z')]
COLS_WORLD = ['w' + c + str(i) for i in range(N_LANDMARKS) for c in ('x', 'y', 'z')]
COLS_META = ['toma', 'participante', 'mano_declarada', 'clase', 'subset', 'frame', 'ruta_relativa', 'carpeta_toma']
COLS_RESULTADO = ['ancho', 'alto', 'brillo', 'detectada', 'handedness', 'handedness_score', 'error']
DTYPES_TEXTO = {c: str for c in ('toma', 'participante', 'mano_declarada', 'clase', 'subset',
                                 'ruta_relativa', 'carpeta_toma', 'handedness', 'error')}
