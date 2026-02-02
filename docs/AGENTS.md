# Agent Specifications

## Overview

This document describes the specialized agents in the Yavin system. Each agent is responsible for monitoring a specific domain, collecting relevant data, and answering questions about that domain.

---

## Agent Architecture

### Base Agent Structure

Every specialized agent inherits from `BaseAgent` and implements:

```python
class BaseAgent(ABC):
    """Base class for all specialized agents"""

    name: str                    # Human-readable name
    description: str             # What this agent monitors
    domain_keywords: list[str]   # Keywords for routing queries

    @abstractmethod
    def get_capabilities(self) -> AgentCapabilities:
        """Return agent's capabilities and data sources"""

    @abstractmethod
    async def collect(self) -> CollectionResult:
        """Execute data collection from all sources"""

    @abstractmethod
    async def query(self, question: str, context: dict) -> AgentResponse:
        """Answer questions using collected data"""

    @abstractmethod
    def get_tools(self) -> list[Tool]:
        """Return LLM tools for this agent"""
```

### Agent Capabilities

```python
@dataclass
class AgentCapabilities:
    name: str
    description: str
    data_sources: list[DataSource]
    metrics_tracked: list[str]
    geographic_scope: str
    update_frequency: str
    example_questions: list[str]
```

---

## Specialized Agents

### 1. Housing Agent (Phase 1 - MVP)

**Purpose**: Monitor the Australian housing market and related economic indicators.

**Domain Keywords**: `housing`, `property`, `real estate`, `mortgage`, `home loan`, `dwelling`, `apartment`, `house prices`, `rent`, `rental`

#### Data Sources

| Source                 | Type     | Frequency  | Data Points                          |
| ---------------------- | -------- | ---------- | ------------------------------------ |
| ABS Building Approvals | API      | Monthly    | Dwelling approvals by type and state |
| RBA Housing Lending    | API      | Monthly    | Housing credit growth, loan balances |
| RBA Interest Rates     | API      | As changed | Cash rate, mortgage rates            |
| ABS Migration Data     | API      | Quarterly  | Net overseas migration               |
| Domain/REA Listings    | Scraping | Weekly     | Number of active listings            |
| News Articles          | RSS/API  | Daily      | Housing-related news coverage        |

#### Metrics Tracked

- `housing_approvals_total` - Total dwelling approvals
- `housing_approvals_houses` - House approvals
- `housing_approvals_apartments` - Apartment approvals
- `housing_credit_growth` - Year-on-year credit growth
- `housing_loan_balance_total` - Total outstanding mortgages
- `interest_rate_cash` - RBA cash rate
- `interest_rate_mortgage_avg` - Average mortgage rate
- `net_migration_quarterly` - Net overseas migration
- `listings_count_sydney` - Active listings in Sydney
- `listings_count_melbourne` - Active listings in Melbourne
- `news_article_count` - Number of housing articles (daily)
- `news_sentiment_avg` - Average sentiment of coverage

#### Example Questions

1. "How have housing approvals changed over the last 12 months?"
2. "What's the current interest rate and how has it affected mortgage lending?"
3. "Is housing still getting media attention? How does current coverage compare to 6 months ago?"
4. "How does immigration correlate with housing demand?"
5. "Give me a summary of what's happened in Australian housing since January 2024"

#### Tools

```python
tools = [
    get_metric_timeseries(metric_name, start_date, end_date),
    get_latest_value(metric_name),
    compare_periods(metric_name, period1, period2),
    search_articles(query, date_range),
    get_media_coverage_trend(date_range),
]
```

---

### Future Specialized Agents

Once the Housing Agent is complete and stable, additional specialized agents can be created following the same patterns. Potential future agents could monitor:

- Commodity markets and producers
- Geopolitical conflicts and tensions
- Economic indicators
- Climate and energy trends
- Other topics of interest

See the "Adding a New Agent" section below for how to create new agents.

---

## Orchestrator Agent

**Purpose**: Route user queries to appropriate specialized agents and synthesize responses.

### Routing Logic

```python
async def route_query(self, question: str) -> list[Agent]:
    """Determine which agents should handle this query"""

    # 1. Extract keywords and intent
    analysis = await self.llm.analyze_query(question)

    # 2. Match against agent domain keywords
    matching_agents = []
    for agent in self.agents:
        relevance = calculate_relevance(analysis, agent.domain_keywords)
        if relevance > THRESHOLD:
            matching_agents.append((agent, relevance))

    # 3. Sort by relevance and return top matches
    return sorted(matching_agents, key=lambda x: x[1], reverse=True)
```

### Multi-Agent Queries

When a question spans multiple domains:

1. Route to all relevant agents in parallel
2. Collect responses from each
3. Use LLM to synthesize a coherent answer
4. Cite which agent provided which information

### Example Multi-Agent Query

Once multiple agents are available, the orchestrator can handle cross-domain queries:

**User**: "How might rising interest rates affect housing?"

**Routing**: Housing Agent (interest rates, housing market)

**Future**: When additional agents are added, queries spanning multiple domains will route to all relevant agents and synthesize responses.

---

## Adding a New Agent

### Checklist

1. [ ] Create agent specification in this document
2. [ ] Define data sources and collection methods
3. [ ] Implement agent class in `src/yavin/agents/specialized/`
4. [ ] Create collectors for each data source
5. [ ] Define database tables for metrics
6. [ ] Implement query tools
7. [ ] Add agent to orchestrator registry
8. [ ] Write tests
9. [ ] Create documentation

### Template

```python
# src/yavin/agents/specialized/new_agent.py

from yavin.agents.base import BaseAgent, AgentCapabilities

class NewTopicAgent(BaseAgent):
    name = "New Topic Agent"
    description = "Monitors [topic] and related developments"
    domain_keywords = ["keyword1", "keyword2", "keyword3"]

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name=self.name,
            description=self.description,
            data_sources=[...],
            metrics_tracked=[...],
            geographic_scope="Global",
            update_frequency="Daily",
            example_questions=[
                "Example question 1?",
                "Example question 2?",
            ]
        )

    async def collect(self) -> CollectionResult:
        # Implement collection logic
        pass

    async def query(self, question: str, context: dict) -> AgentResponse:
        # Implement query handling
        pass

    def get_tools(self) -> list[Tool]:
        return [
            # Define tools
        ]
```
