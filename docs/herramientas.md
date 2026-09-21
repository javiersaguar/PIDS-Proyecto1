# Herramientas y puesta a punto

Las partes 2 y 3 se desarrollan y ejecutan **dentro de Ubuntu (WSL2)**; la parte 1, en Windows.

## Lo que necesita cada miembro del equipo

| Herramienta | Para qué | Cómo comprobarlo |
|---|---|---|
| WSL2 con Ubuntu | Entorno Linux | `wsl -l -v` (en PowerShell) |
| Docker Engine con Compose v2 (dentro de Ubuntu) | Toda la plataforma | `docker compose version` |
| Git | Control de versiones | `git --version` |
| uv | Entorno Python local (tests y scripts) | `uv --version` |
| make | Atajos | `make` |
| VS Code + extensiones WSL, Python, Docker y Scala (Metals) | Edición | `code .` desde Ubuntu |
| NVIDIA Container Toolkit (solo con GPU NVIDIA) | Ollama con GPU | `docker run --rm --gpus all ubuntu nvidia-smi` |
| Node 22 con npm (solo para desarrollar el portal web) | `npm ci`, `npm run dev` y tests de la SPA | `node --version` |

No hace falta instalar Java, Scala, sbt ni Spark: se compilan dentro de Docker (`make test-spark`). Tampoco Node
para usar el portal: `make frontend` construye la SPA dentro de Docker.
Sin GPU NVIDIA, el chatbot funciona en CPU con `make chatbot SIN_GPU=1` y `OLLAMA_MODELO=llama3.2:3b`.

## NVIDIA Container Toolkit (en Ubuntu/WSL2)

Es lo que permite que el contenedor de Ollama use la GPU. Probado el 17/09/2026 con Ubuntu 26.04,
Docker 29.6 y el driver 595.79 (RTX 5070 Laptop).

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo nvidia-ctk cdi generate --mode=wsl --output=/etc/cdi/nvidia.yaml
sudo systemctl restart docker
docker run --rm --gpus all ubuntu:24.04 nvidia-smi -L        # debe listar la GPU
```

**El paso del CDI es imprescindible** y no aparece destacado en la guía oficial: Docker 29 busca la GPU
por CDI, así que sin `/etc/cdi/nvidia.yaml` falla con «failed to discover GPU vendor from CDI: no known
GPU vendor found» aunque el toolkit esté instalado. En WSL hace falta `--mode=wsl`, porque el driver lo
aporta Windows (`/usr/lib/wsl/lib`).

Si no tienes la contraseña de `sudo` en WSL, desde PowerShell puedes cambiarla sin saber la anterior:
`wsl -d Ubuntu -u root passwd <tu_usuario>`.

## Primera ejecución

```bash
git clone https://github.com/javiersaguar/PIDS-Proyecto1.git ~/proyectos/PIDS-Proyecto1
cd ~/proyectos/PIDS-Proyecto1
make entorno        # .env con claves aleatorias
make sync           # entorno Python local
make test           # tests de Python
make nucleo         # S3, Redpanda, MongoDB y APIs
```

La primera construcción descarga las imágenes base (Spark, Airflow, Ollama, MongoDB…, unos 10 GB en
total) y el modelo del LLM (4,9 GB).

## Guías de estilo

- Código, comentarios y documentación en español.
- Python: tipado, funciones pequeñas, lógica pura separada de la entrada/salida (así se prueba sin servicios).
- Scala: funciones que reciben y devuelven `DataFrame`; los efectos (leer, escribir) se inyectan para los tests.
- Ningún secreto en el repositorio: todo sale de `.env`.
