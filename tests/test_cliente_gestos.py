"""Anti-rebote del cliente de gestos: solo sale un gesto estable, y nunca la imagen."""
import json
import urllib.error

from integracion.cliente_gestos import EmisorGestos


def emisor(monkeypatch, estabilidad=4, repetir=3.0):
    reloj = {'t': 1000.0}
    monkeypatch.setattr('integracion.cliente_gestos.time.monotonic', lambda: reloj['t'])
    e = EmisorGestos('clave', modelo='gestos_pids_CNN1', estabilidad=estabilidad,
                     confianza_minima=0.85, repetir_cada_s=repetir)
    enviados = []
    monkeypatch.setattr(e, 'enviar', lambda gesto, conf: enviados.append((gesto, conf)) or True)
    return e, enviados, reloj


def test_solo_envia_tras_mantener_el_gesto(monkeypatch):
    e, enviados, _ = emisor(monkeypatch)
    assert [e.observar('thumbsup', 0.9) for _ in range(3)] == [False, False, False]
    assert enviados == []
    assert e.observar('thumbsup', 0.97) is True
    assert enviados == [('thumbsup', 0.97)]


def test_none_o_poca_confianza_rompen_la_racha(monkeypatch):
    e, enviados, _ = emisor(monkeypatch)
    e.observar('paper', 0.99)
    e.observar('paper', 0.99)
    e.observar('None', 1.0)
    e.observar('paper', 0.5)
    assert [e.observar('paper', 0.99) for _ in range(3)] == [False, False, False]
    assert enviados == []
    assert e.observar('paper', 0.99) is True


def test_no_repite_el_mismo_gesto_antes_de_3_segundos(monkeypatch):
    e, enviados, reloj = emisor(monkeypatch, estabilidad=1)
    assert e.observar('thumbsup', 0.99) is True
    reloj['t'] += 2.9
    assert e.observar('thumbsup', 0.99) is False
    reloj['t'] += 0.2
    assert e.observar('thumbsup', 0.99) is True
    assert [g for g, _ in enviados] == ['thumbsup', 'thumbsup']


def test_un_gesto_distinto_no_espera_la_repeticion(monkeypatch):
    e, enviados, _ = emisor(monkeypatch, estabilidad=1)
    assert e.observar('thumbsup', 0.99) is True
    assert e.observar('paper', 0.99) is True
    assert [g for g, _ in enviados] == ['thumbsup', 'paper']


def test_enviar_solo_manda_etiqueta_y_confianza(monkeypatch):
    capturado = {}

    class Respuesta:
        status = 202

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def urlopen(peticion, timeout):
        capturado['url'] = peticion.full_url
        capturado['clave'] = peticion.get_header('X-api-key')
        capturado['cuerpo'] = json.loads(peticion.data.decode())
        capturado['timeout'] = timeout
        return Respuesta()

    monkeypatch.setattr('integracion.cliente_gestos.urllib.request.urlopen', urlopen)
    monkeypatch.setattr('integracion.cliente_gestos.socket.gethostname', lambda: 'portatil')
    ok = EmisorGestos('secreta', modelo='cnn', url='http://localhost:8001').enviar('thumbsup', 0.9876)
    assert ok is True
    assert capturado['url'] == 'http://localhost:8001/gestos'
    assert capturado['clave'] == 'secreta'
    assert capturado['timeout'] == 2
    assert capturado['cuerpo'] == {'gesto': 'thumbsup', 'confianza': 0.988, 'modelo': 'cnn',
                                   'dispositivo': 'portatil'}
    assert 'imagen' not in capturado['cuerpo']


def test_un_fallo_de_red_no_tumba_la_demo(monkeypatch, capsys):
    def urlopen(*_a, **_k):
        raise urllib.error.URLError('caido')

    monkeypatch.setattr('integracion.cliente_gestos.urllib.request.urlopen', urlopen)
    assert EmisorGestos('k', 'm').enviar('ok', 0.9) is False
    assert 'no se pudo enviar ok' in capsys.readouterr().out
