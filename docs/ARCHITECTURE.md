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
agents (id, name, type, config, enabled, created_at)

-- Collected data points
data_points (id, agent_id, metric_name, value, timestamp, source, metadata)

-- Collection runs
collection_runs (id, agent_id, started_at, completed_at, status, records_collected)

-- Media articles
articles (id, agent_id, title, content, url, published_at, source, sentiment)
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

## Technology Stack

| Component         | Technology            | Rationale                      |
| ----------------- | --------------------- | ------------------------------ |
| Language          | Python 3.11+          | AI/ML ecosystem, async support |
| Backend Framework | FastAPI               | Modern, async, auto-docs       |
| Task Queue        | Celery + Redis        | Mature, reliable scheduling    |
| Database          | PostgreSQL + pgvector | Relational + vector in one     |
| LLM Framework     | LangChain/LangGraph   | Agent orchestration patterns   |
| LLM Provider      | OpenAI / Anthropic    | TBD based on cost/quality      |
| Frontend          | Next.js               | React ecosystem, SSR           |
| Containerization  | Docker + Compose      | Reproducible deployment        |
| Monitoring        | Prometheus + Grafana  | Optional, for production       |

---

## Directory Structure

```
yavin/
├── README.md
├── docs/                      # Documentation
│   ├── REQUIREMENTS.md
│   ├── ARCHITECTURE.md
│   ├── AGENTS.md
│   ├── ROADMAP.md
│   └── decisions/            # ADRs
├── src/
│   ├── yavin/                # Main package
│   │   ├── __init__.py
│   │   ├── config.py         # Configuration management
│   │   ├── api/              # FastAPI routes
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── routes/
│   │   │   └── dependencies.py
│   │   ├── agents/           # Agent implementations
│   │   │   ├── __init__.py
│   │   │   ├── base.py       # Base agent class
│   │   │   ├── orchestrator.py
│   │   │   └── specialized/
│   │   │       ├── __init__.py
│   │   │       └── housing.py
│   │   ├── collectors/       # Data collection modules
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   └── sources/
│   │   ├── db/               # Database models and access
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   └── repository.py
│   │   ├── workers/          # Celery tasks
│   │   │   ├── __init__.py
│   │   │   └── tasks.py
│   │   └── utils/
│   └── tests/
├── frontend/                  # Web UI (Phase 3)
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── scripts/                   # Utility scripts
├── pyproject.toml
└── .env.example
```

---

## Security Considerations

1. **API Keys**: Stored in environment variables or secrets manager
2. **Database**: Not exposed publicly, accessed only by backend
3. **Authentication**: JWT-based for API, session-based for web UI
4. **Rate Limiting**: Prevent abuse of LLM endpoints
5. **Input Validation**: Sanitize all user inputs

---

## Future Considerations

- **Multi-tenancy**: Support multiple users with isolated data
- **Agent Marketplace**: Share agent configurations
- **Local LLM Support**: Run without cloud LLM providers
- **Mobile App**: Push notifications for alerts
- **API Access**: Allow programmatic access to data
