# Repositorio: autoría, incidencias y cómo recuperarse

Documento de referencia para cualquier persona o asistente que trabaje en el repositorio. Explica la regla de
autoría, cómo se hace cumplir, la incidencia del 22/09/2026 (se borró y se recreó el repositorio en GitHub) y
qué hacer si algo de eso vuelve a dar problemas, sobre todo con Vercel.

## 1. Regla principal: solo el grupo como autor

En el repositorio solo figuran como autores los cinco del grupo: Javier Saguar, Alejandro Cuevas, Mónica
Fernández, Pedro José Orrego y Daniel Naval. Si se trabaja con un asistente de programación, el commit lo
firma la persona que lo ha usado y revisado. **Nunca**, en ningún sitio:

- trailers `Co-Authored-By:` (ni siquiera entre miembros del grupo: cada commit tiene un único autor);
- firmas automáticas del tipo «Generated with …» o el emoji 🤖 en commits o en *pull requests*;
- menciones a herramientas de IA como autoras en código, comentarios, documentación o commits.

Muchas herramientas añaden esas líneas **por defecto** al hacer commits o abrir *pull requests*. Quien las use
tiene que desactivarlo en su configuración y revisar el mensaje antes de subir.

## 2. Cómo se hace cumplir (tres barreras)

| Barrera | Qué hace | Dónde |
|---|---|---|
| Hook `commit-msg` | Quita del mensaje las líneas prohibidas antes de crear el commit y avisa de ello | `.githooks/commit-msg`; se activa con `make hooks` (lo hace también `make sync`) |
| CI «Autoría» | En cada *push* y *pull request* revisa los mensajes de los commits nuevos, y el título y la descripción del PR. Si encuentra algo, falla | `.github/workflows/autoria.yml` |
| Plantilla de PR | Casilla «Los autores somos solo los cinco del grupo» | `.github/pull_request_template.md` |

Las tres usan las mismas reglas, en `scripts/comprobar_autoria.py` (probadas en `tests/test_autoria.py`):

```bash
python3 scripts/comprobar_autoria.py --rango origin/main..HEAD   # revisar mis commits antes de subir
git config core.hooksPath                                        # debe responder .githooks
```

El hook es local: cada persona tiene que ejecutar `make hooks` (o `make sync`) una vez en su copia, y se puede
saltar con `--no-verify`. Por eso existe también la barrera del CI. **Un PR con el CI «Autoría» en rojo no se
fusiona.** La descripción del PR se puede corregir editándola; el CI se vuelve a lanzar solo.

## 3. Incidencia del 22/09/2026: repositorio borrado y recreado

**Qué pasó.** El commit `fa9036a` («Portal web: rediseño de las secciones del frontend», de Alejandro Cuevas)
llegó a `main` con el PR #1, y tanto el commit como la descripción del PR llevaban una coautoría y una firma
automáticas de un asistente. GitHub pasó a mostrar a esa herramienta como contribuidora del repositorio.

**Qué se hizo, por orden:**

1. Se reescribieron el commit y el *merge* del PR sin el trailer, **con el mismo código, autor, fecha y
   texto** (`git commit-tree`, ver §5): quedaron como `6785183` y `095b340`. Se subieron con
   `--force-with-lease` a `main` y a `alejandro-cuevas`.
2. No bastó: GitHub guarda cada PR en una referencia de solo lectura (`refs/pull/1/head`) que seguía
   apuntando al commit antiguo, y el PR no se puede borrar ni editar su lista de commits. Solo el soporte de
   GitHub puede purgarlo.
3. Se hizo una copia completa (espejo de Git, configuración, colaboradores, PR) en el equipo de Javier:
   `~/copias/PIDS-Proyecto1-20260922-0051` (WSL).
4. Se **borró el repositorio** `javiersaguar/PIDS-Proyecto1` en GitHub, se creó otro con el mismo nombre
   (público) y se subieron las 9 ramas limpias: `main`, `alejandro-cuevas`, `daniel-naval`, `javier-saguar`,
   `monica-fernandez`, `pedro-jose-orrego`, `tarea/frontend`, `tarea/frontend-demo` y `tarea/rag-base`.
5. Se volvió a invitar con permiso de escritura a `processDaniel`, `pedrocrack05`, `DRO98` y
   `monicafdezlortal`.
6. Se comprobó que GitHub ya no encuentra `fa9036a` y que los contribuidores son solo miembros del grupo.

**Qué se perdió con el borrado (y es normal que no esté):**

- El PR #1 y su conversación (su contenido está en la copia; el código está en `main`).
- El historial de ejecuciones del CI y los *deployments* y entornos que Vercel había registrado en GitHub.
- La conexión de Vercel con el repositorio (§4) y los accesos de los colaboradores hasta que aceptan la
  invitación.
- No había issues, secretos del CI, reglas de protección, webhooks ni *releases*.

**Hashes que siguen valiendo.** Toda la historia anterior a `235ddc2` es idéntica: los commits citados en
`BITACORA.md` siguen existiendo con el mismo hash. Solo cambiaron `fa9036a → 6785183` y `7ea22c9 → 095b340`.

## 4. Problemas que pueden aparecer y cómo resolverlos

### Vercel no despliega (proyectos `happytaxi` y `yellowveil`)

Vercel se engancha al repositorio por su **identificador interno**, no por el nombre. El repositorio nuevo
tiene otro identificador, así que después de recrearlo Vercel sigue apuntando al borrado.

