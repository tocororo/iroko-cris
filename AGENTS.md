# AGENTS.md

## Project Overview

**Iroko CRIS** is a Current Research Information System that uses PostgreSQL as the source of truth and a graph database (Memgraph / Neo4j) for relationship-heavy queries. It provides a REST API (FastAPI), an evaluation framework for research entities, and a task/crawler system for data enrichment.

**Tech stack:**
- Python 3.12+
- FastAPI (REST API)
- PostgreSQL (async via SQLAlchemy) – source of truth
- Neo4j / Memgraph – graph store
- Angular (frontend, in `iroko-ui/`)
- Docker / Podman (container orchestration)
- Nginx (reverse proxy, static serving)

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Angular   │────▶│   HAProxy   │────▶│   FastAPI   │
│   (UI)      │     │  (reverse)  │     │   (api)     │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                                 │
                                    ┌────────────┼────────────┐
                                    │            │            │
                               ┌────▼────┐   ┌───▼───┐   ┌────▼────┐
                               │PostgreSQL│   │Neo4j  │   │  Tasks  │
                               │(nodes,  │   │(graph)│   │(crawlers│
                               │ auth,   │   │       │   │ , sync) │
                               │ evals)  │   │       │   └─────────┘
                               └─────────┘   └───────┘
```

- **PostgreSQL** stores authoritative node data (`nodes` table), authentication, evaluation records.
- **Neo4j/Memgraph** stores the graph (nodes + relationships). Writes are atomic: NodeService updates both stores.
- **API** exposes REST endpoints under `/api/v1/` (authentication, Cypher queries, node CRUD, evaluations, crawler tasks).
- **Task System** (`iroko/tasks/`) – pluggable crawlers for MIAR, SciELO, ORCID, OJS, organizations, etc.
- **Evaluation Framework** – YAML-based methodologies with Python rules (see `methodologies/` and `iroko/evals/rules/`).

## Directory Structure (key paths)

```
iroko-cris/
├── iroko/                     # Main backend package
│   ├── main.py                # FastAPI app with lifespan
│   ├── config.py              # Pydantic settings (Neo4j, PG, JWT, CORS)
│   ├── database.py            # SQLAlchemy async engine + Base
│   ├── storage.py             # Neo4j driver wrapper
│   ├── auth/                  # JWT auth, roles, CAPTCHA
│   ├── cypher/                # Read-only Cypher queries + edit endpoints
│   ├── evals/                 # Evaluation engine (methodologies, rules)
│   ├── nodes/                 # Node CRUD and PG↔MG sync
│   ├── tasks/                 # Crawler manager and task implementations
│   ├── hd2neo4j/              # Legacy mapper (JSON → graph)
│   └── sync/                  # Background sync daemon (PG → MG)
├── iroko-ui/                  # Angular frontend (built static)
├── methodologies/             # YAML evaluation methodologies + questions
├── docs/schema/               # JSON schemas + mapping configs for entities
├── haproxy/                   # HAProxy config + self-signed SSL
├── initdb/                    # PG init scripts (extensions)
├── Dockerfile                 # Multi-stage API image
├── podman-compose.dev.yml    # Dev stack (Postgres, Memgraph, Lab)
├── podman-compose.prod.yml   # Prod stack (+ Neo4j, HAProxy, frontend)
├── rebuild.py                 # Script to drop all data and rebuild from seeds
├── entrypoint.sh              # Waits for PG/Neo4j, starts uvicorn
└── requirements.txt / pyproject.toml
```

## Core Modules & Responsibilities

| Module | Purpose |
|--------|---------|
| `auth` | JWT token generation/validation, user/role management, CAPTCHA protection. |
| `cypher` | Execute read-only Cypher queries, full‑text search, CSV export; also edit endpoints for node properties/relationships. |
| `nodes` | CRUD for nodes (stored in PG and synced to MG). Includes `NodeService` with merge methods and sync status. |
| `evals` | Load evaluation methodologies (YAML), execute rule‑based evaluation (questions → categories → sections → methodology). Rules are Python functions registered via decorators. |
| `tasks` | Async task manager with auto‑discovery. Tasks extend `CrawlerTask` and implement `execute()`. Examples: `MiarJournalsProcessingTask`, `OrcidMappingTask`, `OrganizationsProcessingTask`. |
| `hd2neo4j` | Legacy JSON‑to‑graph mapper (used during initial data loading). |
| `sync` | Daemon that periodically reconstructs Memgraph from PG nodes table. |

## Key Development Commands

### Local development (without containers)

```bash
# Install dependencies (recommended: use virtualenv with Python 3.12)
pip install -r requirements.txt

