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

✅ **Phase 1: Foundation** - Complete

- Housing Agent fully operational with 11 tools
- Data collection from ABS, RBA (Excel, Minutes, Statements)
- 14,000+ data points across 31 metrics
- Interactive CLI with chat and data commands
- PostgreSQL storage with full history

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
# Edit .env to add ANTHROPIC_API_KEY

# Start database services
cd docker && docker compose up -d && cd ..

# Run the CLI
uv run yavin --help

# Collect data from all sources
uv run yavin collect          # Collect from all sources
uv run yavin collect abs       # ABS only (building approvals, labour, earnings)
uv run yavin collect rba       # RBA only (rates, inflation, minutes, statements)

# Interactive chat
uv run yavin chat              # Start interactive chat
uv run yavin chat "What is the current cash rate?"  # Single question

# View collected data
uv run yavin data metrics      # List all metrics
uv run yavin data latest       # Show latest values
uv run yavin data series interest_rate_cash  # View time series
```

## Example Questions

```bash
# Interest rates and monetary policy
uv run yavin chat "What is the current RBA cash rate?"
uv run yavin chat "What were the key points from the latest RBA meeting?"

# Housing affordability
uv run yavin chat "What is the housing affordability for first home buyers?"
uv run yavin chat "How has the average loan size changed over time?"

# Economic trends
uv run yavin chat "What has happened to building approvals in 2024?"
uv run yavin chat "Compare unemployment rate and inflation over the last 2 years"
```

## Documentation

- [Requirements](docs/REQUIREMENTS.md) - Functional and non-functional requirements
- [Architecture](docs/ARCHITECTURE.md) - System design and technical decisions
- [Agents](docs/AGENTS.md) - Agent specifications and capabilities
- [Roadmap](docs/ROADMAP.md) - Development phases and milestones
- [Data Sources](docs/DATA_SOURCES.md) - Available data sources and APIs

## License

MIT
