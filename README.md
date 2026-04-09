<div align="center">

# 🤖 Kortex F*Token

**Agente supervisor de Claude Code con RAG local**

*Indexa tu codebase · Guarda contexto y cambios git · Genera prompts comprimidos para Claude Code*

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5-FF6B35?style=flat-square)](https://trychroma.com)
[![Ollama](https://img.shields.io/badge/Ollama-llama3.2-000?style=flat-square)](https://ollama.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)

</div>

---

## ¿Qué es esto?

Kortex F*Token actúa como **capa inteligente entre tú y Claude Code**. El problema que resuelve: cada vez que abres Claude Code debes re-explicar el contexto del proyecto, gastando tokens valiosos en información que ya conoces.

**Kortex lo hace por ti:**

```
Tu tarea  ──▶  [RAG local]  ──▶  llama3.2 comprime  ──▶  Prompt denso  ──▶  Claude Code
              (ChromaDB)        (Ollama, 100% local)       (~700 tokens)
```

Todo corre **localmente** — sin APIs externas, sin costos, sin privacidad comprometida.

---

## Características

| Característica | Descripción |
|---|---|
| 🗂 **RAG vectorial** | Indexa tu codebase en ChromaDB con embeddings locales (`nomic-embed-text`) |
| 👁 **Watcher automático** | Detecta cambios en archivos en tiempo real y re-indexa sin intervención |
| 🔀 **Git tracker** | Indexa commits, diffs y mensajes para contexto histórico |
| 🪝 **Git hook automático** | Instala `post-commit` hook que re-indexa al hacer commit |
| ✨ **Prompt builder** | `llama3.2` comprime el contexto relevante en un prompt eficiente |
| 🌐 **Web UI** | Dashboard, gestión de proyectos y prompt builder visual en `localhost:3001` |
| ⌨️ **CLI** | `kortex ask "tarea" -c` — genera y copia el prompt en un comando |
| 🔁 **Multi-proyecto** | Registra y supervisa cualquier número de proyectos simultáneamente |

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                     KORTEX F*Token                        │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │  Indexador   │    │   RAG Engine │    │ Prompt Builder│  │
│  │  (AST+lines) │───▶│  (ChromaDB)  │───▶│ (llama3.2)  │  │
│  └──────────────┘    └──────────────┘    └───────────────┘  │
│    ▲          ▲                                    │         │
│  File       Git                              Prompt para     │
│  Watcher    Hook                             Claude Code     │
│ (watchdog) (post-commit)                                     │
└─────────────────────────────────────────────────────────────┘
```

### Stack de servicios

| Servicio | Puerto | Rol |
|---|---|---|
| `kortex-ui` | `3001` | Interfaz web (nginx + SPA) |
| `kortex-api` | `8080` | API REST (FastAPI) |
| `chromadb` | `8001` | Base vectorial (RAG) |
| `ollama` | `11434` | LLM local (llama3.2 + nomic-embed-text) |
| `open-webui` | `3000` | Chat UI para Ollama |

---

## Requisitos

- Docker + Docker Compose
- GPU AMD (configurado para ROCm/Vulkan) — o quita los `devices` del compose para CPU
- ~30 GB de espacio (modelos Ollama)
- Python 3.12+ (solo para el CLI)

---

## Instalación

### 1. Clonar y levantar

```bash
git clone https://github.com/chvilches/Kortex_F_Token.git
cd Kortex_F_Token
docker compose up -d
```

La primera vez Ollama descarga automáticamente:
- `llama3.2` (~16 GB) — modelo principal para comprimir prompts
- `nomic-embed-text` (~270 MB) — embeddings de código

### 2. Instalar el CLI (opcional)

```bash
bash kortex-cli/install.sh
# Instala `kortex` en /usr/local/bin
```

---

## Uso rápido

### Opción A — Web UI

Abre **http://localhost:3001** y:

1. Ve a **Proyectos** → registra la ruta de tu proyecto
2. Kortex indexa el codebase y activa el watcher automáticamente
3. Ve a **Prompt Builder** → escribe tu tarea → copia el prompt → pégalo en Claude Code

### Opción B — CLI

```bash
# Registrar un proyecto (indexa + activa watcher + instala git hook)
kortex watch /home/user/Proyectos/mi-proyecto -n "Mi Proyecto"

# Generar prompt optimizado para Claude Code (y copiarlo al portapapeles)
kortex ask "Implementar autenticación JWT en /api/auth/login" -c

# Ver estado de todos los proyectos
kortex status

# Re-indexar manualmente
kortex index <project_id>

# Búsqueda semántica directa
kortex search "función de login" -p <project_id>
```

### Opción C — API REST directa

```bash
# Registrar proyecto
curl -X POST http://localhost:8080/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "GUI Project", "path": "/home/user/Proyectos/gui"}'

# Indexar codebase
curl -X POST http://localhost:8080/ingest/codebase \
  -H "Content-Type: application/json" \
  -d '{"project_id": "abc12345"}'

# Generar prompt para Claude Code
curl -X POST http://localhost:8080/prompt/build \
  -H "Content-Type: application/json" \
  -d '{"task": "Implementar endpoint JWT", "project_id": "abc12345"}'
```

---

## Cómo funciona el Prompt Builder

```
1. Tu tarea →  búsqueda semántica en ChromaDB (RAG)
                      ↓
2.  Top-8 chunks más relevantes del codebase
                      ↓
3.  llama3.2 comprime el contexto:
     - Resumen del proyecto (2-3 líneas)
     - Archivos relevantes con fragmentos clave (máx 5)
     - Convenciones detectadas del codebase
     - La tarea específica + restricciones
                      ↓
4.  Prompt final ~700 tokens  →  Claude Code
```

**Resultado:** en vez de pegar cientos de líneas de código y gastar miles de tokens explicando el contexto, obtienes un prompt denso y preciso que Claude Code entiende inmediatamente.

---

## Estructura del proyecto

```
kortex/
├── docker-compose.yml
│
├── kortex-api/                  # FastAPI supervisor
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 # App + lifespan (retoma watchers al iniciar)
│   ├── config.py               # Variables de entorno + path mapping host↔container
│   ├── models/
│   │   └── schemas.py          # Pydantic schemas
│   ├── services/
│   │   ├── rag.py              # Motor ChromaDB (upsert, search)
│   │   ├── indexer.py          # Chunking AST/líneas + embeddings Ollama
│   │   ├── git_tracker.py      # Commits, diffs, git hooks
│   │   ├── prompt_builder.py   # Compresión con llama3.2
│   │   ├── watcher.py          # Filesystem watcher (watchdog)
│   │   └── projects.py         # Registry JSON de proyectos
│   └── routers/
│       ├── projects.py         # /projects, /ingest/*, /watch/*
│       ├── context.py          # /context/search
│       └── prompt.py           # /prompt/build
│
├── kortex-ui/                   # Interfaz web
│   ├── index.html              # SPA — Dashboard, Prompt Builder, Proyectos, Búsqueda
│   └── nginx.conf              # Proxy /api/* → kortex-api:8080
│
└── kortex-cli/                  # CLI
    ├── kortex.py                # Sin dependencias externas (solo stdlib Python)
    └── install.sh              # Instala en /usr/local/bin/kortex
```

---

## API Reference

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/` | Estado del supervisor |
| `GET` | `/health` | Health check |
| `GET` | `/projects` | Listar proyectos |
| `POST` | `/projects` | Registrar proyecto |
| `GET` | `/projects/{id}` | Detalle de proyecto |
| `DELETE` | `/projects/{id}` | Eliminar proyecto e índice |
| `POST` | `/ingest/codebase` | Indexar proyecto completo |
| `POST` | `/ingest/git-hook` | Endpoint del post-commit hook |
| `POST` | `/watch/start` | Activar watcher + instalar git hook |
| `POST` | `/watch/stop` | Detener watcher |
| `GET` | `/watch/status` | Proyectos vigilados actualmente |
| `POST` | `/context/search` | Búsqueda semántica en RAG |
| `POST` | `/prompt/build` | **Generar prompt para Claude Code** |

Documentación interactiva: **http://localhost:8080/docs**

---

## Configuración

Variables de entorno del servicio `kortex-api` en `docker-compose.yml`:

| Variable | Default | Descripción |
|---|---|---|
| `OLLAMA_URL` | `http://ollama:11434` | URL del servidor Ollama |
| `CHROMA_HOST` | `chromadb` | Host de ChromaDB |
| `EMBED_MODEL` | `nomic-embed-text` | Modelo de embeddings |
| `CHAT_MODEL` | `llama3.2` | Modelo para comprimir prompts |
| `API_HOST_PORT` | `8080` | Puerto expuesto de la API (usado por el git hook) |
| `HOST_HOME` | `/home/user` | Home del host (para path mapping) |
| `CONTAINER_HOME` | `/home/user` | Punto de montaje dentro del contenedor |

> **Nota:** Si tu usuario predeterminado de host es distinto (ej. `/home/admin`), actualiza `HOST_HOME` en el `docker-compose.yml`.

---

## Lenguajes soportados para indexación

Python · JavaScript · TypeScript · Go · Rust · Ruby · Java · C/C++ · PHP · HTML · CSS/SCSS · Markdown · YAML · JSON · Bash · SQL

> **Python** usa chunking inteligente por AST (funciones y clases). El resto usa chunking por bloques de líneas con overlap.

---

## Troubleshooting

**El watcher no detecta cambios**
```bash
# Verificar que el proyecto está siendo vigilado
kortex status
# o
curl http://localhost:8080/watch/status
```

**Error de conexión a la API**
```bash
# Verificar que los contenedores están corriendo
docker compose ps
docker compose logs kortex-api --tail 50
```

**Ollama tarda en responder**
> Normal. `llama3.2` tarda 5-20s por request dependiendo del hardware. El timeout está configurado en 120s.

**El CLI no copia al portapapeles**
```bash
# Instalar xclip
sudo apt install xclip
```

**Re-indexar después de cambios grandes**
```bash
kortex index <project_id>
# o desde la UI: Proyectos → Re-index
```

---

## Licencia

MIT
