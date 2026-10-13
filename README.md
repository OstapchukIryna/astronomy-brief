# AI Astronomy Daily Brief



[![CI](https://github.com/OstapchukIryna/astronomy-brief/actions/workflows/ci.yaml/badge.svg)](https://github.com/OstapchukIryna/astronomy-brief/actions/workflows/ci.yaml)
![Python](https://img.shields.io/badge/python-3.14-blue)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

An API that turns NASA's Astronomy Picture of the Day into a small learning brief: the pulled original image and explanation, a beginner-friendly rewrite by an LLM, key facts, and answers to your questions about the topic.

## Key Features

| Feature | Status |
|---|---|
| Health checks (liveness / readiness) | ✅ done |
| Fetch APOD with image metadata and original explanation | 🚧 planned |
| Beginner-friendly explanation (LLM) | 🚧 planned |
| 3–5 key facts about the topic | 🚧 planned |
| Ask questions about the topic | 🚧 planned |
| History of previous daily briefs | 🚧 planned |


## Tech stack

FastAPI · async SQLAlchemy · PostgreSQL · Pydantic · httpx · OpenAI API / Ollama · pytest · uv · GitHub Actions

## Getting started

### Prerequisites

- [uv](https://docs.astral.sh/uv/)
- Docker (for PostgreSQL)
- An OpenAI API key / a local [Ollama](https://ollama.com/) installation

### Setup

```bash
git clone https://github.com/OstapchukIryna/astronomy-brief.git
cd astronomy-brief
cp .env.example .env        # then fill in LLM_MODEL (and OPENAI_API_KEY if using OpenAI)
docker compose up -d        # starts PostgreSQL
uv sync                     # installs Python and dependencies
uv run uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for the interactive API documentation.

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness: the process is up |
| `GET` | `/health/ready` | Readiness: the database is reachable (or `503`) |


## Project structure

```
app/
├── api/routers/     # HTTP layer: request/response, status codes
├── services/        # use cases and transaction boundaries
├── repositories/    # database access
├── clients/         # external APIs (NASA, LLM providers)
├── models/          # SQLAlchemy models
├── schemas/         # Pydantic request/response schemas
├── prompts/         # LLM prompt templates
├── config.py        # settings from environment
├── database.py      # engine, sessions, DB dependency
└── main.py          # app factory and lifespan
tests/               # mirrors app/ structure
```
