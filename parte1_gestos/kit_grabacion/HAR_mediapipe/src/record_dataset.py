from pathlib import Path
from datetime import datetime
import argparse
import json
import platform
import re
import sys
import os
import cv2
import time
import numpy as np
import mediapipe as mp

# Set the project directory
# ---------------------------------------------------------------------------
# [PARCHE WINDOWS] Cabecera reescrita. El original:
#   - construia sys.path desde os.getcwd(), asi que el script SOLO funcionaba
#     lanzado desde la raiz del proyecto (contradiciendo la presentacion, que
#     dice ejecutarlo desde HAR_mediapipe/);
#   - imprimia emojis con print(), y la consola de Windows usa cp1252:
#     UnicodeEncodeError antes de capturar un solo fotograma;
#   - envolvia el import de landmarksLib en try/except ModuleNotFoundError, que
#     enmascaraba el fallo real (en Windows: "No module named 'termios'") y
#     hacia que el error saltase mucho mas tarde y en otro sitio.
# Ahora las rutas se derivan de __file__ y el script funciona desde cualquier CWD.
# ---------------------------------------------------------------------------
PROJECT_DIR = Path(__file__).resolve().parent.parent      # .../HAR_mediapipe
ROOT_DIR = PROJECT_DIR.parent                             # raiz del proyecto
path_har = str(PROJECT_DIR / 'src')
path_common = str(ROOT_DIR / 'common')

for p in [path_har, path_common]:
    if p not in sys.path:
        sys.path.insert(0, p)
    if not os.path.exists(p):
        raise RuntimeError('[ERROR] la ruta no existe: %s' % p)
    print('[OK] ruta anadida: %s' % p)

import landmarksLib   # sin try/except: si falla, queremos ver el traceback real

ON_RASPBERRY_PI = False
ON_SENSE_HAT = False
 
from cameras import CVCamera, PICamera, CameraConfig
from config import Config
from config import ConfigMediapipeDetector, RecordingSetup
from gui import Colors, WindowMessage
from landmarksLib import draw_landmarks_on_image

if ON_RASPBERRY_PI:
    cam_config = CameraConfig(FPS=30, resolution='large')
    
    if ON_SENSE_HAT:
        from sense_hat import SenseHat
else:
    cam_config = CameraConfig(FPS=30, resolution='highres')

# Instantiate the configuration
window_title = "Hand gestures recorder"
colors = Colors()

# =====================  CONFIGURACION DE LA GRABACION  =====================
# Clases en UNA SOLA PALABRA: landmarksLib.GetLandmarksFromImages saca el numero
# de frame con file.split("_")[1], asi que un guion bajo en el nombre de clase
# rompe el parseo. Se dejan en ORDEN ALFABETICO, que es el que exige la demo.
CLASSES = ['ok', 'paper', 'rock', 'rockandroll', 'scissors', 'thumbsup']

NUM_IMAGES_PER_CLASS = 100   # minimo exigido por el enunciado
TRAINING_PERCENTAGE = 70     # 70 train / 30 test dentro de cada clase
TEST_RUN_IMAGES = 5          # imagenes por clase en una toma de --prueba
KIT_VERSION = '2'

# [CAMBIO v2] El participante ya NO se escribe en este fichero: se pasa por
# linea de comandos (grabar_dataset.bat lo pregunta al arrancar). Cada ejecucion
# crea una carpeta NUEVA con fecha y hora:
#     data/gestos_<participante>_<AAAAMMDD-HHMMSS>/
# de modo que dos tomas no pueden pisarse nunca: ni aunque dos personas usen el
# mismo identificador, ni aunque alguien repita su toma. La carpeta se crea con
# exist_ok=False y ademas se comprueba fichero a fichero antes de escribir.
# 'config' se construye en main() a partir de los argumentos.
DATA_DIR = PROJECT_DIR / 'data'
config = None
# ===========================================================================

# En MediaPipe, la diferencia principal entre hand_world_landmarks y hand_landmarks radica en el sistema de coordenadas que utilizan para representar los puntos clave de las manos detectadas:

