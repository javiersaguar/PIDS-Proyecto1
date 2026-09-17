"""Descubrimiento de tomas grabadas con el kit y listado de sus imagenes.

Una toma es una carpeta  gestos_<participante>_<AAAAMMDD-HHMMSS>/  con train/ y
test/ dentro (kit v2, con metadata.json), o  gestos_pids_<participante>/  (kit v1).
Se buscan de forma recursiva, asi que da igual si al descomprimir un .zip queda
una carpeta dentro de otra con el mismo nombre.
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

RE_TOMA = re.compile(r'^gestos_(?P<participante>[a-z0-9]+)_(?P<marca>\d{8}-\d{6})$')
RE_LEGADO = re.compile(r'^gestos_pids_(?P<participante>[a-z0-9]+)$')
RE_IMAGEN = re.compile(r'^(?P<clase>[a-z0-9]+)_(?P<frame>\d{5})\.jpg$', re.IGNORECASE)


@dataclass
class Toma:
    carpeta: Path
    participante: str
    marca: str = None
    mano: str = None
    estado: str = 'desconocido'
    prueba: bool = False
    version_kit: str = '1'
    metadata: dict = field(default_factory=dict)

    @property
    def nombre(self):
        return self.carpeta.name


def es_carpeta_toma(d):
    d = Path(d)
    return d.is_dir() and (d / 'train').is_dir() and (d / 'test').is_dir()


def leer_toma(carpeta):
    """Toma a partir de su carpeta, o None si no se puede saber de quien es.

    Se acepta aunque alguien haya renombrado la carpeta, siempre que su metadata.json
    diga el participante: ignorar en silencio una toma renombrada seria perder datos.
    """
    carpeta = Path(carpeta)
    meta = {}
    f = carpeta / 'metadata.json'
    if f.exists():
        try:
            meta = json.loads(f.read_text(encoding='utf-8'))
        except (ValueError, OSError):
            meta = {'_error': 'metadata.json ilegible'}
    m = RE_TOMA.match(carpeta.name) or RE_LEGADO.match(carpeta.name)
    if not m and not meta.get('participante'):
        return None
    grupos = m.groupdict() if m else {}
    if not m and meta.get('toma'):
        m2 = RE_TOMA.match(str(meta['toma']))
        grupos = m2.groupdict() if m2 else {}
    return Toma(
        carpeta=carpeta,
        participante=str(meta.get('participante') or grupos['participante']).lower(),
        marca=grupos.get('marca'),
        mano=meta.get('mano'),
        estado=meta.get('estado', 'desconocido'),
        prueba=bool(meta.get('prueba')) or '_pruebas' in carpeta.parts,
        version_kit=str(meta.get('kit_version', '1')),
        metadata=meta,
    )


def descubrir_tomas(raices, incluir_pruebas=False, incluir_incompletas=False, avisos=None):
    """Lista de Toma encontradas bajo las raices dadas (sin duplicados)."""
    avisos = avisos if avisos is not None else []
    vistas, tomas = set(), []
    for raiz in raices:
        raiz = Path(raiz)
        if not raiz.exists():
            continue
        candidatas = [raiz] if es_carpeta_toma(raiz) else []
        candidatas += sorted(d for d in raiz.rglob('*') if d.name not in ('train', 'test') and es_carpeta_toma(d))
        for d in candidatas:
            clave = d.resolve()
            if clave in vistas:
                continue
            vistas.add(clave)
            t = leer_toma(d)
            if t is None:
                avisos.append('carpeta con train/test pero nombre no reconocido y sin metadata.json, '
                              'se IGNORA: %s' % d)
                continue
            if not (RE_TOMA.match(d.name) or RE_LEGADO.match(d.name)):
                avisos.append('toma con la carpeta renombrada (%s): se usa el participante de su '
                              'metadata.json (%s)' % (d.name, t.participante))
            if t.prueba and not incluir_pruebas:
                continue
            if not incluir_incompletas and t.estado in ('interrumpida', 'en_curso', 'incompleta'):
                avisos.append('toma con estado "%s" (%s): se IGNORA por defecto '
                              '(usa --incluir-incompletas para incluirla)' % (t.estado, t.nombre))
                continue
            tomas.append(t)
    tomas.sort(key=lambda t: (t.participante, t.marca or '', t.nombre))
    return tomas


def listar_imagenes(toma, avisos=None):
    """Una fila por JPG: la clase sale de la CARPETA (no del nombre del fichero)."""
    avisos = avisos if avisos is not None else []
    filas = []
    for subset in ('train', 'test'):
        base = toma.carpeta / subset
        for dclase in sorted(p for p in base.iterdir() if p.is_dir()):
            for f in sorted(dclase.glob('*.jpg')):
                m = RE_IMAGEN.match(f.name)
                if not m:
                    avisos.append('nombre de imagen no reconocido, se ignora: %s' % f)
                    continue
                if m.group('clase').lower() != dclase.name.lower():
                    avisos.append('imagen %s en la carpeta de %s: se usa la carpeta' % (f.name, dclase.name))
                filas.append({
                    'toma': toma.nombre,
                    'participante': toma.participante,
                    'mano_declarada': toma.mano,
                    'clase': dclase.name,
                    'subset': subset,
                    'frame': int(m.group('frame')),
                    'ruta_relativa': f.relative_to(toma.carpeta).as_posix(),
                    'carpeta_toma': str(toma.carpeta),
                })
    return filas
