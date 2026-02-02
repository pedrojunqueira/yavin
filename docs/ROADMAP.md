# Development Roadmap

## Overview

This roadmap outlines the phased development approach for Yavin. The goal is to start small with a working end-to-end system, then expand capabilities incrementally.

---

## Phase 1: Foundation (MVP) 🚧

**Duration**: 4-6 weeks  
**Goal**: One working agent (Housing) with CLI interface

### Milestones

#### 1.1 Project Setup ⬜

- [ ] Initialize Python project with pyproject.toml
- [ ] Set up development environment (uv)
- [ ] Configure linting and formatting (ruff)
- [ ] Set up pre-commit hooks
- [ ] Create basic Docker Compose for PostgreSQL
- [ ] Initialize database schema

#### 1.2 Base Agent Framework ⬜

- [ ] Implement `BaseAgent` abstract class
- [ ] Implement `BaseCollector` abstract class
- [ ] Create agent registry system
- [ ] Set up configuration management
- [ ] Implement basic logging

#### 1.3 Housing Agent - Data Collection ⬜

- [ ] Implement ABS API collector (building approvals)
- [ ] Implement RBA API collector (interest rates, lending)
- [ ] Create data normalization pipeline
- [ ] Store data in PostgreSQL with timestamps
- [ ] Write tests for collectors

#### 1.4 Housing Agent - Query Capability ⬜

- [ ] Set up LLM integration (OpenAI/Anthropic)
- [ ] Implement agent tools (get_timeseries, get_latest, etc.)
- [ ] Create query handler with tool calling
- [ ] Test query responses

#### 1.5 CLI Interface ⬜

- [ ] Create simple CLI for asking questions
- [ ] Add commands for manual data collection
- [ ] Add commands to view collected data
- [ ] Basic formatting for responses

### Deliverables

- ✅ Working Housing Agent that collects real data
- ✅ CLI to ask questions about housing data
- ✅ Data persisted in PostgreSQL
- ✅ Documentation updated

---

## Phase 2: Backend & Scheduling ⬜

**Duration**: 3-4 weeks  
**Goal**: Automated collection, REST API, second agent

### Milestones

#### 2.1 Task Scheduling ⬜

- [ ] Set up Celery with Redis
- [ ] Create scheduled tasks for data collection
- [ ] Implement retry logic for failed collections
- [ ] Add collection status monitoring

#### 2.2 REST API ⬜

- [ ] Set up FastAPI application
- [ ] Implement agent listing endpoints
- [ ] Implement chat/query endpoint
- [ ] Implement data retrieval endpoints
- [ ] Add OpenAPI documentation

#### 2.3 Orchestrator Agent ⬜

- [ ] Implement query routing logic
- [ ] Create agent capability matching
- [ ] Implement response synthesis
- [ ] Add conversation context (optional)

#### 2.4 Prepare for Future Agents ⬜

- [ ] Document process for adding new agents
- [ ] Create agent scaffolding/template script
- [ ] Test orchestrator with single agent
- [ ] Plan next specialized agent based on needs

### Deliverables

- ✅ Automated hourly/daily data collection
- ✅ REST API for all operations
- ✅ Orchestrator ready for multiple agents
- ✅ Framework ready for future specialized agents

---

## Phase 3: Web Interface ⬜

**Duration**: 4-5 weeks  
**Goal**: Full web UI for interacting with the system

### Milestones

#### 3.1 Frontend Setup ⬜

- [ ] Initialize Next.js project
- [ ] Set up Tailwind CSS
- [ ] Create component library
- [ ] Implement API client

#### 3.2 Chat Interface ⬜

- [ ] Build chat UI component
- [ ] Implement message streaming
- [ ] Add source citations
- [ ] Show agent attribution

#### 3.3 Agent Management ⬜

- [ ] Agent listing page
- [ ] Agent detail/status page
- [ ] Enable/disable agents
- [ ] View collection history

#### 3.4 Dashboards ⬜

- [ ] Create dashboard framework
- [ ] Implement charts (Chart.js/Recharts)
- [ ] Housing dashboard with key metrics
- [ ] Historical trend visualization

### Deliverables

- ✅ Functional web interface
- ✅ Chat with agents
- ✅ View and manage agents
- ✅ Visual dashboards

---

## Phase 4: Polish & Expand ⬜

**Duration**: Ongoing  
**Goal**: Add more agents, improve UX, production readiness

### Milestones

#### 4.1 Additional Agents ⬜

- [ ] Identify next high-value agent based on usage
- [ ] Implement additional specialized agents as needed
- [ ] Custom agent creation flow

#### 4.2 Enhanced Features ⬜

- [ ] Alerts and notifications
- [ ] Saved queries
- [ ] Comparative analysis
- [ ] Export data (CSV, PDF reports)

#### 4.3 Production Readiness ⬜

- [ ] Authentication system
- [ ] Rate limiting
- [ ] Error tracking (Sentry)
- [ ] Performance monitoring
- [ ] Backup strategy

### Deliverables

- ✅ Multiple working agents as needed
- ✅ Alert system
- ✅ Production-ready deployment

---

## Success Metrics

### Phase 1 Success

- Can ask "How have housing approvals changed this year?" and get accurate answer
- Data collection runs successfully
- All data persisted correctly

### Phase 2 Success

- System runs unattended for 1 week
- Housing agent fully automated
- API responds in < 3 seconds

### Phase 3 Success

- Web UI fully functional
- Non-technical users can use the system
- Dashboards show meaningful trends

### Phase 4 Success

- System monitors multiple domains as needed
- Alerts work reliably
- System stable for 1 month

---

## Technical Debt & Improvements

Track items to revisit:

| Item | Phase | Priority | Notes |
| ---- | ----- | -------- | ----- |
|      |       |          |       |

---

## Ideas Backlog

Future ideas to evaluate:

- [ ] Mobile app for alerts
- [ ] Email digest summaries
- [ ] Comparison with historical events
- [ ] Prediction capabilities
- [ ] Social media monitoring
- [ ] Podcast/video transcript analysis
- [ ] Multi-language support
- [ ] Share insights publicly
- [ ] Integration with other tools (Notion, Obsidian)

---

## Timeline Summary

```
Phase 1 (MVP)           Phase 2              Phase 3            Phase 4
──────────────────────────────────────────────────────────────────────────►
│                       │                    │                  │
│ Housing Agent         │ Scheduling         │ Web UI           │ Future Agents
│ CLI Interface         │ REST API           │ Dashboards       │ Production
│ PostgreSQL            │ Orchestrator       │ Management       │
│                       │                    │                  │
Week 1-6                Week 7-10            Week 11-16         Ongoing
```