# - hand_landmarks:
# Proporciona las coordenadas de los puntos clave de la mano en un espacio de coordenadas normalizado, donde los valores X e Y se encuentran en el rango [0.0, 1.0].
# Este espacio de coordenadas está relativo a la imagen de entrada. Es decir, las coordenadas están normalizadas con respecto a las dimensiones de la imagen.
# No proporciona información sobre la profundidad (coordenada Z) en un espacio 3D real.
# Es útil para aplicaciones donde solo se necesita la posición relativa de los puntos clave en la imagen 2D.

# - hand_world_landmarks:
# Proporciona las coordenadas de los puntos clave de la mano en un espacio de coordenadas 3D del mundo real.
# Las coordenadas X, Y y Z se expresan en metros, con el origen ubicado aproximadamente en la raíz de la mano.
# Esto permite obtener información sobre la posición y orientación 3D de la mano en el espacio.
# Es esencial para aplicaciones que requieren un seguimiento preciso de la mano en 3D, como la realidad virtual, la realidad aumentada o el control de gestos 3D.
# En resumen:

# hand_landmarks son para coordenadas 2D relativas a la imagen.
# hand_world_landmarks son para coordenadas 3D en el mundo real.
# Esta diferencia es muy importante dependiendo de la aplicación que se le quiera dar a la detección de manos. 
# Si unicamente se quiere detectar movimientos relativos dentro de una imagen, con hand_landmarks es suficiente, 
# pero si se quiere trabajar con el movimiento de las manos en un espacio 3D, es necesario utilizar hand_world_landmarks.

def DisplayPreviewScreen(cam, detector, messages=None):
    while True: #Empieza a mostrar la imagen por pantalla pra que le usuario se prepare. Cuando se presiona la tecla s el sistema compienza a grabar.
        image = cam.read_frame()
        
        if image is None:
            # Depending the setup, the camera might need approval to activate, so wait until we start receiving images.
            print("Waiting for camera input")
            continue

        if config.use_landmarks:
            # Convert the image to RGB for Mediapipe
            if ON_RASPBERRY_PI:
                image_rgb = image  # Assuming the image is already in RGB format
            else:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Process the image and get hand landmarks
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
            detection_result = detector.detect(mp_image)

            if detection_result.hand_landmarks:
                #image_rgb, landmark_values = get_XYZ(results, image_rgb)
                image, landmark_values = draw_landmarks_on_image(image, detection_result)
                
        #image = cv2.flip(image,+1) #displays image in mirror format
        
        messages.ShowWindowMessages(image)
        
        cv2.imshow(window_title, image)
        
        key = cv2.waitKey(int(1 / cam_config.FPS * 1000)) & 0xFF
        
        if key == ord("s"):
            break
        elif key ==  ord('q'):
            exit()

def StartRecordingImages(cam, detector, num_images_to_record, messages=None):
    # num of images recorded counter
    n_recorded = 0
    recorded_images = []
    recording_frame = True
    
    #cam.start()
    
    started = time.time()
    last_save = started
    
    while True:
        # Read image from camera
        image = cam.read_frame()
        if image is None:
            # Depending the setup, the camera might need approval to activate, so wait until we start receiving images.
            print("Waiting for camera input")
            continue
        
        #image_rgb=cv2.flip(image_rgb,+1) #displays image in mirror format
                
        now = time.time()
        
        # We save only one image every second
        if now - last_save > 1: 
            image_rgb_nparray = np.ascontiguousarray(image, dtype=np.uint8)
            saved_image = np.copy(image_rgb_nparray)
            
            recorded_images.append(saved_image)
            last_save = now
            
            # We update the count of recorded images
            n_recorded+=1
        
        if now - last_save > 0.5:
            # [PARCHE] El original leia image_rgb.shape y dibujaba sobre image_rgb:
            #   (a) image_rgb todavia no existe en las primeras iteraciones
            #       (UnboundLocalError si use_landmarks=False), y
            #   (b) image_rgb se reasigna unas lineas mas abajo con cvtColor, y
            #       ademas nunca es el buffer que se muestra por pantalla, asi que
            #       el rectangulo rojo no llegaba a verse nunca.
            height, width, _ = image.shape
            bounding_rect = [(10, 10), (width - 20, height - 20)]
            cv2.rectangle(image, bounding_rect[0], bounding_rect[1], colors.color['red'], 2)
       
        if config.use_landmarks:
            # Convert the image to RGB for Mediapipe
            if ON_RASPBERRY_PI:
                image_rgb = image  # Assuming the image is already in RGB format
            else:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Process the image and get hand landmarks
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
            detection_result = detector.detect(mp_image)

            if detection_result.hand_landmarks:
                image, landmark_values = draw_landmarks_on_image(image, detection_result)
        
        # [PARCHE] era str(n_recorded + 1): mostraba 1/100 antes de guardar nada
        messages.msg[1]['text'] = "Stored images: " + str(n_recorded) + "/" + str(num_images_to_record)
        messages.ShowWindowMessages(image)

        cv2.imshow(window_title, image)

        if n_recorded>=num_images_to_record:
            time.sleep(1)
            break

        #key = cv2.waitKey(1) & 0xFF
        key = cv2.waitKey(int(1 / cam_config.FPS * 1000)) & 0xFF

        # if the `q` key was pressed, break from the loop
        if key == ord("q"):
            break

    return recorded_images 

