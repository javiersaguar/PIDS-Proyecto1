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

No hace falta instalar Java, Scala, sbt ni Spark: se compilan dentro de Docker (`make test-spark`).
Sin GPU NVIDIA, el chatbot funciona en CPU con `make chatbot SIN_GPU=1` y `OLLAMA_MODELO=llama3.2:3b`.

## NVIDIA Container Toolkit (en Ubuntu/WSL2)

Para que el contenedor de Ollama use la GPU. Sigue la guía oficial de NVIDIA para Ubuntu (instalar el
paquete `nvidia-container-toolkit` desde su repositorio) y después:

```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
docker run --rm --gpus all ubuntu nvidia-smi
```

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
