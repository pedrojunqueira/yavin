# Requirements

## Vision Statement

Build a system that maintains continuous visibility into important trends and topics that fade from mainstream media attention, enabling users to track long-term developments regardless of current news cycles.

---

## Functional Requirements

### FR-1: Data Collection

| ID     | Requirement                                                                          | Priority | Status  |
| ------ | ------------------------------------------------------------------------------------ | -------- | ------- |
| FR-1.1 | System shall collect data from multiple source types (APIs, web scraping, RSS feeds) | High     | Planned |
| FR-1.2 | System shall schedule data collection at configurable intervals                      | High     | Planned |
| FR-1.3 | System shall store raw data with timestamps and source metadata                      | High     | Planned |
| FR-1.4 | System shall handle rate limiting and retry failed collections                       | Medium   | Planned |
| FR-1.5 | System shall validate and normalize collected data                                   | Medium   | Planned |

### FR-2: Specialized Agents

| ID     | Requirement                                                              | Priority | Status  |
| ------ | ------------------------------------------------------------------------ | -------- | ------- |
| FR-2.1 | Each agent shall focus on a specific domain (housing, commodities, etc.) | High     | Planned |
| FR-2.2 | Agents shall be configurable via UI or configuration files               | High     | Planned |
| FR-2.3 | Agents shall expose a standard interface for querying their data         | High     | Planned |
| FR-2.4 | Agents shall provide natural language responses about their domain       | High     | Planned |
| FR-2.5 | New agents shall be addable without system restart                       | Medium   | Planned |

### FR-3: Orchestrator Agent

| ID     | Requirement                                                          | Priority | Status  |
| ------ | -------------------------------------------------------------------- | -------- | ------- |
| FR-3.1 | Orchestrator shall route questions to appropriate specialized agents | High     | Planned |
| FR-3.2 | Orchestrator shall aggregate responses from multiple agents          | High     | Planned |
| FR-3.3 | Orchestrator shall maintain conversation context                     | Medium   | Planned |
| FR-3.4 | Orchestrator shall provide cross-domain insights                     | Medium   | Planned |

### FR-4: User Interface

| ID     | Requirement                                                  | Priority | Status  |
| ------ | ------------------------------------------------------------ | -------- | ------- |
| FR-4.1 | Users shall be able to ask natural language questions        | High     | Planned |
| FR-4.2 | Users shall be able to view dashboards for each topic        | Medium   | Planned |
| FR-4.3 | Users shall be able to configure agent parameters            | Medium   | Planned |
| FR-4.4 | Users shall be able to add/remove/enable/disable agents      | Medium   | Planned |
| FR-4.5 | Users shall be able to set up alerts for specific conditions | Low      | Planned |

### FR-5: Data Storage & Retrieval

| ID     | Requirement                                                      | Priority | Status  |
| ------ | ---------------------------------------------------------------- | -------- | ------- |
| FR-5.1 | System shall store structured data in relational database        | High     | Planned |
| FR-5.2 | System shall store text data with embeddings for semantic search | High     | Planned |
| FR-5.3 | System shall support time-series queries for trend analysis      | High     | Planned |
| FR-5.4 | System shall retain historical data indefinitely (configurable)  | Medium   | Planned |

---

## Non-Functional Requirements

### NFR-1: Performance

| ID      | Requirement                | Target                         |
| ------- | -------------------------- | ------------------------------ |
| NFR-1.1 | Query response time        | < 5 seconds for simple queries |
| NFR-1.2 | Data collection throughput | Support 100+ data sources      |
| NFR-1.3 | Concurrent users           | Support 10 concurrent users    |

### NFR-2: Reliability

| ID      | Requirement                    | Target                              |
| ------- | ------------------------------ | ----------------------------------- |
| NFR-2.1 | System uptime                  | 99% (non-critical personal project) |
| NFR-2.2 | Data collection success rate   | > 95%                               |
| NFR-2.3 | No data loss on system restart | Required                            |

### NFR-3: Scalability

| ID      | Requirement                    | Notes           |
| ------- | ------------------------------ | --------------- |
| NFR-3.1 | Horizontal scaling of agents   | Nice to have    |
| NFR-3.2 | Support 50+ specialized agents | Target for v2.0 |

### NFR-4: Security

| ID      | Requirement                            | Priority |
| ------- | -------------------------------------- | -------- |
| NFR-4.1 | API keys stored securely (not in code) | High     |
| NFR-4.2 | Authentication for web interface       | Medium   |
| NFR-4.3 | Rate limiting on API endpoints         | Medium   |

### NFR-5: Maintainability

| ID      | Requirement                | Notes                     |
| ------- | -------------------------- | ------------------------- |
| NFR-5.1 | Modular agent architecture | Easy to add new agents    |
| NFR-5.2 | Comprehensive logging      | For debugging             |
| NFR-5.3 | Docker-based deployment    | Reproducible environments |

---

## User Stories

### Epic: Housing Market Monitoring (First Agent)

```
As a user interested in the Australian housing market,
I want to track key indicators over time,
So that I can understand trends even when media coverage fades.
```

#### Stories:

1. **US-1.1**: As a user, I want the system to collect housing starts data monthly, so I can track new construction trends.

2. **US-1.2**: As a user, I want the system to collect mortgage/housing loan balances, so I can track lending trends.

3. **US-1.3**: As a user, I want the system to track interest rate changes, so I can correlate with housing activity.

4. **US-1.4**: As a user, I want the system to monitor property listing volumes, so I can track market supply.

5. **US-1.5**: As a user, I want the system to track immigration numbers, so I can correlate with housing demand.

6. **US-1.6**: As a user, I want to ask questions like "What's happened to housing starts since 2023?" and get a coherent answer.

7. **US-1.7**: As a user, I want to see a dashboard showing all housing indicators over time.

---

## Data Requirements for Housing Agent (Phase 1)

| Data Point               | Source Type         | Update Frequency | Notes                 |
| ------------------------ | ------------------- | ---------------- | --------------------- |
| Housing starts/approvals | ABS API             | Monthly          | Official statistics   |
| Housing loan balances    | RBA API             | Monthly          | Central bank data     |
| Interest rates           | RBA API             | As changed       | Cash rate decisions   |
| Property listings count  | Domain/REA scraping | Weekly           | May need alternative  |
| Median house prices      | CoreLogic / Domain  | Monthly          | May need paid API     |
| Immigration numbers      | ABS API             | Quarterly        | Population statistics |
| Housing news articles    | News APIs / RSS     | Daily            | Sentiment tracking    |

---

## Open Questions

- [ ] Which LLM provider to use? (OpenAI, Anthropic, local models?)
- [ ] Self-hosted vs cloud database?
- [ ] How to handle paywalled data sources?
- [ ] What's the MVP for "asking questions" - CLI or web UI first?
