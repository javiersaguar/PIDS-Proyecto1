import cv2
import sys
import os
import numpy as np
import random

# [PARCHE WINDOWS] tty y termios son modulos SOLO-UNIX: en Windows el import
# falla con ModuleNotFoundError y arrastra a config.py y a record_dataset.py.
if os.name == 'nt':
    import msvcrt
else:
    import tty
    import termios

class Colors:
    def __init__(self):
        #background=(0, 0, 0), text=(255, 255, 255), button=(0, 0, 255)):
        #self.background = background
        #self.text = text
        #self.button = button
        # Colors for annotations
        self.color = {}
        self.color['green'] = (0, 255, 0)
        self.color['blue'] = (255, 0, 0)
        self.color['red'] = (0, 0, 255)
        self.color['black'] = (0, 0, 0)
        self.color['yellow'] = (0, 255, 255)
        self.color['white'] = (255, 255, 255)
        self.color['purple'] = (128, 0, 128)
        self.color['orange'] = (0, 165, 255)
        self.color['gray'] = (128, 128, 128)
        self.color['brown'] = (42, 42, 165)
        self.color['pink'] = (147, 20, 255)
        self.color['cyan'] = (255, 255, 0)
        self.color['magenta'] = (255, 0, 255)
        self.color['light_blue'] = (255, 216, 150)
        self.color['light_green'] = (250, 250, 211)
        self.color['light_red'] = (0, 0, 204)
        self.color['light_yellow'] = (0, 204, 204)
        self.color['light_purple'] = (153, 0, 153)
        self.color['light_orange'] = (0, 128, 255)
        self.color['light_gray'] = (192, 192, 192)
        self.color['light_brown'] = (42, 107, 165)
        self.color['light_pink'] = (204, 153, 255)
        self.color['light_cyan'] = (255, 255, 204)
        self.color['light_magenta'] = (255, 204, 255)

        self.classes = []
        self.class_colors = []
        self.list = []

    def SelectRandomColorFromListForClasses(self, classes):
        self.classes = classes
        self.class_colors = []
        for _ in range(len(classes)):
            self.class_colors.append(self.color[random.choice(list(self.color.keys()))])
    
    def GetColorForClass(self, class_name):
        return self.class_colors[self.classes.index(class_name)]
    
    def DefineListRandomColorsForLabels(self, labels):
        self.classes = labels
        self.list = np.random.uniform(0, 255, size=(len(labels), 3))
        self.class_colors = [tuple(map(int, color)) for color in self.list]

def wait_for_keypress(target_key, exit_key, yes_to_all_key):
    """Lee una tecla sin Enter. Devuelve True si el usuario elige 'si a todo'.

    [PARCHE WINDOWS] El original usaba tty.setraw()/termios sobre sys.stdin, que
    no existen en Windows. Ademas tenia un 'return' dentro del 'finally', que
    descarta la excepcion en vuelo: el sys.exit(0) de la tecla 'q' quedaba
    anulado y la grabacion continuaba igualmente. Aqui el exit funciona.
    Nota: msvcrt.getch() devuelve bytes, por eso se usa getwch() (str).
    """
    print(f"Press '{target_key}' to continue or '{exit_key}' to exit... ('{yes_to_all_key}') if YES to all...")
    sys.stdout.flush()

    if os.name == 'nt':
        while True:
            char = msvcrt.getwch()
            if char == target_key:
                return False
            elif char == yes_to_all_key:
                print("Yes to all...")
                return True
            elif char == exit_key:
                print("Exiting...")
                sys.exit(0)

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    yes_to_all_result = False
    try:
        tty.setraw(sys.stdin.fileno())
        while True:
            char = sys.stdin.read(1)
            if char == target_key:
                break
            elif char == yes_to_all_key:
                print("Yes to all...")
                yes_to_all_result = True
                break
            elif char == exit_key:
                print("Exiting...")
                sys.exit(0)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return yes_to_all_result

class WindowMessage:
    def __init__(self, txt1=None, col1=None, pos1=None, txt2=None, col2=None, pos2=None, txt3=None, col3=None, pos3=None):

        # Initialize messages with default or provided values
        self.msg = []

        texts = [txt1, txt2, txt3]
        colors = [col1, col2, col3]
        positions = [pos1, pos2, pos3]

        for txt, col, pos in zip(texts, colors, positions):
            self.msg.append({
                'text': txt if txt is not None else '',
                'color': col if col is not None else (255, 0, 0),
                'position': pos if pos is not None else (0, 0)
            })

    def ShowWindowMessages(self, image):
        for i in range(3):
            cv2.putText(
                image, 
                self.msg[i]['text'],
                org=self.msg[i]['position'],
                fontFace=2, # cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=0.75, 
                color=self.msg[i]['color'],
                thickness=2)  # [PARCHE] por defecto era 1: ilegible a 1280x720