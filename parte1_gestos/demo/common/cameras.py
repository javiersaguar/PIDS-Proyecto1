import cv2
import os
from time import sleep

class CameraConfig:
    def __init__(self, FPS=30, resolution='highres'): 
        # RESOLUTIONS
        self.resolutions = {}
        self.resolutions['highres'] = (1280, 720)
        self.resolutions['large'] = (640, 480)
        self.resolutions['small'] = (320, 200)

        # RESOLUTION
        self.resolution = self.resolutions[resolution]

        # FRAME RATE
        self.FPS = FPS
        
class Camera:
    def read_frame(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass


class CVCamera(Camera):
    """Camara via OpenCV.

    [PARCHES WINDOWS] respecto al original:
      1. Backend explicito. Sin el, en Windows OpenCV elige MSMF, que a veces
         tarda segundos en abrir o ignora la resolucion pedida. Medido en este
         portatil: DSHOW y MSMF dan ambos 1280x720 a 30 fps sostenidos.
      2. Fotogramas de calentamiento: la webcam integrada devuelve los primeros
         frames en negro (media 0.0) justo despues de abrir; sin esto las
         primeras muestras del dataset saldrian negras.
      3. isOpened(): avisa si el obturador fisico esta cerrado en vez de grabar
         100 imagenes inservibles en silencio.
      4. read_frame() respeta el flag 'ret'. El original devolvia el frame
         aunque la lectura fallase, y el bucle de grabacion lo guardaba.
    """

    def __init__(self, recording_res, index_cam=0, backend=None, warmup_frames=10):
        self.index_cam = index_cam
        self.rec_res = recording_res
        if backend is None:
            backend = cv2.CAP_DSHOW if os.name == 'nt' else cv2.CAP_ANY
        self.backend = backend
        self.warmup_frames = warmup_frames
        self.vid = None

    def read_frame(self):
        ret, frame = self.vid.read()
        if not ret:
            return None
        return frame

    def start(self):
        # OpenCV entrega los fotogramas de tres canales en orden BGR, igual que cv2.imread().
        self.vid = cv2.VideoCapture(self.index_cam, self.backend)
        if not self.vid.isOpened():
            raise RuntimeError(
                "No se pudo abrir la camara index=%d con backend=%d. "
                "Comprueba el obturador fisico / interruptor de camara del portatil, "
                "y que ninguna otra aplicacion (Teams, Zoom, Chrome) la este usando."
                % (self.index_cam, self.backend))
        self.vid.set(cv2.CAP_PROP_FRAME_WIDTH, self.rec_res[0])
        self.vid.set(cv2.CAP_PROP_FRAME_HEIGHT, self.rec_res[1])
        for _ in range(self.warmup_frames):
            self.vid.read()
        w = int(self.vid.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.vid.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if (w, h) != tuple(self.rec_res):
            print("[AVISO] se pidio %dx%d y la camara entrega %dx%d" % (self.rec_res[0], self.rec_res[1], w, h))

    def stop(self):
        if self.vid is not None:
            self.vid.release()
        cv2.destroyAllWindows()

    def close(self):
        self.stop()


class PICamera(Camera):
    def __init__(self, recording_res):
        try:
            from picamera2 import Picamera2, Preview
            import libcamera

            self.picam2 = Picamera2()
            #self.Preview = Preview
            preview_config = self.picam2.create_preview_configuration(
                main={"size": recording_res, "format": "RGB888"},#recording_res[::-1]},
                controls={
                    "AwbEnable": True,
                    # "AwbMode": libcamera.controls.AwbModeEnum.Indoor,
                    #"AwbMode": libcamera.controls.AwbModeEnum.Auto,
                    #"AnalogueGain": 1.0,
                },
            )
            self.picam2.configure(preview_config)

        except ModuleNotFoundError:
            print(
                "Cannnot initialize PiCamera on this device. Check if you are using a Raspberry Pi and it is up to date."
            )
            exit()

    def start(self):
        # self.picam2.start_preview(self.Preview.QTGL)
        self.picam2.start()
        sleep(2)  # Wait for the camera to warm up

    def close(self):
        self.picam2.close()

    def read_frame(self):
        # image_bgr = self.picam2.capture_array("main")
        # # Depending on the raspberry orientation
        # #image_bgr = cv2.rotate(image_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
        # image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        # return image_rgb
        image_rgb = self.picam2.capture_array("main")
        return image_rgb