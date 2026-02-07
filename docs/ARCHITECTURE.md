# Architecture

## Overview

Yavin follows a modular, event-driven architecture designed for extensibility. The system is built around the concept of specialized agents that independently collect and manage domain-specific data, coordinated by an orchestrator agent.

---

## System Components

### 1. Frontend (Web UI)

**Technology**: React/Next.js or Vue.js (TBD)

**Responsibilities**:

- User authentication and session management
- Agent configuration interface
- Question/answer chat interface
- Dashboard visualization for each topic
- Agent management (add/remove/configure)

### 2. Backend API

**Technology**: Python FastAPI

**Responsibilities**:

- REST API for frontend communication
- WebSocket for real-time updates
- Authentication and authorization
- Agent lifecycle management
- Query routing to orchestrator

**Key Endpoints**:

```
POST /api/chat                 # Send question to orchestrator
GET  /api/agents               # List all agents
POST /api/agents               # Create new agent
GET  /api/agents/{id}/data     # Get agent's collected data
POST /api/agents/{id}/collect  # Trigger manual collection
GET  /api/dashboards/{topic}   # Get dashboard data
```

### 3. Task Scheduler

**Technology**: Celery + Redis

**Responsibilities**:

- Schedule periodic data collection tasks
- Manage task queues and priorities
- Handle retries and failure recovery
- Distribute work across workers

### 4. Message Queue

**Technology**: Redis

**Responsibilities**:

- Task queue for Celery
- Pub/sub for real-time events
- Caching frequently accessed data

### 5. Orchestrator Agent

**Technology**: LangGraph or custom Python

**Responsibilities**:

- Receive natural language queries from users
- Determine which specialized agents to consult
- Route queries to appropriate agents
- Aggregate and synthesize responses
- Maintain conversation context

**Decision Flow**:

```
User Query
    │
    ▼
┌─────────────────────┐
│ Intent Classification│
│ "What topic is this?"│
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  Agent Selection    │
│ "Which agents know  │
│  about this?"       │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  Query Agents       │
│ (parallel if needed)│
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  Synthesize Response│
│  "Combine insights" │
└─────────────────────┘
    │
    ▼
Response to User
```

### 6. Specialized Agents

**Technology**: Python classes with standard interface

**Each agent contains**:

- **Collectors**: Modules that fetch data from specific sources
- **Storage**: Interface to persist collected data
- **Query Handler**: LLM-powered responder for questions
- **Tools**: Functions the agent can use (database queries, calculations)

**Standard Agent Interface**:

```python
class BaseAgent(ABC):
    @abstractmethod
    def get_capabilities(self) -> AgentCapabilities:
        """Describe what this agent can do"""
        pass

    @abstractmethod
    async def collect(self) -> CollectionResult:
        """Run data collection"""
        pass

    @abstractmethod
    async def query(self, question: str, context: dict) -> AgentResponse:
        """Answer a question about this domain"""
        pass

    @abstractmethod
    def get_tools(self) -> list[Tool]:
        """Return tools available to this agent"""
        pass
```

### 7. Data Layer

#### PostgreSQL (Structured Data)

- Time-series data (economic indicators, statistics)
- Agent configurations
- Collection logs and metadata
- User data and preferences

**Key Tables**:

```sql
-- Agent registry
agents (id, name, agent_type, description, config, enabled, created_at, updated_at)

-- Collected data points (14,000+ records)
data_points (
  id, agent_id, metric_name, value, value_text,
  period,        -- e.g., "2025-09" for monthly data
  timestamp,     -- when collected
  source,        -- e.g., "ABS", "RBA"
  geography,     -- e.g., "Australia"
  unit,          -- e.g., "$", "%"
  extra_data,    -- JSON metadata
  created_at
)

-- Documents (RBA minutes, statements)
documents (
  id, agent_id, document_type, external_id,
  title, source_url, published_at,
  content,       -- Full document text
  summary,       -- LLM-generated summary
  extra_data,    -- e.g., {"cash_rate": 3.85, "decision": "unchanged"}
  collected_at, created_at, updated_at
)

-- Collection runs
collection_runs (id, agent_id, started_at, completed_at, status, records_collected, errors)

-- Document chunks (for future RAG)
document_chunks (id, document_id, chunk_index, content, char_start, char_end)
```

#### Vector Store (Embeddings)

**Technology**: pgvector (PostgreSQL extension) or Chroma

- Article embeddings for semantic search
- Query embeddings for retrieval
- Agent capability descriptions

---

## Data Flow

### Collection Flow