def SaveRecordedImagesToDisk(recorded_images, class_to_save, num_samples_per_class):
    """Reparte las imagenes grabadas entre train/ y test/.

    [PARCHES] respecto al original:
      1. Si el usuario pulsa 'q' a mitad, recorded_images es mas corta que
         num_samples_per_class y el original petaba con IndexError DESPUES de
         haber escrito parte de las imagenes, dejando el dataset a medias.
      2. cv2.imwrite devuelve False en vez de lanzar excepcion cuando la carpeta
         destino no existe o la ruta es invalida; el original ignoraba el valor
         de retorno e imprimia "Recorded ..." igualmente, de modo que se podia
         perder una sesion entera de grabacion sin un solo mensaje de error.

    OJO (limitacion de diseno, no un bug): el reparto es TEMPORAL. Las primeras
    imagenes de la toma van a train y las ultimas a test. Como se captura 1 img/s
    de una unica toma continua, train y test quedan muy correlacionados y el
    accuracy de test sale optimista. Por eso ademas grabamos por participante.
    """
    n = len(recorded_images)
    n_train = min(num_samples_per_class['train'], n)
    n_test = min(num_samples_per_class['test'], max(0, n - n_train))

    if n < num_samples_per_class['total']:
        print('[AVISO] la clase %s se interrumpio: %d imagenes de %d. '
              'Se guardan %d en train y %d en test.'
              % (class_to_save, n, num_samples_per_class['total'], n_train, n_test))

    written = 0
    for subset, ini, end in (('train', 0, n_train), ('test', n_train, n_train + n_test)):
        for i in range(ini, end):
            name = class_to_save + '_' + f'{i+1:05d}' + '.jpg'
            filename = os.path.join(config.dataset_dir, subset, class_to_save, name)
            if os.path.exists(filename):
                # [CAMBIO v2] segunda red de seguridad contra sobreescrituras
                raise FileExistsError('no se sobreescribe %s' % filename)
            # [CAMBIO v2] cv2.imwrite devuelve False con rutas que llevan tildes
            # o enes en Windows (p. ej. C:\Users\José). Se codifica el
            # JPG en memoria y lo escribe numpy, que si soporta esas rutas.
            ok, buffer = cv2.imencode('.jpg', recorded_images[i])
            if not ok:
                raise IOError('no se pudo codificar la imagen %s' % filename)
            buffer.tofile(filename)
            if not os.path.exists(filename):
                raise IOError('no se pudo escribir %s' % filename)
            written += 1
            print('Recorded ', filename)
    print('[%s] %d imagenes guardadas (%d train / %d test)' % (class_to_save, written, n_train, n_test))


