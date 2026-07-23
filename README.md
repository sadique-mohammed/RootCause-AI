# RootCause AI

> AI-powered systems incident investigator — SSHes into broken Linux boxes and diagnoses root causes with cited evidence.

## Quick Start

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Install dev dependencies
uv sync --group dev

# Run the API server
uv run uvicorn backend.app.main:app --reload --port 8000

# Run tests
uv run pytest
```

## Architecture

```
User → [Next.js Frontend] → [FastAPI Backend] → [AI Reasoning Engine] → [Diagnostic Tools] → [SSH Runner] → [Target VM]
```

<!-- ## Documentation

See [`docs/`](./docs/) for full project documentation:
- [Product Requirements](./docs/01-product-requirements.md)
- [Technical Architecture](./docs/02-technical-architecture.md)
- [Phase Plan & Sprints](./docs/03-phase-plan.md)
- [Incident Catalog](./docs/04-incident-catalog.md)
- [Version Roadmap](./docs/05-version-roadmap.md)
- [AI Agent Design](./docs/06-ai-agent-design.md)
- [Anti-Scope & Decisions](./docs/07-anti-scope-and-decisions.md)
- [Learning Roadmap](./docs/08-learning-roadmap.md)
- [Competitive Analysis](./docs/09-competitive-analysis.md)
- [Tech Stack](./docs/10-tech-stack.md) -->

## Tech Stack

| Layer       | Technology                    |
| ----------- | ----------------------------- |
| Language    | Python 3.12+                  |
| Backend     | FastAPI + Pydantic v2         |
| ORM         | SQLModel                      |
| Database    | PostgreSQL 16                 |
| SSH         | Paramiko 5.x                  |
| AI (Cloud)  | OpenAI Responses API (GPT-4o) |
| AI (Local)  | Ollama (llama3.1:8b)          |
| AI Router   | LiteLLM                       |
| Packets     | Scapy 2.6+                    |
| Frontend    | Next.js 15 + Tailwind CSS v4  |
| Package Mgr | uv                            |
| Linting     | Ruff                          |
| Testing     | pytest + httpx                |

## License

MIT