```
Scheduler triggers collection
         │
         ▼
    ┌─────────┐
    │ Celery  │
    │ Worker  │
    └─────────┘
         │
         ▼
┌─────────────────┐
│ Specialized     │
│ Agent.collect() │
└─────────────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌───────┐
│API/Web│ │ RSS   │
│Source │ │ Feed  │
└───────┘ └───────┘
    │         │
    └────┬────┘
         ▼
┌─────────────────┐
│ Validate &      │
│ Normalize       │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Store in        │
│ PostgreSQL      │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Generate        │
│ Embeddings      │
└─────────────────┘
```

### Query Flow

```
User asks question
         │
         ▼
┌─────────────────┐
│ Backend API     │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Orchestrator    │
│ Agent           │
└─────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ Housing Agent               │
│ (+ Future Agents)           │
└─────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ Synthesize      │
│ Response        │
└─────────────────┘
         │
         ▼
    User Response
```

---

## Technology Stack (Implemented)

| Component         | Technology       | Status | Notes                          |
| ----------------- | ---------------- | ------ | ------------------------------ |
| Language          | Python 3.11+     | ✅     | AI/ML ecosystem, async support |
| Package Manager   | uv               | ✅     | Fast, modern Python packaging  |
| CLI Framework     | Typer + Rich     | ✅     | Beautiful terminal interface   |
| Database          | PostgreSQL       | ✅     | Relational with JSON support   |
| ORM               | SQLAlchemy 2.0   | ✅     | Modern async patterns          |
| LLM Framework     | LangChain        | ✅     | Tool calling, agent patterns   |
| LLM Provider      | Anthropic Claude | ✅     | claude-sonnet-4-20250514       |
| Backend Framework | FastAPI          | ⏳     | Phase 2                        |
| Task Queue        | Celery + Redis   | ⏳     | Phase 2                        |
| Frontend          | Next.js          | ⏳     | Phase 3                        |
| Containerization  | Docker + Compose | ✅     | PostgreSQL only currently      |

---

## Directory Structure (Current)

```
yavin/
├── README.md
├── pyproject.toml             # Project config, dependencies
├── .env.example               # Environment template
├── docs/                      # Documentation
│   ├── REQUIREMENTS.md
│   ├── ARCHITECTURE.md
│   ├── AGENTS.md
│   ├── DATA_SOURCES.md
│   ├── ROADMAP.md
│   └── decisions/             # ADRs
│       ├── 001-agent-framework.md
│       └── 002-llm-provider.md
├── src/yavin/                 # Main package
│   ├── __init__.py
│   ├── cli.py                 # Typer CLI commands
│   ├── config.py              # Configuration management
│   ├── llm.py                 # LLM client setup
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py            # BaseAgent ABC
│   │   └── specialized/
│   │       ├── __init__.py
│   │       └── housing.py     # HousingAgent (11 tools)
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── base.py            # BaseCollector ABC
│   │   └── sources/
│   │       ├── __init__.py
│   │       ├── abs.py         # ABS SDMX API collector
│   │       └── rba.py         # RBA collectors (Excel, Minutes, Statements)
│   └── db/
│       ├── __init__.py
│       ├── models.py          # SQLAlchemy models
│       ├── repository.py      # Data access layer
│       └── session.py         # Database sessions
├── tests/
│   ├── __init__.py
│   ├── test_agents.py
│   └── test_collectors.py
└── docker/
    └── docker-compose.yml     # PostgreSQL service
```

---

## Security Considerations

1. **API Keys**: Stored in environment variables (`.env` file, not committed)
2. **Database**: Not exposed publicly, accessed only by backend
3. **SQL Injection Protection**:
   - `query_database` tool only allows SELECT queries
   - 30+ dangerous SQL keywords blocked (INSERT, UPDATE, DELETE, DROP, ALTER, etc.)
   - Multiple statements blocked (no semicolons except at end)
   - SQL comments blocked (prevents hiding malicious code)
   - 30-second query timeout
   - Maximum 500 rows returned
4. **Authentication**: JWT-based for API, session-based for web UI (Phase 2+)
5. **Rate Limiting**: Prevent abuse of LLM endpoints (Phase 2+)
6. **Input Validation**: Sanitize all user inputs

---

## Future Considerations

- **Multi-tenancy**: Support multiple users with isolated data
- **Agent Marketplace**: Share agent configurations
- **Local LLM Support**: Run without cloud LLM providers
- **Mobile App**: Push notifications for alerts
- **API Access**: Allow programmatic access to data
