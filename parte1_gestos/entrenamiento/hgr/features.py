"""Del DataFrame de landmarks a la entrada de los modelos.

Orden de las transformaciones (siempre el mismo al entrenar y en la demo):

    coordenadas MediaPipe (x, y en [0,1])
      -> espacio con aspecto corregido  P  (x * ancho/alto, y)   [unidades de alto de imagen]
      -> [aumentacion, solo en train]
      -> [espejo segun la lateralidad estimada por MediaPipe]
      -> normalizacion
      -> entrada: (N, 21, 2, 1) para las CNN, (N, 42) para el resto

Por que corregir el aspecto: MediaPipe normaliza x por el ANCHO e y por el ALTO.
En una imagen 1280x720 una unidad de x mide 1.78 veces lo que una de y, asi que
girar o medir distancias directamente sobre esas coordenadas deforma la mano.

Normalizaciones:
  ninguna            coordenadas crudas de MediaPipe. Es lo que hace el notebook de
                     la asignatura: norm_type="None" y la condicion norm_type=="L0"
                     nunca se cumple. La posicion de la mano en el encuadre es una
                     feature mas, y eso no deberia importar para reconocer el gesto.
  muneca             todos los landmarks relativos a la muneca (landmark 0), incluida
                     la propia muneca, que queda en (0, 0). normalize_from_0_landmark
                     del repo empieza el bucle en k=2 y deja x0, y0 absolutos.
  muneca_escala      ademas, dividido por la distancia muneca -> nudillo del corazon
                     (landmarks 0 -> 9). Esa distancia apenas cambia entre gestos
                     porque la palma no se deforma: quita la dependencia de lo cerca
                     que este la mano de la camara.
  muneca_escala_rot  ademas, girado para que el vector muneca -> nudillo del corazon
                     apunte hacia arriba. Quita la inclinacion de la mano en el plano
                     de la imagen. Contrapartida: si dos gestos se distinguieran solo
                     por la orientacion (pulgar arriba vs pulgar abajo) dejarian de
                     poder separarse. En nuestras 6 clases no ocurre.
"""
import numpy as np

from . import constantes as C


def coordenadas(df):
    """(P, ar): P con forma (N, 21, 2) en espacio de aspecto corregido; ar = ancho/alto."""
    ar = (df['ancho'].to_numpy(float) / df['alto'].to_numpy(float))
    x = df[C.COLS_X].to_numpy(float) * ar[:, None]
    y = df[C.COLS_Y].to_numpy(float)
    return np.stack([x, y], axis=-1), ar


def coordenadas_desde_mediapipe(xy, ancho, alto):
    """Igual que coordenadas() pero desde un array (N, 21, 2) de x, y crudos."""
    xy = np.asarray(xy, dtype=float)
    ar = np.full(len(xy), float(ancho) / float(alto))
    P = xy.copy()
    P[..., 0] = P[..., 0] * ar[:, None]
    return P, ar


def espejar(P, ar, mascara):
    """Refleja horizontalmente dentro del encuadre las filas marcadas."""
    Q = P.copy()
    m = np.asarray(mascara, dtype=bool)
    Q[m, :, 0] = ar[m, None] - P[m, :, 0]
    return Q


def mascara_espejo(handedness, lado='Left'):
    """True en las manos que hay que reflejar para llevarlas todas a la misma lateralidad.

    Ojo: MediaPipe asume imagen tipo selfie (espejada). Nuestras imagenes no lo estan,
    asi que su 'Left' suele ser la mano DERECHA de la persona. Da igual para lo que
    importa aqui: se lleva a TODAS las manos a la misma lateralidad, sea cual sea.
    """
    return np.asarray([h == lado for h in handedness], dtype=bool)


def normalizar(P, ar, metodo):
    if metodo not in C.NORMALIZACIONES:
        raise ValueError('normalizacion desconocida: %r (opciones: %s)' % (metodo, C.NORMALIZACIONES))
    if metodo == 'ninguna':
        Q = P.copy()
        Q[..., 0] = P[..., 0] / ar[:, None]      # vuelta exacta a las coordenadas de MediaPipe
        return Q

    Q = P - P[:, C.MUNECA:C.MUNECA + 1, :]
    if metodo == 'muneca':
        return Q

    escala = np.linalg.norm(Q[:, C.MCP_CORAZON, :], axis=1)
    escala = np.where(escala < 1e-9, 1.0, escala)
    Q = Q / escala[:, None, None]
    if metodo == 'muneca_escala':
        return Q

    v = Q[:, C.MCP_CORAZON, :]
    angulo = np.arctan2(v[:, 1], v[:, 0])
    giro = -np.pi / 2 - angulo                  # llevar v a (0, -1): "arriba" con el eje y hacia abajo
    c, s = np.cos(giro), np.sin(giro)
    R = np.stack([np.stack([c, -s], axis=-1), np.stack([s, c], axis=-1)], axis=-2)   # (N, 2, 2)
    return np.einsum('nij,nkj->nki', R, Q)


def transformar(P, ar, handedness, metodo, espejo=False, lado_espejo='Left'):
    if espejo:
        P = espejar(P, ar, mascara_espejo(handedness, lado_espejo))
    return normalizar(P, ar, metodo)


def aumentar(P, ar, rng, n_copias, rotacion_grados=15.0, escala=0.10, desplazamiento=0.05,
             ruido=0.004, voltear=False):
    """Copias perturbadas de P (solo para train).

    Cada copia: giro aleatorio en [-rotacion, +rotacion] y escalado en [1-escala, 1+escala]
    alrededor del centro de la mano, desplazamiento en [-d, +d] y ruido gaussiano por
    landmark (simula el temblor de MediaPipe). Con voltear=True, ademas se refleja la
    mitad de las copias: alternativa al espejo por lateralidad para lograr invarianza
    izquierda/derecha solo con datos.

    Devuelve (P_aug, ar_aug, indice_origen).
    """
    if n_copias <= 0:
        return P[:0].copy(), ar[:0].copy(), np.zeros(0, dtype=int)
    N = len(P)
    idx = np.repeat(np.arange(N), n_copias)
    B = P[idx].copy()
    A = ar[idx].copy()
    M = len(B)
    theta = np.deg2rad(rng.uniform(-rotacion_grados, rotacion_grados, M))
    s = rng.uniform(1.0 - escala, 1.0 + escala, M)
    t = rng.uniform(-desplazamiento, desplazamiento, (M, 1, 2))
    centro = B.mean(axis=1, keepdims=True)
    c, sn = np.cos(theta), np.sin(theta)
    R = np.stack([np.stack([c, -sn], axis=-1), np.stack([sn, c], axis=-1)], axis=-2)
    B = centro + s[:, None, None] * np.einsum('nij,nkj->nki', R, B - centro) + t
    B = B + rng.normal(0.0, ruido, B.shape)
    if voltear:
        B = espejar(B, A, rng.random(M) < 0.5)
    return B, A, idx


def preparar_entrada(Q, forma):
    """'cnn' -> (N, 21, 2, 1) con [:, :, 0] = x y [:, :, 1] = y, igual que
    ArrangeInputDataForNetwork del repo y el reshape de la demo.
    'plano' -> (N, 42) intercalado x0, y0, x1, y1... como el .npy del notebook."""
    Q = np.asarray(Q, dtype=np.float32)
    if forma == 'cnn':
        return Q[..., None]
    if forma == 'plano':
        return Q.reshape(len(Q), -1)
    raise ValueError('forma de entrada desconocida: %r' % forma)
