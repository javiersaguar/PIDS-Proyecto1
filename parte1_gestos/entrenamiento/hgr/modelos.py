"""Registro de modelos con una interfaz comun: ajustar / predecir_proba / guardar.

cnn_baseline   la CNN del enunciado: entrada 21x2, DOS Conv2D de 16 filtros con kernel
               que recorre 5 landmarks, ReLU, Flatten, Dense(32) ReLU, Dense(C) softmax.
               (El enunciado dice "entrada 2x21 y kernel 1x5"; aqui es (21,2,1) con
               kernel (5,1): la misma operacion traspuesta, y la forma que ya espera
               la demo del repo con np.reshape(..., (1, 21, 2, 1)).)
cnn_repo       la CNN1 que construye DE VERDAD el notebook: UNA sola Conv2D (la segunda
               esta comentada) y Dropout 0.3 tras la convolucion y tras Dense(32).
mlp            perceptron multicapa 42 -> 64 -> 32 -> C. Referencia de red sin estructura
               convolucional.
svm            SVM con kernel RBF sobre las 42 coordenadas estandarizadas.
random_forest  200 arboles. Modelo grande en disco: interesante para el trade-off.
knn            5 vecinos. No aprende nada: guarda todo el train. Cota inferior sencilla.
logreg         regresion logistica. Si acierta casi tanto como la CNN, el problema es
               casi linealmente separable tras normalizar.

Hiperparametros de las redes: los del notebook (AdamW lr=1e-3, weight_decay=1e-4, batch 32,
early stopping sobre val_loss restaurando los mejores pesos) salvo la duracion: hasta 200 epocas
con paciencia 20, en vez de 300 y 50. Medido con las 5 tomas reales (experimento prueba_gpu), la
mejor epoca llega en la 23 de media en LOPO y en la 53 en temporal: con paciencia 50 cada
entrenamiento seguia 50 epocas mas sin mejorar, que era la mayor parte del tiempo de la rejilla.
Los modelos clasicos van con valores por defecto razonables y SIN ajuste sobre test. Todos los
modelos se entrenan exactamente con el mismo conjunto de train; val solo lo usan las redes para parar.

Rejilla por defecto: sin cnn_repo, porque esa red (la CNN1 del repo) ya la entrena el notebook de
la asignatura (HAR_mediapipe_local.ipynb) y aqui solo duplicaria tiempo de GPU. Sigue disponible
con --modelos cnn_repo.
"""
import numpy as np

MODELOS = ['cnn_baseline', 'cnn_repo', 'mlp', 'svm', 'random_forest', 'knn', 'logreg']
MODELOS_POR_DEFECTO = ['cnn_baseline', 'mlp', 'svm', 'random_forest', 'knn', 'logreg']
FORMA_ENTRADA = {'cnn_baseline': 'cnn', 'cnn_repo': 'cnn', 'mlp': 'plano', 'svm': 'plano',
                 'random_forest': 'plano', 'knn': 'plano', 'logreg': 'plano'}
FAMILIA = {'cnn_baseline': 'red neuronal', 'cnn_repo': 'red neuronal', 'mlp': 'red neuronal',
           'svm': 'clasico', 'random_forest': 'clasico', 'knn': 'clasico', 'logreg': 'clasico'}
# Modelos cuyo resultado depende de la semilla (con aumentacion, todos lo son)
ESTOCASTICOS = {'cnn_baseline', 'cnn_repo', 'mlp', 'svm', 'random_forest'}
HP_REDES = {'epocas': 200, 'paciencia': 20, 'batch': 32, 'lr': 1e-3, 'weight_decay': 1e-4}


