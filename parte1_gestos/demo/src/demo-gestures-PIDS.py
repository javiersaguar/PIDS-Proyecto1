"""Demo en tiempo real de reconocimiento de gestos (pasos 12-13 de la presentacion).

Copia de demo-custom-dataset.py adaptada al proyecto:
  - ON_RASPBERRY_PI = False: webcam del portatil.
  - MODEL_PATH -> el modelo que guarda el notebook (gestos_pids_CNN1.keras).
  - classes -> nuestros 6 gestos EN ORDEN ALFABETICO y 'None' al final, porque el notebook entreno
    con la clase NO_GESTURE (7 salidas). El demo original declaraba 6 nombres para un modelo de 7.
  - Ademas muestra el comando del tanque (Project 2) asociado a cada gesto.

Arreglos respecto al original (marcados [PIDS]):
  - rutas desde __file__ (el original buscaba 'FER_mediapipe/src' y dependia del directorio de trabajo);
  - Keras con backend PyTorch: model(...) devuelve un tensor (quiza en la GPU) y np.argmax no lo acepta;
  - num_frames=+1 -> num_frames += 1;
  - se comprueba al arrancar que la lista de clases tiene tantos nombres como salidas el modelo.

Uso (con el entorno del proyecto, que tiene Keras):
    ..\\..\\..\\.venv\\Scripts\\python.exe demo-gestures-PIDS.py
    ... demo-gestures-PIDS.py --modelo C:/.../entrenamiento/modelos/<exportado>   (modelo del pipeline)
    ... demo-gestures-PIDS.py --imagenes <carpeta con subcarpetas por gesto> --sin-ventana   (prueba sin camara)
Tecla q: salir.
"""
from pathlib import Path
import argparse
import os
import sys
import time

import cv2
import numpy as np

# [PIDS] rutas desde este fichero
PROJECT_DIR = Path(__file__).resolve().parent.parent          # .../parte1_gestos/demo
PARTE1_DIR = PROJECT_DIR.parent                               # .../parte1_gestos
for p in (PROJECT_DIR / 'src', PROJECT_DIR / 'common', PARTE1_DIR / 'entrenamiento'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
os.environ.setdefault('KERAS_BACKEND', 'torch')
os.environ.setdefault('GLOG_minloglevel', '2')

import mediapipe as mp  # noqa: E402
import keras  # noqa: E402

ON_RASPBERRY_PI = False

from cameras import CVCamera, PICamera, CameraConfig  # noqa: E402
from config import Config, ConfigMediapipeDetector  # noqa: E402
from gui import Colors, WindowMessage  # noqa: E402
from landmarksLib import draw_landmarks_on_image  # noqa: E402

# El modelo del notebook se versiona en parte1_gestos/modelos/; si se acaba de entrenar, también vale
# la copia que deja el notebook junto a la demo.
_CANDIDATOS_MODELO = [PROJECT_DIR / "models" / "gestos_pids_CNN1.keras",
                      PARTE1_DIR / "modelos" / "gestos_pids_CNN1.keras"]
MODEL_PATH = next((c for c in _CANDIDATOS_MODELO if c.is_file()), _CANDIDATOS_MODELO[-1])

# Classes to be recognized; ATENTION: 'None' class must be the last one; the others must be specified
# in the order they were trained (alphabetical order)
classes = ['ok', 'paper', 'rock', 'rockandroll', 'scissors', 'thumbsup', 'None']

# [PIDS] comando del vehiculo tanque (Project 2) que activa cada gesto
try:
    from hgr.constantes import COMANDOS_TANQUE
except ImportError:
    COMANDOS_TANQUE = {}

window_title = "Hand gestures recognition demonstrator (PIDS)"
cam_config = CameraConfig(FPS=15, resolution='highres')
debug_HAR = False


class ModeloNotebook:
    """El modelo del notebook: landmarks crudos (1, 21, 2, 1), igual que el demo original."""

    def __init__(self, ruta, nombres):
        self.modelo = keras.models.load_model(ruta, compile=False)
        salidas = int(self.modelo.output_shape[-1])
        if salidas != len(nombres):
            raise SystemExit('[ERROR] el modelo %s tiene %d salidas y la lista classes tiene %d nombres. '
                             'Revisa classes (orden alfabetico y None al final si se entreno con NO_GESTURE).'
                             % (ruta.name, salidas, len(nombres)))
        self.clases = list(nombres)

    def predecir(self, resultado, ancho, alto):
        _, landmark_values = draw_landmarks_on_image(np.zeros((alto, ancho, 3), np.uint8), resultado)
        x = np.reshape(np.array(landmark_values, dtype=np.float32), (1, 21, 2, 1))
        # [PIDS] con backend PyTorch la salida es un tensor: se pasa a numpy antes de argmax
        p = keras.ops.convert_to_numpy(self.modelo(x, training=False))[0]
        k = int(np.argmax(p))
        return self.clases[k], float(p[k])


class ModeloPipeline:
    """Un modelo exportado por entrenamiento/exportar_modelo.py (con su normalizacion)."""

    def __init__(self, carpeta):
        from hgr.inferencia import ClasificadorGestos
        self.clf = ClasificadorGestos(carpeta)
        self.clases = self.clf.clases

    def predecir(self, resultado, ancho, alto):
        clase, conf, _ = self.clf.predecir_resultado_mediapipe(resultado, ancho, alto)
        return clase, conf


def texto_prediccion(pred, conf):
    comando = COMANDOS_TANQUE.get(pred)
    return "Gesto: %s (%0.2f)%s" % (pred, conf, ("  ->  %s" % comando) if comando else '')


def detectar(detector, image):
    image_rgb = image if ON_RASPBERRY_PI else cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb))


