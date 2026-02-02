# Yavin - Multi-Agent Trend Monitor

> _"Keeping track of the stories that matter, even when the media moves on."_

## Overview

Yavin is a multi-agent system designed to monitor trends and topics that often disappear from mainstream media attention. By collecting and storing data from various sources, Yavin helps users maintain visibility into ongoing issues even after they fade from public discourse.

## The Problem

Media agenda shifts constantly. Important topics like housing affordability, economic indicators, or geopolitical conflicts get heavy coverage, then suddenly disappear—not because they're resolved, but because something else captured attention. Yavin solves this by:

1. **Continuous Monitoring** - Specialized agents collect data on specific topics periodically
2. **Historical Context** - All data is stored for trend analysis over time
3. **Intelligent Querying** - A general agent can query across all specialized agents to provide insights
4. **Expandable** - Easy to add new specialized agents for emerging topics

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Web UI)                       │
│         Configure agents, view dashboards, ask questions     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Backend API (FastAPI)                    │
│              REST API, WebSocket, Authentication             │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Orchestrator   │  │  Task Scheduler │  │  Message Queue  │
│     Agent       │  │    (Celery)     │  │    (Redis)      │
└─────────────────┘  └─────────────────┘  └─────────────────┘
          │                   │
          ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    Specialized Agents                        │
│  ┌──────────┐  ┌─────────────────────────────────────────┐  │
│  │ Housing  │  │     Future Specialized Agents           │  │
│  │  Agent   │  │          (Coming Soon)                  │  │
│  └──────────┘  └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │   PostgreSQL     │  │   Vector Store   │                 │
│  │ (Structured Data)│  │  (Embeddings)    │                 │
│  └──────────────────┘  └──────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

## Project Status

🚧 **Phase 1: Foundation** - In Progress

See [ROADMAP.md](docs/ROADMAP.md) for detailed development phases.

## Quick Start

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
cd yavin
uv sync

# Copy environment file and add your API keys
cp .env.example .env

# Start database services
cd docker && docker compose up -d && cd ..

# Run the CLI
uv run yavin --help

# Test the ABS collector
uv run yavin test-abs
```

## Documentation

- [Requirements](docs/REQUIREMENTS.md) - Functional and non-functional requirements
- [Architecture](docs/ARCHITECTURE.md) - System design and technical decisions
- [Agents](docs/AGENTS.md) - Agent specifications and capabilities
- [Roadmap](docs/ROADMAP.md) - Development phases and milestones
- [Data Sources](docs/DATA_SOURCES.md) - Available data sources and APIs

## License

MIT