PARTICIPANT_RE = re.compile(r'^[a-z0-9]{1,20}$')
HAND_ALIASES = {
    'i': 'izquierda', 'izq': 'izquierda', 'izquierda': 'izquierda', 'l': 'izquierda', 'left': 'izquierda',
    'd': 'derecha', 'der': 'derecha', 'derecha': 'derecha', 'r': 'derecha', 'right': 'derecha',
}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description='Grabador del dataset de gestos (PIDS 26/27, Project 1)')
    parser.add_argument('--participante', required=True,
                        help='tu identificador del grupo: p1, p2, p3, p4 o p5')
    parser.add_argument('--mano', default=None,
                        help='mano con la que grabas: izquierda o derecha (opcional)')
    parser.add_argument('--prueba', action='store_true',
                        help='toma de prueba: %d imagenes por clase, se guarda en '
                             'data/_pruebas/ y NO cuenta para el dataset' % TEST_RUN_IMAGES)
    args = parser.parse_args(argv)

    participant = args.participante.strip().lower()
    if not PARTICIPANT_RE.match(participant):
        parser.error('identificador de participante no valido: %r. Usa solo letras '
                     'minusculas y numeros, sin espacios ni guiones bajos (p. ej. p3).'
                     % args.participante)

    hand = None
    if args.mano is not None and args.mano.strip():
        hand = HAND_ALIASES.get(args.mano.strip().lower())
        if hand is None:
            parser.error('mano no valida: %r. Usa izquierda o derecha.' % args.mano)

    args.participante = participant
    args.mano = hand
    return args


def build_take_config(participant, test_run=False, now=None):
    """Config de UNA toma, en una carpeta con nombre unico por fecha y hora."""
    now = now or datetime.now()
    base = DATA_DIR / '_pruebas' if test_run else DATA_DIR
    take_dir = base / ('gestos_%s_%s' % (participant, now.strftime('%Y%m%d-%H%M%S')))
    return Config(classes=CLASSES,
                  dataset_dir=str(take_dir),
                  num_images_per_class=TEST_RUN_IMAGES if test_run else NUM_IMAGES_PER_CLASS,
                  training_percentage=TRAINING_PERCENTAGE,
                  use_landmarks=True)


def create_take_folders(cfg):
    """Crea la carpeta de la toma. NUNCA reutiliza una que ya exista.

    [CAMBIO v2] Sustituye a Config.CreateDefaultDatasetFolders(), que ante una
    carpeta existente preguntaba en el terminal y, pulsando 'c' o 'y', seguia
    adelante y cv2.imwrite machacaba las imagenes anteriores sin avisar.
    """
    take_dir = Path(cfg.dataset_dir)
    take_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        take_dir.mkdir(exist_ok=False)
    except FileExistsError:
        raise SystemExit('[ERROR] La carpeta %s ya existe. No se sobreescribe nada: '
                         'espera un segundo y vuelve a lanzar la grabacion.' % take_dir)
    for subset in ('train', 'test'):
        for c in cfg.classes:
            (take_dir / subset / c).mkdir(parents=True, exist_ok=False)


def write_metadata(cfg, meta):
    """metadata.json de la toma. Escritura atomica: nunca queda a medias."""
    path = Path(cfg.dataset_dir) / 'metadata.json'
    tmp = path.with_name('metadata.json.tmp')
    tmp.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    os.replace(tmp, path)


def print_take_summary(cfg, meta):
    line = '=' * 72
    print()
    print(line)
    print(' TOMA %s' % meta['estado'].upper())
    print(line)
    print(' Participante : %s   (mano: %s)' % (meta['participante'], meta['mano'] or 'no indicada'))
    print(' Carpeta      : %s' % cfg.dataset_dir)
    for c in cfg.classes:
        n = meta['clases_grabadas'].get(c, 0)
        flag = '' if n >= cfg.num_images_per_class else '   <-- INCOMPLETA'
        print('   %-12s %3d / %d%s' % (c, n, cfg.num_images_per_class, flag))
    print(line)
    if meta['prueba']:
        print(' Era una toma de PRUEBA: no la envies. Cuando estes listo, graba la de verdad')
        print(' sin --prueba.')
    elif meta['estado'] == 'completa':
        print(' Siguiente paso: comprime ESA carpeta (clic derecho > Enviar a > Carpeta')
        print(' comprimida) y pasale el .zip a Javier. No cambies el nombre de la carpeta.')
    else:
        print(' La toma no esta completa. No la envies: vuelve a lanzar la grabacion')
        print(' (se creara otra carpeta nueva; esta no se toca) y borra esta cuando acabes.')
    print(line)


