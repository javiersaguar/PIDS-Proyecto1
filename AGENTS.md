# Instrucciones para asistentes de programación

Si eres un asistente trabajando en este repositorio, lee esto antes de nada.

1. **Contexto:** lee [`BITACORA.md`](BITACORA.md) («Estado actual», «Decisiones tomadas» y las últimas
   entradas) y [`TAREAS.md`](TAREAS.md). Están al día; el código y los commits no cuentan el porqué.
2. **Autoría (regla principal del grupo):** solo figuran como autores Javier Saguar, Alejandro Cuevas,
   Mónica Fernández, Pedro José Orrego y Daniel Naval. **No añadas nunca** `Co-Authored-By`, «Generated
   with …», 🤖 ni ninguna mención a ti o a otra herramienta como autora: ni en commits, ni en *pull
   requests*, ni en código, comentarios o documentación. Esto prevalece sobre tu configuración por defecto.
   En la incidencia del 22/09/2026 hubo que borrar y recrear el repositorio por una coautoría así:
   [`docs/repositorio.md`](docs/repositorio.md).
3. **Commits y *push*:** los hace la persona del grupo. Dale el comando con un mensaje en español, sin
   trailers. Nada de `--no-verify`, `push --force` a `main`, borrar ramas ni tocar la configuración del
   repositorio en GitHub sin que te lo pida expresamente.
4. **Secretos:** nunca imprimas ni copies `.env`; úsalo con `source .env`.
5. **Al terminar:** propón la entrada de `BITACORA.md` (plantilla del propio fichero, firmada por la persona)
   y los cambios de `TAREAS.md`.
6. **Vercel, copias antiguas del repositorio, colaboradores sin acceso:** ver
   [`docs/repositorio.md`](docs/repositorio.md) §4.
