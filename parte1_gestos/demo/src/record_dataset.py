from pathlib import Path
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
# Participante que graba AHORA. Cada participante va a su propia carpeta para
# poder hacer despues una evaluacion con participantes separados entre train y
# test (el split temporal que hace este script por si solo es demasiado
# optimista: los fotogramas consecutivos son casi identicos).
PARTICIPANT = 'p1'

# Clases en UNA SOLA PALABRA: landmarksLib.GetLandmarksFromImages saca el numero
# de frame con file.split("_")[1], asi que un guion bajo en el nombre de clase
# rompe el parseo. El orden aqui es indiferente para grabar, pero la demo exige
# la lista en ORDEN ALFABETICO, asi que se dejan ya ordenadas.
CLASSES = ['ok', 'paper', 'rock', 'rockandroll', 'scissors', 'thumbsup']

NUM_IMAGES_PER_CLASS = 100   # minimo exigido por el enunciado
TRAINING_PERCENTAGE = 70     # 70 train / 30 test dentro de cada clase

config = Config(classes=CLASSES,
                dataset_dir=str(PROJECT_DIR / 'data' / ('gestos_pids_' + PARTICIPANT)),
                num_images_per_class=NUM_IMAGES_PER_CLASS,
                training_percentage=TRAINING_PERCENTAGE,
                use_landmarks=True)
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
            if not cv2.imwrite(filename, recorded_images[i]):
                raise IOError('cv2.imwrite fallo al escribir %s '
                              '(carpeta inexistente o ruta invalida)' % filename)
            written += 1
            print('Recorded ', filename)
    print('[%s] %d imagenes guardadas (%d train / %d test)' % (class_to_save, written, n_train, n_test))


def main():
    # Recording setup 
    num_samples_per_class = RecordingSetup(config)

    # Create default dataset folders
    config.CreateDefaultDatasetFolders()

    # Create the detector
    detector = ConfigMediapipeDetector()  # [PARCHE] antes 'HAR_mediapipe/models/...' relativo al CWD

    # Start camera, use CVCamera if working on a laptop and PICamera in case you are working on a Raspberry PI
    if ON_RASPBERRY_PI:
        cam = PICamera(recording_res=cam_config.resolution)
        if ON_SENSE_HAT:
            sense_hat = SenseHat()
            sense_hat.set_rotation(180)
    else:
        cam = CVCamera(recording_res=cam_config.resolution, index_cam=0) # Use the first camera
        if ON_SENSE_HAT:
            sense_hat = None

    # Start camera
    cam.start()

    # Main loop
    for c in config.classes:
        print("\nPREPARING TO RECORD CLASS:", c)

        preview_msgs = WindowMessage(
            txt1 = "Class to be recorded: " + c, pos1 = (70, 210), col1 = colors.color['green'],
            txt2 = "Get ready and press \'s\' to start recording", pos2 = (70, 260), col2 = colors.color['green'],
            txt3 = "or \'q\' to exit.", pos3 = (70, 300), col3 = colors.color['green'])
        
        # Display preview screen
        DisplayPreviewScreen(cam, detector, preview_msgs)

        recording_msgs = WindowMessage(
            txt1 = "Recording in progress...", pos1 = (20, 40), col1 = colors.color['red'],
            txt2 = "Get ready and press \'s\' to start recording", pos2 = (20, 80), col2 = colors.color['red'],
            txt3 = "", pos3 = (20, 120), col3 = colors.color['red'])
        
        # Start recording images
        recorded_images = StartRecordingImages(cam, detector, num_samples_per_class['total'], recording_msgs)

        # Save images to disk
        SaveRecordedImagesToDisk(recorded_images, c, num_samples_per_class)

    print('\n[RECORDING FINISHED SUCCESSFULLY!!!]\n')

    post_msgs = WindowMessage(
            txt1 = "Recording finished successfully!!!", pos1 = (70, 210), col1 = colors.color['blue'],
            txt2 = "You can now press \'q\' to exit...", pos2 = (70, 260), col2 = colors.color['blue'],
            txt3 = "", pos3 = (70, 300), col3 = colors.color['blue'])

    # Display final message
    DisplayPreviewScreen(cam, detector, post_msgs)

    # Release resources
    cam.stop()          # [PARCHE] cam.stop() ahora tambien hace destroyAllWindows()
    print('[DATASET GUARDADO EN] %s' % config.dataset_dir)
if __name__ == "__main__":
    main()