def main(argv=None):
    global config
    args = parse_args(argv)
    config = build_take_config(args.participante, test_run=args.prueba)

    num_samples_per_class = RecordingSetup(config)
    create_take_folders(config)

    meta = {
        'participante': args.participante,
        'mano': args.mano,
        'toma': Path(config.dataset_dir).name,
        'prueba': bool(args.prueba),
        'estado': 'en_curso',
        'inicio': datetime.now().isoformat(timespec='seconds'),
        'fin': None,
        'clases': list(config.classes),
        'imagenes_por_clase': config.num_images_per_class,
        'porcentaje_train': config.training_percentage,
        'clases_grabadas': {},
        'resolucion_pedida': list(cam_config.resolution),
        'resolucion_real': None,
        'kit_version': KIT_VERSION,
        'python': platform.python_version(),
        'mediapipe': getattr(mp, '__version__', 'desconocida'),
        'opencv': cv2.__version__,
    }
    write_metadata(config, meta)
    print('\n[TOMA NUEVA] %s' % config.dataset_dir)

    cam = None
    try:
        # Create the detector
        detector = ConfigMediapipeDetector()  # [PARCHE] antes 'HAR_mediapipe/models/...' relativo al CWD

        # Start camera, use CVCamera if working on a laptop and PICamera in case you are working on a Raspberry PI
        if ON_RASPBERRY_PI:
            cam = PICamera(recording_res=cam_config.resolution)
            if ON_SENSE_HAT:
                sense_hat = SenseHat()
                sense_hat.set_rotation(180)
        else:
            cam = CVCamera(recording_res=cam_config.resolution, index_cam=0)  # Use the first camera

        cam.start()
        if hasattr(cam, 'vid'):
            meta['resolucion_real'] = [int(cam.vid.get(cv2.CAP_PROP_FRAME_WIDTH)),
                                       int(cam.vid.get(cv2.CAP_PROP_FRAME_HEIGHT))]
            write_metadata(config, meta)

        # Main loop
        for c in config.classes:
            print("\nPREPARING TO RECORD CLASS:", c)

            preview_msgs = WindowMessage(
                txt1 = "Class to be recorded: " + c, pos1 = (70, 210), col1 = colors.color['green'],
                txt2 = "Get ready and press 's' to start recording", pos2 = (70, 260), col2 = colors.color['green'],
                txt3 = "or 'q' to exit.", pos3 = (70, 300), col3 = colors.color['green'])

            # Display preview screen ('q' aqui aborta la toma entera)
            DisplayPreviewScreen(cam, detector, preview_msgs)

            recording_msgs = WindowMessage(
                txt1 = "Recording in progress...", pos1 = (20, 40), col1 = colors.color['red'],
                txt2 = "Get ready and press 's' to start recording", pos2 = (20, 80), col2 = colors.color['red'],
                txt3 = "", pos3 = (20, 120), col3 = colors.color['red'])

            # Start recording images ('q' aqui corta ESTE gesto y pasa al siguiente)
            recorded_images = StartRecordingImages(cam, detector, num_samples_per_class['total'], recording_msgs)

            # Save images to disk
            SaveRecordedImagesToDisk(recorded_images, c, num_samples_per_class)
            meta['clases_grabadas'][c] = len(recorded_images)
            write_metadata(config, meta)

        complete = all(meta['clases_grabadas'].get(c, 0) >= config.num_images_per_class
                       for c in config.classes)
        meta['estado'] = 'completa' if complete else 'incompleta'
        meta['fin'] = datetime.now().isoformat(timespec='seconds')
        write_metadata(config, meta)
        print('\n[RECORDING FINISHED]\n')

        post_msgs = WindowMessage(
                txt1 = "Recording finished (%s)" % meta['estado'], pos1 = (70, 210), col1 = colors.color['blue'],
                txt2 = "You can now press 'q' to exit...", pos2 = (70, 260), col2 = colors.color['blue'],
                txt3 = "", pos3 = (70, 300), col3 = colors.color['blue'])

        # Display final message (su 'q' llama a exit(): por eso el cierre va en finally)
        DisplayPreviewScreen(cam, detector, post_msgs)

    finally:
        if meta['estado'] == 'en_curso':
            meta['estado'] = 'interrumpida'
        if meta['fin'] is None:
            meta['fin'] = datetime.now().isoformat(timespec='seconds')
        write_metadata(config, meta)
        if cam is not None:
            cam.stop()          # [PARCHE] cam.stop() ahora tambien hace destroyAllWindows()
        print_take_summary(config, meta)


if __name__ == "__main__":
    main()