# Start PostgreSQL and Memgraph/Neo4j (e.g., via podman-compose.dev.yml)
podman-compose -f podman-compose.dev.yml up -d

# Run FastAPI with hot reload
uvicorn iroko.main:app --reload --host 0.0.0.0 --port 8000
```

### With Podman (production‑like)

```bash
podman-compose -f podman-compose.prod.yml build
podman-compose -f podman-compose.prod.yml up -d
```

### Database rebuild (seed data + crawlers)

```bash
python rebuild.py
```
This drops all data, recreates PG tables, imports bulk data (orgs, sources, persons, outputs) from `.data-init/`, and runs all enrichment tasks.

## Important Conventions

### 1. Node identity and storage
- Every node must have an `iroko_uuid` (UUID) and a `name`.
- Nodes are stored in PG `nodes` table (columns: `iroko_uuid`, `name`, `labels`, `data`, `relationships`, `updated_at`).
- The graph store mirrors the node with the same `iroko_uuid` and uses the `Node` label plus domain labels (e.g., `:Person`). Relationships are stored natively.
- **Write path:** Use `NodeService.merge_node()` / `merge_relationship()` – they update both PG and MG atomically.

### 2. Adding a new crawler task
1. Create a new class in `iroko/tasks/tasks/` extending `CrawlerTask`.
2. Implement `execute()` and `validate_config()`.
3. The task will be auto‑discovered if placed in that package.
4. Use `NodeService` for any graph writes.

### 3. Evaluation methodology
- Place YAML in `methodologies/methodology-*.yaml` and questions in `methodologies/questions.yaml`.
- For each `question` you can implement a rule in `iroko/evals/rules/` using `@rules_registry.register_question_rule('question_id')`.
- Category, section, and methodology rules are similarly registered.

### 4. Environment variables (see `config.py`)
- `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`
- `DATABASE_URL` (postgresql+asyncpg)
- `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- `CORS_ORIGINS` (list)
- `APP_ENV` (development/production)

## Testing

Currently there is no dedicated test suite. Manual testing is done via:
- Swagger UI (when `APP_ENV != production`) at `/api/docs`
- Running specific tasks with `tasks.py`
- Using `rebuild.py` to verify end‑to‑end import.

When adding features, ensure you test both PG and MG consistency.

## Contribution Guidelines (for AI agents)

- **Read the OpenAPI spec** (`openapi.json` / `openapi.yml`) to understand endpoints.
- **Model changes** require both SQLAlchemy (PG) and Cypher (MG) updates. Always use `NodeService` for writes.
- **When editing evaluation rules**, keep dependencies explicit (list of question IDs) and cacheable where possible.
- **Use `logging.getLogger('iroko-cris.<module>')`** – logs are captured by the central `logging_config.py`.
- **Never hardcode secrets** – use `app_settings` (pydantic-settings) and environment variables.
- **Database migrations** – not yet set up (tables are created via `init_db()`). If you alter models, modify `Base.metadata` accordingly.

## Troubleshooting

- **Neo4j connection refused** – check that `NEO4J_URI` is correct and the container is healthy.
- **Cypher write operations blocked** – the `/v1/cypher/query` endpoint enforces read‑only by default. Use edit endpoints or `NodeService` for writes.
- **Evaluation returns None** – missing rule implementation or dependencies not satisfied.

## Useful Files to Explore

| File | Why |
|------|-----|
| `iroko/main.py` | Lifespan, middleware, router includes. |
| `iroko/nodes/service.py` | Core sync logic (PG↔MG) and merge operations. |
| `iroko/evals/service.py` | Methodology loading and evaluation flow. |
| `iroko/tasks/manager.py` | Task registry, execution, status. |
| `rebuild.py` | Complete database rebuild pipeline (seed + tasks). |
| `methodologies/methodology-sceiba-v1.yaml` | Example evaluation for journals. |
| `podman-compose.prod.yml` | Production service definitions. |

---
