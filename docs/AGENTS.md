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

#### Data Sources (Implemented)

| Source                 | Type      | Frequency  | Data Points                              | Status |
| ---------------------- | --------- | ---------- | ---------------------------------------- | ------ |
| ABS Building Approvals | SDMX API  | Monthly    | Dwelling approvals (10,000+ data points) | ✅     |
| ABS Labour Force       | SDMX API  | Monthly    | Unemployment, participation (since 1978) | ✅     |
| ABS Earnings           | SDMX API  | Bi-annual  | Weekly earnings by gender                | ✅     |
| ABS Lending Indicators | SDMX API  | Monthly    | Average loan sizes by borrower type      | ✅     |
| RBA Excel Data         | Excel/CSV | Monthly    | Interest rates, inflation, lending rates | ✅     |
| RBA Meeting Minutes    | HTML      | 8x/year    | Full text for semantic search            | ✅     |
| RBA Policy Statements  | HTML      | As changed | Cash rate decisions (immediate updates)  | ✅     |

#### Metrics Tracked (31 Total)

**Housing Approvals (from ABS):**

- `housing_approvals_total` - Total dwelling approvals (monthly, since 1983)

**Interest Rates & Inflation (from RBA):**

- `interest_rate_cash` - RBA cash rate target
- `inflation_cpi_annual` - Annual CPI inflation
- `inflation_trimmed_mean_annual` - Core inflation measure
- `housing_lending_rate_*` - Various lending rates (variable, fixed, investor, owner-occupier)

**Labour Market (from ABS):**

- `unemployment_rate` - Unemployment rate (since 1978)
- `labour_force_participation_rate` - Participation rate
- `employment_to_population_ratio` - Employment ratio

**Earnings (from ABS):**

- `fulltime_adult_avg_weekly_ordinary_earnings` - Weekly earnings (total, male, female)
- `all_employees_avg_weekly_total_earnings` - All employee earnings

**Lending (from ABS):**

- `avg_loan_size_total` - Average loan size (all borrowers)
- `avg_loan_size_first_home_buyer` - First home buyer average loan
- `avg_loan_size_owner_occupier` - Owner occupier average loan
- `avg_loan_size_investor` - Investor average loan

#### Example Questions

**Interest Rates & Monetary Policy:**

1. "What is the current RBA cash rate?"
2. "What were the key points from the latest RBA meeting?"
3. "How has inflation changed over the past 2 years?"

**Housing Affordability:** 4. "What is the current housing affordability for first home buyers?" 5. "How has the average loan size grown over time?" 6. "Compare first home buyer loans vs investor loans"

**Economic Analysis:** 7. "How have housing approvals changed over the last 12 months?" 8. "What is the trend in unemployment rate?" 9. "Calculate the average monthly building approvals for each year from 2020 to 2025" 10. "What data do you have available?"

#### Tools (11 Total)

**Data Retrieval:**

```python
get_latest_metric(metric_name)          # Get most recent value for a metric
get_metric_timeseries(metric_name, limit) # Get historical time series
list_available_metrics()                  # List all metrics in database
get_metrics_summary()                     # Comprehensive summary with ranges
query_metric_by_period(metric_name, start, end)  # Query specific date range
```

**Analysis Tools:**

```python
analyze_metric_growth(metric_name, periods)  # Calculate growth %, CAGR, trends
calculate_affordability(loan_type, income_type)  # Housing affordability analysis
compare_metrics(metric_names, limit)      # Side-by-side metric comparison
```

**RBA Documents:**

```python
get_rba_minutes(limit)                    # Get recent RBA meeting minutes
search_rba_minutes(query, limit)          # Search minutes by keyword
```

**Flexible SQL (Read-Only):**

```python
query_database(sql_query)                 # Execute custom SELECT queries
```

> **Security Note:** The `query_database` tool only allows SELECT queries. All data-modifying operations (INSERT, UPDATE, DELETE, DROP, etc.) are blocked. Queries have a 30-second timeout and return max 500 rows.

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