class ModeloKeras:
    familia = 'red neuronal'

    def __init__(self, nombre, n_clases, hp=None):
        self.nombre, self.n_clases = nombre, n_clases
        self.hp = {**HP_REDES, **(hp or {})}
        self.modelo, self.historial = None, {}
        self.epocas_entrenadas = self.mejor_epoca = None

    def _construir(self):
        import keras
        from keras import layers
        C = self.n_clases
        if self.nombre == 'cnn_baseline':
            capas = [keras.Input((21, 2, 1)),
                     layers.Conv2D(16, (5, 1), padding='same', activation='relu'),
                     layers.Conv2D(16, (5, 1), padding='same', activation='relu'),
                     layers.Flatten(),
                     layers.Dense(32, activation='relu'),
                     layers.Dense(C, activation='softmax')]
        elif self.nombre == 'cnn_repo':
            capas = [keras.Input((21, 2, 1)),
                     layers.Conv2D(16, (5, 1), padding='same', activation='relu'),
                     layers.Dropout(0.3),
                     layers.Flatten(),
                     layers.Dense(32, activation='relu'),
                     layers.Dropout(0.3),
                     layers.Dense(C, activation='softmax')]
        elif self.nombre == 'mlp':
            capas = [keras.Input((42,)),
                     layers.Dense(64, activation='relu'),
                     layers.Dropout(0.2),
                     layers.Dense(32, activation='relu'),
                     layers.Dense(C, activation='softmax')]
        else:
            raise ValueError(self.nombre)
        m = keras.Sequential(capas, name=self.nombre)
        m.compile(optimizer=keras.optimizers.AdamW(learning_rate=self.hp['lr'], weight_decay=self.hp['weight_decay']),
                  loss='sparse_categorical_crossentropy', metrics=['accuracy'])
        return m

    def ajustar(self, X_train, y_train, X_val, y_val, semilla):
        import keras
        keras.backend.clear_session()
        keras.utils.set_random_seed(int(semilla))
        self.modelo = self._construir()
        hay_val = X_val is not None and len(X_val) > 0
        parada = keras.callbacks.EarlyStopping(monitor='val_loss' if hay_val else 'loss',
                                               patience=self.hp['paciencia'], restore_best_weights=True)
        h = self.modelo.fit(X_train, y_train, validation_data=(X_val, y_val) if hay_val else None,
                            epochs=self.hp['epocas'], batch_size=self.hp['batch'], shuffle=True,
                            verbose=0, callbacks=[parada])
        self.historial = {k: [float(v) for v in vs] for k, vs in h.history.items()}
        self.epocas_entrenadas = len(self.historial.get('loss', []))
        clave = 'val_loss' if hay_val else 'loss'
        self.mejor_epoca = int(np.argmin(self.historial[clave])) + 1 if self.historial.get(clave) else None
        return self

    def predecir_proba(self, X):
        return np.asarray(self.modelo.predict(X, batch_size=2048, verbose=0))

    def n_parametros(self):
        return int(self.modelo.count_params())

    def guardar(self, carpeta):
        from pathlib import Path
        ruta = Path(carpeta) / 'modelo.keras'
        ruta.parent.mkdir(parents=True, exist_ok=True)
        self.modelo.save(ruta)
        return ruta


class ModeloSklearn:
    familia = 'clasico'

    def __init__(self, nombre, n_clases, hp=None):
        self.nombre, self.n_clases = nombre, n_clases
        self.modelo, self.historial = None, {}
        self.epocas_entrenadas = self.mejor_epoca = None

    def _construir(self, semilla):
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.neighbors import KNeighborsClassifier
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.svm import SVC
        if self.nombre == 'svm':
            return make_pipeline(StandardScaler(), SVC(kernel='rbf', C=10.0, gamma='scale',
                                                       probability=True, random_state=int(semilla)))
        if self.nombre == 'random_forest':
            return RandomForestClassifier(n_estimators=200, random_state=int(semilla), n_jobs=1)
        if self.nombre == 'knn':
            return make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=5))
        if self.nombre == 'logreg':
            return make_pipeline(StandardScaler(), LogisticRegression(max_iter=5000))
        raise ValueError(self.nombre)

    def ajustar(self, X_train, y_train, X_val, y_val, semilla):
        self.modelo = self._construir(semilla)
        self.modelo.fit(X_train, y_train)
        return self

    def predecir_proba(self, X):
        p = self.modelo.predict_proba(X)
        completo = np.zeros((len(X), self.n_clases))
        completo[:, np.asarray(self.modelo.classes_, dtype=int)] = p   # por si faltase alguna clase en train
        return completo

    def n_parametros(self):
        return None

    def guardar(self, carpeta):
        from pathlib import Path
        import joblib
        ruta = Path(carpeta) / 'modelo.joblib'
        ruta.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.modelo, ruta)
        return ruta


def crear_modelo(nombre, n_clases, hp=None):
    if nombre not in MODELOS:
        raise ValueError('modelo desconocido: %r (opciones: %s)' % (nombre, MODELOS))
    return (ModeloKeras if FAMILIA[nombre] == 'red neuronal' else ModeloSklearn)(nombre, n_clases, hp)


def cargar_modelo(ruta):
    from pathlib import Path
    ruta = Path(ruta)
    if ruta.suffix == '.keras':
        import keras
        return keras.models.load_model(ruta, compile=False)
    import joblib
    return joblib.load(ruta)
