# PoC Workspace — Engineering Scripts, Local AI Infrastructure & Orchestration

A single, reproducible **proof-of-concept workspace** for the `c:\src` monorepo-style layout.
It bundles the shared Python library, local AI infrastructure (Ollama / Open WebUI), the
Firestore export & emulator toolchain, browser bookmark managers, PowerShell administration
utilities, multi-provider AI benchmark scripts, DSPy prompt-engineering services and a staged
LangChain agent archive — all driven from one **central orchestrator**: [`run.ps1`](run.ps1).

---

## Table of Contents

1. [Workspace Layout](#workspace-layout)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Central Orchestrator — `run.ps1`](#central-orchestrator--runps)
5. [Shared Python Library — `libs/py`](#shared-python-library--libspy)
6. [Docker Local AI Infrastructure — `docker/ai`](#docker-local-ai-infrastructure--dockerai)
7. [Firestore Export & Emulator Toolchain — `apps/firestore-export`](#firestore-export--emulator-toolchain--appsfirestore-export)
8. [Node.js Bookmark Managers — `script/node`](#nodejs-bookmark-managers--scriptnode)
9. [PowerShell Administration Scripts — `script/ps`](#powershell-administration-scripts--scriptps)
10. [AI Benchmarking & Diagnostics — `script/py`](#ai-benchmarking--diagnostics--scriptpy)
11. [DSPy Pipelines & Prompt Engineering — `script/py`](#dspy-pipelines--prompt-engineering--scriptpy)
12. [Developer Utilities — `script/py`](#developer-utilities--scriptpy)
13. [LangChain Agent Evolutionary Archive — `script/py/agents_archive`](#langchain-agent-evolutionary-archive--scriptpyagents_archive)
14. [Environment Variables](#environment-variables)
15. [Troubleshooting](#troubleshooting)

---

## Workspace Layout

```
c:\src
├── .venv\                          # Shared virtual environment (created by run.ps1 setup)
├── abyssium-studio\                # Vite/React front end (npm run dev/build/lint)
├── enterprise-rag-pgvector-rbac\   # FastAPI + Streamlit + FastMCP RAG stack
├── suntiq-product\                 # Product/monorepo project (docs, apps, packages)
└── poc\                            # ← this repository
    ├── run.ps1                     # Central Workspace Orchestrator (menu + CLI actions)
    ├── activate.ps1                # Activates the parent workspace .venv
    ├── ollama.ps1                  # One-line Ollama launcher (deepseek-r1:8b)
    ├── .gitignore                  # Secrets, venvs, build output, caches
    ├── libs\
    │   └── py\                     # Shared `py-libraries` package
    │       ├── setup.py
    │       ├── __init__.py
    │       └── utilities.py        # RBAC, embeddings, loaders, safe math, logging, …
    ├── docker\
    │   └── ai\
    │       ├── docker-compose-ollama.yml   # GPU Ollama + model-pull sidecar
    │       └── docker-compose-webui.yml    # Open WebUI against host Ollama
    ├── apps\
    │   └── firestore-export\       # Firestore export/import/emulator helpers (Node ESM)
    └── script\
        ├── node\                   # Chrome/Edge bookmark sorters
        ├── ps\                     # Administrative & cleanup PowerShell scripts
        └── py\                     # Benchmarks, DSPy services, dev utilities
            └── agents_archive\     # Staged LangChain agent evolution (01 → 06)
```

> **Workspace root detection:** `run.ps1` resolves the workspace root from its own location
> (the parent of `poc\`), falling back to the current directory and finally to `c:\src`.
> It is safe to launch from any folder: `.\poc\run.ps1 help`.

---

## Prerequisites

| Tool | Version | Needed for |
| --- | --- | --- |
| Windows PowerShell | 5.1+ (PowerShell 7+ recommended) | All `.ps1` scripts |
| Python | 3.11+ | `libs/py`, `script/py`, FastAPI/Streamlit |
| Node.js | 20+ | `script/node`, `apps/firestore-export`, Abyssium Studio |
| Docker Desktop | current | `docker/ai`, RAG Postgres/Jaeger |
| Ollama | current | Local model sessions and agent scripts |
| NVIDIA Container Toolkit | current | GPU acceleration in `docker-compose-ollama.yml` |

Python dependencies are installed into the shared `c:\src\.venv` by `run.ps1 setup` from
`enterprise-rag-pgvector-rbac\requirements.txt`. The `libs/py` package additionally declares
`numpy`, `psycopg2-binary`, `python-dotenv`, `langchain-core`, `langchain-community`,
`langchain-openai`, `langchain-text-splitters`.

Optional feature packages (install only what you use):

| Feature | Packages |
| --- | --- |
| `script/py/agents_archive/*` | `langchain-core`, `langchain-ollama` |
| `script/py/dspy_ollama.py`, `dspy_server.py` | `dspy`, `fastapi`, `uvicorn` |
| `script/py/nvidia-models.py` | `openai`, `python-dotenv` |
| `script/py/compress_pdf.py` | `PyMuPDF`, `pypdf` |
| `script/py/gmail_tools.py` | `langchain-community`, Google API client libraries |

The provider benchmark scripts also need `requests` and `python-dotenv`.


---

## Quick Start

```powershell
# 1. From the workspace root, create/refresh the environment
.\poc\run.ps1 setup

# 2. (Optional) show where the venv lives, then activate it in this shell
.\poc\run.ps1 activate
& C:\src\.venv\Scripts\Activate.ps1

# 3. Bring up the local data plane
.\poc\run.ps1 docker-up        # PostgreSQL 16 + pgvector, Jaeger

# 4. Start the RAG stack (separate terminals)
.\poc\run.ps1 api              # http://localhost:8000/docs
.\poc\run.ps1 ui               # http://localhost:8501
.\poc\run.ps1 mcp-ui           # FastMCP Inspector / Evaluate UI

# 5. Everything at a glance
.\poc\run.ps1 status
```

Running `.\poc\run.ps1` with **no arguments** opens the interactive numbered menu
(`0` = quit, `1`–`17` = actions below). Any action is also available as a direct
CLI parameter for scripting/CI.

---

## Central Orchestrator — `run.ps1`

`run.ps1` is the single entry point for the whole workspace. It detects the workspace root,
the shared `.venv` (`Python`/`pip`/`uvicorn`/`streamlit`), `fastmcp.exe`, and `mcp.exe`,
then dispatches one of the actions below.

### Interactive menu (`0`–`17`)

| # | Action | Category | Description |
| --- | --- | --- | --- |
| 0 | `quit` | — | Exit the menu |
| 1 | `status` / `st` | Diagnostics | Git status of workspace repos, Python/Node runtimes, port listeners (8000, 8501, 5173, 5432, 16686, 4317, 11434), `docker ps` |
| 2 | `api` | RAG stack | `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` |
| 3 | `ui` | RAG stack | `streamlit run streamlit_app.py --server.port 8501` |
| 4 | `mcp` | RAG stack | `python -m app.mcp` (FastMCP Gateway) |
| 5 | `mcp-ui` | RAG stack | FastMCP Inspector / Evaluate UI against `app/mcp/gateway.py:mcp` |
| 6 | `test` | RAG stack | `pytest -v` (extra args are forwarded, e.g. `-k rbac`) |
| 7 | `ingest` | RAG stack | `python scripts/ingest.py` with interactive path/role/`--force` prompts |
| 8 | `docker-up` / `db` | RAG stack | `docker compose up -d` (Postgres 16 + pgvector, Jaeger Badger) |
| 9 | `docker-down` | RAG stack | `docker compose down` |
| 10 | `studio` | Abyssium Studio | `npm run dev` (Vite, port 5173) |
| 11 | `build` | Abyssium Studio | `npm run build` |
| 12 | `lint` | Abyssium Studio | `npm run lint` |
| 13 | `ollama` | Local AI | `ollama run deepseek-r1:8b --verbose` |
| 14 | `activate` | Maintenance | Prints the exact `.venv` activation command |
| 15 | `clean` | Maintenance | Purges `node_modules`, `__pycache__`, `.pytest_cache`, Vite `dist` — **never** `.venv` |
| 16 | `setup` | Maintenance | Creates `.venv` if missing, upgrades pip, installs `requirements.txt`, `npm install` for Abyssium Studio |
| 17 | `help` | Maintenance | Formatted command reference |

### Direct CLI actions

```powershell
.\poc\run.ps1 status            # workspace health
.\poc\run.ps1 api               # FastAPI backend
.\poc\run.ps1 ui                # Streamlit frontend
.\poc\run.ps1 mcp               # FastMCP gateway
.\poc\run.ps1 mcp-ui            # inspector / evaluate UI (aliases: inspector, mcp-eval-ui)
.\poc\run.ps1 test -k rbac      # pytest with passthrough args
.\poc\run.ps1 ingest docs --force
.\poc\run.ps1 docker-up         # alias: db
.\poc\run.ps1 docker-down
.\poc\run.ps1 studio            # alias: web
.\poc\run.ps1 build
.\poc\run.ps1 lint
.\poc\run.ps1 ollama
.\poc\run.ps1 activate
.\poc\run.ps1 clean
.\poc\run.ps1 setup
.\poc\run.ps1 help
```

Companion launchers:

* [`activate.ps1`](activate.ps1) — activates `..\.venv\Scripts\Activate.ps1` with a clear
  error if the environment has not been created yet.
* [`ollama.ps1`](ollama.ps1) — one line: `ollama run deepseek-r1:8b --verbose`.

---

## Shared Python Library — `libs/py`

Import it either as an installed package (`pip install -e libs/py`) or by prepending
`libs\py` to `sys.path` (the scripts in this repo do the latter).

| Function | Purpose |
| --- | --- |
| `expand_user_roles(raw_roles)` | Expands RBAC hierarchy: `admin` → admin, executive, finance_analyst, engineering; `finance_lead` → finance_lead, finance_analyst |
| `truncate_and_normalize(embedding, target_dim=1536)` | Truncates an embedding and L2-normalises it for pgvector |
| `load_config(env_path=None)` | Finds the nearest `.env`, requires `OPENAI_API_KEY` + `DATABASE_URL` |
| `get_documents(file_paths)` | Loads `.pdf` (PyPDF) and `.md` (UnstructuredMarkdown) |
| `split_chunks(documents, chunk_size=2000, chunk_overlap=200)` | `RecursiveCharacterTextSplitter` chunking |
| `get_embedding_model(api_key)` | `OpenAIEmbeddings("text-embedding-3-large", dimensions=1536)` |
| `get_llm(api_key, model="gpt-4o", temperature=0.0)` | `ChatOpenAI` factory |
| `get_db_connection(database_url, timeout=30)` | psycopg2 connection with `connect_timeout` |
| `get_ollama_host` / `get_timeout_seconds` / `get_retry_attempts` | Env/CLI parsers for Ollama scripts |
| `log_error(stage, error)` | Structured stage + traceback logger |
| `safe_calculate(expression)` | AST-only math evaluator (`+ - * / **`, unary minus, parentheses) — no `eval` |
| `remove_comments_and_docstrings(filepath)` | Strips docstrings and `#` / `--` comments while keeping valid code lines |

`setup.py` packages this module as `py-libraries` v0.1.0.

---

## Docker Local AI Infrastructure — `docker/ai`

### `docker-compose-ollama.yml`

* `ollama` service — `ollama/ollama:latest`, GPU reservations via
  `deploy.resources.reservations.devices` (`driver: nvidia`, `capabilities: [gpu]`),
  `ipc: host`, port `11434:11434`, persistent volume `ollama:/root/.ollama`.
* Tuned environment: `OLLAMA_HOST=0.0.0.0`, `OLLAMA_KEEP_ALIVE=-1`,
  `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=1`,
  `OLLAMA_MAX_QUEUE=512`.
* Healthcheck (`ollama list`).
* `ollama-pull-model` sidecar — waits for the healthcheck, then pulls `llama3.1:8b`.

```powershell
docker compose -f .\docker\ai\docker-compose-ollama.yml up -d
```

### `docker-compose-webui.yml`

* `open-webui` (`ghcr.io/open-webui/open-webui:main`), port `3000:8080`,
  persistent `open-webui-data` volume.
* Talks to the host Ollama via `OLLAMA_BASE_URL=http://host.docker.internal:11434`
  and `extra_hosts: ["host.docker.internal:host-gateway"]`.

```powershell
docker compose -f .\docker\ai\docker-compose-webui.yml up -d   # http://localhost:3000
```

---

## Firestore Export & Emulator Toolchain — `apps/firestore-export`

Node.js **ES Module** project (`"type": "module"`, `firebase` v11+, `dotenv`).

| File | Role |
| --- | --- |
| [`firebaseSetup.js`](apps/firestore-export/firebaseSetup.js) | Environment-driven Firebase app + Firestore client, emulator support |
| [`exportFirestore.js`](apps/firestore-export/exportFirestore.js) | Exports collections (up to 10,000 docs) to JSON, Timestamps → ISO strings |
| [`importFirestore.js`](apps/firestore-export/importFirestore.js) | Imports JSON back into Firestore in batches |
| [`createNotification.js`](apps/firestore-export/createNotification.js) | Injects a test notification under `users/{uid}/notifications` |
| [`filterRequestsByUserDocumentReference.js`](apps/firestore-export/filterRequestsByUserDocumentReference.js) | Finds `requests` referencing a user `DocumentReference` and updates status |
| [`utils.js`](apps/firestore-export/utils.js) | Deep recursive Firestore Timestamp → ISO conversion |
| [`_start.ps1`](apps/firestore-export/_start.ps1) | firebase-tools setup, gcloud auth, GCS export sync, `firebase emulators:start --import … --export-on-exit` |

```powershell
cd .\apps\firestore-export
npm install
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\path\to\service_account.json"
node .\exportFirestore.js
```

---

## Node.js Bookmark Managers — `script/node`

* [`sortChromeBookmarks.js`](script/node/sortChromeBookmarks.js) — locates
  `%LOCALAPPDATA%\Google\Chrome\User Data\Default\Bookmarks` (macOS/Linux paths documented
  in-file), writes a `.backup` copy **before** touching anything, recursively walks
  `bookmark_bar`, `other` and `synced`, skips protected folders (`Chrome`, `MTC`, `ACER`),
  sorts folders then URLs alphabetically and appends skipped folders last, then rewrites the
  file with Chrome's 3-space indentation.
* [`sortEdgeBookmarks.js`](script/node/sortEdgeBookmarks.js) — same algorithm for Microsoft Edge
  profile data.

```powershell
cd .\script\node
npm run sort:chrome
npm run sort:edge
```

> Close the browser before sorting; both scripts abort safely if the Bookmarks file is absent.

---

## PowerShell Administration Scripts — `script/ps`

| Script | What it does |
| --- | --- |
| [`Get-ObsoleteFilesReport.ps1`](script/ps/Get-ObsoleteFilesReport.ps1) | Scans `C:`, `D:`, `E:` while excluding `Windows`, `Program Files`, `$Recycle.Bin`, `System Volume Information`; flags files older than 60/90 days, aggregates Bytes/MB/GB, exports `ObsoleteFilesReport.csv`. Supports `-WhatIf`. |
| [`_remove-node-modules.ps1`](script/ps/_remove-node-modules.ps1) | High-impact recursive `node_modules` purge with `SupportsShouldProcess` (`-WhatIf`, `-Confirm`). |
| [`_remove-git-files.ps1`](script/ps/_remove-git-files.ps1) | Recursively removes `.git` folders and `.git*` files from a target directory. |
| [`_rename_by_extension_sequential.ps1`](script/ps/_rename_by_extension_sequential.ps1) | Renames files to zero-padded sequential names per extension (`001.jpg`, `002.jpg`, …) using a collision-safe two-pass rename. |

```powershell
.\script\ps\Get-ObsoleteFilesReport.ps1 -Drives C: -WhatIf
.\script\ps\_remove-node-modules.ps1 -Path C:\work\project -WhatIf
.\script\ps\_remove-git-files.ps1 -Path C:\work\project -WhatIf
.\script\ps\_rename_by_extension_sequential.ps1 -Path C:\photos -WhatIf
```

---

## AI Benchmarking & Diagnostics — `script/py`

Run the full matrix or a single provider:

```powershell
python .\script\py\run-all-model-tests.py
python .\script\py\gemini-models.py
```

| Script | Provider / API | Behaviour |
| --- | --- | --- |
| [`run-all-model-tests.py`](script/py/run-all-model-tests.py) | orchestrator | Runs the provider scripts in sequence with `sys.executable`, reports pass/fail/skip |
| [`gemini-models.py`](script/py/gemini-models.py) | Google Generative Language `/v1beta/models` | Lists `generateContent` models, benchmarks latency with `ThreadPoolExecutor` |
| [`openai-models.py`](script/py/openai-models.py) | OpenAI | Lists models, benchmarks minimal chat completions |
| [`nvidia-models.py`](script/py/nvidia-models.py) | NVIDIA NIM (OpenAI-compatible) | Validates endpoint connectivity and model responses |
| [`openrouter-models.py`](script/py/openrouter-models.py) | OpenRouter | Lists (free) models, validates completions |
| [`serper-models.py`](script/py/serper-models.py) | Serper.dev | Validates Google Search API credentials and engine results |
| [`ollama-models.py`](script/py/ollama-models.py) | Local Ollama `/api/tags` | Verifies each pulled model generates a response, with timeout/retry env config |

---

## DSPy Pipelines & Prompt Engineering — `script/py`

* [`dspy_ollama.py`](script/py/dspy_ollama.py) — configures `dspy.LM` for a local Ollama model
  (`ollama/gemma4:e2b` by default, or the first available local model), defines the
  `VideoPromptGenerator` signature and runs `dspy.ChainOfThought`, printing reasoning and the
  final structured prompt (Subject → Style → Camera → Lighting).
* [`dspy_server.py`](script/py/dspy_server.py) — FastAPI wrapper exposing
  `POST /api/chat/optimize` with `ChatRequest(message)` →
  `ChatResponse(user_brief, rationale, optimized_prompt)`.

```powershell
python .\script\py\dspy_ollama.py
python .\script\py\dspy_server.py     # http://127.0.0.1:8000/docs
```

---

## Developer Utilities — `script/py`

| Script | Purpose |
| --- | --- |
| [`compress_pdf.py`](script/py/compress_pdf.py) | Dual-engine PDF shrinker: PyMuPDF (`fitz`) re-encodes images at target DPI/quality, `garbage=4` + deflate + clean; falls back to `pypdf`; reports original vs compressed sizes. |
| [`combine_files.py`](script/py/combine_files.py) | Concatenates markdown docs/codebases into structured bundles with headers. |
| [`check_all_py.py`](script/py/check_all_py.py) | Parallel syntax validation of every `.py` file (excludes `.venv`, `node_modules`, `__pycache__`) without executing code. |
| [`gmail_tools.py`](script/py/gmail_tools.py) | LangChain `GmailToolkit` wrapper: searches Gmail from the CLI using `credentials.json` / `token.json`. |
| [`list-pip-packages.py`](script/py/list-pip-packages.py) | Lists installed packages and versions via `pip list --format=json`. |

---

## LangChain Agent Evolutionary Archive — `script/py/agents_archive`

A teaching sequence where each file adds exactly one capability:

| Stage | File | Capability |
| --- | --- | --- |
| 1 | [`agent-01.py`](script/py/agents_archive/agent-01.py) | Basic single-turn chat: `ChatPromptTemplate \| OllamaLLM \| StrOutputParser` |
| 2 | [`agent-02.py`](script/py/agents_archive/agent-02.py) | Prompt formatting + conversational memory |
| 3 | [`agent-03.py`](script/py/agents_archive/agent-03.py) | Dynamic tool invocation (calculator + search) |
| 4 | [`agent-04.py`](script/py/agents_archive/agent-04.py) | Structured JSON output parsing |
| 5 | [`agent-05.py`](script/py/agents_archive/agent-05.py) | Multi-turn conversation with scratchpad reasoning |
| 6 | [`agent-06.py`](script/py/agents_archive/agent-06.py) | Multi-agent / supervisor collaboration |
| — | [`all-agents.py`](script/py/agents_archive/all-agents.py) | Runs 01 → 06 sequentially in subprocesses and summarises results |

All agents read `AGENT_MODEL` (default `gemma4:e2b`) and require a running Ollama instance
(`ollama serve` / `docker compose -f docker/ai/docker-compose-ollama.yml up -d`).

```powershell
python .\script\py\agents_archive\all-agents.py
```

---

## Environment Variables

Create a `.env` at the workspace root (`c:\src\.env`) and/or in the project you run.
`.env`, `credentials.json`, `token.json` and `service_account.json` are git-ignored.

| Variable | Used by | Notes |
| --- | --- | --- |
| `OPENAI_API_KEY`, `DATABASE_URL` | `libs/py`, RAG stack | Required by `load_config()` |
| `GOOGLE_API_KEY` | `gemini-models.py` | Google Generative Language API key |
| `OPENROUTER_API_KEY` | `openrouter-models.py` | OpenRouter key |
| `NVIDIA_API_KEY` | `nvidia-models.py` | NVIDIA NIM key |
| `SERPER_API_KEY` | `serper-models.py` | Serper.dev key |
| `OLLAMA_HOST` | Ollama scripts, DSPy | Default `http://localhost:11434` |
| `OLLAMA_TIMEOUT_SECONDS`, `OLLAMA_RETRY_ATTEMPTS` | `ollama-models.py` | Timeout / retry tuning |
| `AGENT_MODEL` | `agents_archive/*` | Default `gemma4:e2b` |
| `DSPY_OLLAMA_MODEL`, `OLLAMA_HOST` | `dspy_ollama.py`, `dspy_server.py` | Model + endpoint |
| `FIREBASE_*` | `apps/firestore-export` | Web app config (apiKey, authDomain, projectId, …) |
| `USE_EMULATOR`, `FIRESTORE_EMULATOR_HOST` | `apps/firestore-export` | Point the SDK at the local emulator (`127.0.0.1:8080`) |
| `GMAIL_TOKEN_PATH`, `GMAIL_CREDENTIALS_PATH` | `gmail_tools.py` | OAuth files (default `token.json`, `credentials.json`) |

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `run.ps1` reports `Python (.venv) : NOT FOUND` | Run `.\run.ps1 setup`, or create `c:\src\.venv` with `python -m venv c:\src\.venv`. |
| `activate.ps1` fails: "Virtual environment not found" | Same as above; the script looks for `..\.venv\Scripts\Activate.ps1`. |
| Port shows `STOPPED` but the service is running | `status` uses `Get-NetTCPConnection -State Listen`; another process may own a different port or bind IPv6 only. |
| `docker ps` shows nothing after `docker-up` | Ensure Docker Desktop is running and you are in `enterprise-rag-pgvector-rbac` (compose file lives there). |
| `mcp-ui` cannot start the inspector | Install `fastmcp`/`mcp` into the venv (`pip install fastmcp`), or allow `npx @modelcontextprotocol/inspector` to download. |
| Ollama model missing in agent scripts | `ollama pull gemma4:e2b` (or set `AGENT_MODEL` to a pulled model: `ollama list`). |
| `check_all_py.py` reports INVALID on valid files | Permission issue writing `__pycache__`; it falls back to an in-memory compile check. |
| `sort*Bookmarks.js` cannot read the file | Close the browser; confirm the profile path (Chrome/Edge may use `Profile 1` instead of `Default`). |