**Síntomas:** un *push* a `main` no lanza ningún despliegue; el panel de Vercel dice que el repositorio no se
encuentra o está desconectado; la web pública sigue mostrando la versión anterior.

**Solución** (la tiene que hacer el dueño de la cuenta de Vercel, en la web):

1. En cada proyecto (`happytaxi` y `yellowveil`): *Settings → Git → Disconnect* y después *Connect Git
   Repository* → `javiersaguar/PIDS-Proyecto1`, rama de producción `main`.
2. Si el repositorio no aparece en la lista: en GitHub, *Settings → Applications → Installed GitHub Apps →
   Vercel → Configure* y añadirlo a los repositorios permitidos.
3. Lanzar un despliegue (*Deployments → Redeploy*, o un *push* a `main`) y comprobar que termina en verde.

La configuración de la construcción **no está en Vercel sino en el repositorio** (`vercel.json`), así que no
hay que tocar nada más. Si falla con «No FastAPI entrypoint found», es que no está leyendo `vercel.json`:
comprobar que el *Root Directory* del proyecto es la raíz del repositorio. Nunca se arregla añadiendo
`[tool.vercel]` al `pyproject.toml` (publicaría la API de acceso; ver la entrada T14 de `BITACORA.md` y
`parte4_frontend/demo/README.md`).

### Alguien con una copia anterior al 22/09/2026

Una copia clonada antes de la incidencia tiene el commit antiguo. Si se sube, **vuelve a colar la coautoría**.
Hay que sincronizarla una vez (quien tenga cambios sin guardar, antes `git stash`):

```bash
git fetch origin && git checkout main && git reset --hard origin/main
```

Para comprobar si una rama local arrastra el commit antiguo (si responde «contaminada», no subirla):

```bash
git merge-base --is-ancestor fa9036a HEAD 2>/dev/null && echo contaminada || echo limpia
```

Si la rama tiene trabajo propio encima del commit antiguo, se rehace sobre `main` con
`git rebase --onto origin/main 7ea22c9 <rama>` (o se le pide ayuda a Javier).

### Otras

- **Un colaborador no puede hacer *push* («Permission denied» o 403):** no ha aceptado la invitación. Está en
  https://github.com/javiersaguar/PIDS-Proyecto1/invitations o en el correo.
- **Enlaces antiguos al PR #1:** ya no existen. El código está en `main` (commit `095b340`).
- **El CI no aparece en un commit antiguo:** el historial de ejecuciones se perdió con el borrado; se genera de
  nuevo con cada *push*.
- **La sesión de `gh` de Javier conserva el permiso `delete_repo`** que se pidió para borrar el repositorio.
  Se retira con `gh auth refresh -h github.com -r delete_repo`.

## 5. Si se cuela una coautoría (procedimiento)

Cuanto antes se detecte, más fácil. Nunca se resuelve borrando el repositorio salvo que ya esté en un PR
fusionado y no se pueda esperar al soporte de GitHub.

| Situación | Qué hacer |
|---|---|
| Commit hecho, sin subir | `git commit --amend` y borrar la línea (o `make hooks` y repetir el commit) |
| Subido a mi rama, sin PR | Reescribir (`git rebase -i` o `--amend`) y `git push --force-with-lease origin <rama>` |
| En un PR abierto | Igual que arriba, y editar la descripción del PR si también la lleva. El CI «Autoría» debe quedar en verde |
| Ya fusionado en `main` | Reescribir el commit y el *merge* conservando autor, fecha y árbol (abajo), subir `main` y la rama con `--force-with-lease`, y pedir a todos que sincronicen. Si GitHub sigue mostrando la coautoría por el PR: soporte de GitHub (*Remove sensitive data*: borrar el PR y purgar el commit), o, en último caso, recrear el repositorio como en §3 |

Reescribir un commit ya fusionado sin cambiar nada más que el mensaje (`O` es el commit con la coautoría,
`M` el *merge* del PR que lo trajo y ninguno tiene commits encima; si los tiene, hay que rehacerlos también):

```bash
env_de() { export GIT_AUTHOR_NAME="$(git show -s --format=%an $1)" GIT_AUTHOR_EMAIL="$(git show -s --format=%ae $1)" \
  GIT_AUTHOR_DATE="$(git show -s --format=%aD $1)" GIT_COMMITTER_NAME="$(git show -s --format=%cn $1)" \
  GIT_COMMITTER_EMAIL="$(git show -s --format=%ce $1)" GIT_COMMITTER_DATE="$(git show -s --format=%cD $1)"; }
git show -s --format=%B $O > /tmp/mensaje && python3 scripts/comprobar_autoria.py --mensaje /tmp/mensaje --limpiar
env_de $O; N=$(git commit-tree "$O^{tree}" -p "$O^1" -F /tmp/mensaje)
env_de $M; NM=$(git show -s --format=%B $M | git commit-tree "$M^{tree}" -p "$M^1" -p "$N")
git diff $M $NM --quiet && echo "mismo código"            # tiene que decir «mismo código»
git branch -f <rama-del-pr> $N && git checkout main && git merge --ff-only $NM
```

Borrar o recrear el repositorio es **irreversible** y rompe Vercel y los accesos (§3 y §4): solo lo decide el
dueño del repositorio, y siempre después de una copia con `git clone --mirror`.