def demo_camara(modelo, detector, colors):
    if ON_RASPBERRY_PI:
        cam = PICamera(recording_res=cam_config.resolution)
    else:
        cam = CVCamera(recording_res=cam_config.resolution, index_cam=0)
    cam.start()
    last, num_frames, pred, conf = 0.0, 0, 'None', 1.0
    try:
        while True:
            image = cam.read_frame()
            if image is None:
                print("Waiting for camera input")
                continue
            now = time.time()
            num_frames += 1                               # [PIDS] era num_frames=+1
            alto, ancho = image.shape[:2]
            detection_result = detectar(detector, image)
            if detection_result.hand_landmarks:
                image, _ = draw_landmarks_on_image(image, detection_result)
                if now - last > 0.25:                     # como el original: una prediccion cada 0,25 s
                    pred, conf = modelo.predecir(detection_result, ancho, alto)
                    last = time.time()
                    if debug_HAR:
                        print('Prediction:', pred, 'Confidence:', conf)
            else:
                pred, conf = 'None', 1.0
            color1 = colors.color['black'] if pred == 'None' else colors.GetColorForClass(pred)
            WindowMessage(txt1=texto_prediccion(pred, conf), pos1=(10, alto - 20), col1=color1,
                          txt2="q: salir", pos2=(10, 30), col2=colors.color['white']).ShowWindowMessages(image)
            cv2.imshow(window_title, image)
            if (cv2.waitKey(int(1 / cam_config.FPS * 1000)) & 0xFF) == ord('q'):
                break
    finally:
        cam.stop()


def demo_imagenes(modelo, detector, carpeta, mostrar):
    """[PIDS] Misma logica sobre fotos guardadas (carpeta/<gesto>/*.jpg): sirve para probar sin camara."""
    carpeta = Path(carpeta)
    aciertos = total = sin_mano = 0
    for d_clase in sorted(p for p in carpeta.iterdir() if p.is_dir()):
        for f in sorted(d_clase.glob('*.jpg')):
            image = cv2.imdecode(np.fromfile(str(f), np.uint8), cv2.IMREAD_COLOR)
            alto, ancho = image.shape[:2]
            res = detectar(detector, image)
            if not res.hand_landmarks:
                sin_mano += 1
                continue
            pred, conf = modelo.predecir(res, ancho, alto)
            total += 1
            aciertos += int(pred == d_clase.name)
            if mostrar:
                image, _ = draw_landmarks_on_image(image, res)
                WindowMessage(txt1=texto_prediccion(pred, conf), pos1=(10, alto - 20),
                              col1=(0, 255, 0)).ShowWindowMessages(image)
                cv2.imshow(window_title, image)
                if (cv2.waitKey(300) & 0xFF) == ord('q'):
                    return
    print('Imagenes con mano: %d | aciertos: %d (%.1f%%) | sin mano detectada: %d'
          % (total, aciertos, 100 * aciertos / max(1, total), sin_mano))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--modelo', default=None,
                        help='carpeta de un modelo exportado por el pipeline (por defecto: el .keras del notebook)')
    parser.add_argument('--imagenes', default=None, help='probar sobre fotos en vez de con la camara')
    parser.add_argument('--sin-ventana', action='store_true', help='con --imagenes, no abrir ventana')
    args = parser.parse_args()

    print("Loading model...")
    modelo = ModeloPipeline(args.modelo) if args.modelo else ModeloNotebook(MODEL_PATH, classes)
    print("Model loaded! Clases:", modelo.clases)
    colors = Colors()
    colors.SelectRandomColorFromListForClasses(modelo.clases)
    Config(classes=modelo.clases, use_landmarks=True)
    detector = ConfigMediapipeDetector()

    if args.imagenes:
        demo_imagenes(modelo, detector, args.imagenes, mostrar=not args.sin_ventana)
    else:
        demo_camara(modelo, detector, colors)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
