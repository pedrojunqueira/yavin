# ADR-001: Agent Framework Selection

## Status

**Accepted** | Date: 2026-01-25

## Context

We need to choose an approach for implementing the multi-agent system. The key requirements are:

1. Support for multiple specialized agents
2. An orchestrator that routes queries to appropriate agents
3. Tool calling (database queries, API calls)
4. Conversation context management
5. Easy to add new agents
6. **Support for GitHub Models, Azure OpenAI, and OpenAI**

## Decision

**LangChain v1 with Tools** for Phase 1, with option to evolve to **LangGraph** for complex multi-agent workflows.

## Rationale

Based on patterns from [Azure-Samples/python-ai-agent-frameworks-demos](https://github.com/Azure-Samples/python-ai-agent-frameworks-demos):

### Why LangChain v1?

1. **Provider flexibility** - Works with GitHub Models, Azure, OpenAI via same `ChatOpenAI` class
2. **Simple tool pattern** - Perfect for our Phase 1 single-agent use case
3. **Supervisor pattern** - Available when we need multi-agent orchestration
4. **Well documented** - Large community, many examples
5. **Proven patterns** - Used in production systems

### Evolution Path

```
Phase 1 (MVP)              Phase 2+                    Future
───────────────────────────────────────────────────────────────
LangChain v1 + Tools       LangChain Supervisor        LangGraph
(Housing Agent)            (Orchestrator + Agents)     (Complex workflows)
```

## Patterns We'll Use

### Phase 1: Agent with Tools

```python
from langchain.agents import create_agent
from langchain_core.tools import tool

@tool
def get_housing_approvals(start_date: str, end_date: str) -> dict:
    """Get housing approval data for a date range."""
    # Query database
    ...

agent = create_agent(
    model=get_chat_model(),
    system_prompt="You are a housing market analyst...",
    tools=[get_housing_approvals, get_interest_rates, get_news_coverage],
)

response = agent.invoke("How have housing approvals changed this year?")
```

### Phase 2+: Supervisor Pattern

```python
# Orchestrator routes to specialized agents
from langchain.agents import create_agent

housing_agent = create_agent(model=model, tools=housing_tools, ...)
commodity_agent = create_agent(model=model, tools=commodity_tools, ...)

supervisor = create_agent(
    model=model,
    system_prompt="Route queries to the appropriate specialist agent...",
    tools=[query_housing_agent, query_commodity_agent],
)
```

## Alternatives Considered

| Framework                     | Verdict         | Notes                               |
| ----------------------------- | --------------- | ----------------------------------- |
| **Microsoft Agent Framework** | Future option   | Newer, less mature, but promising   |
| **AutoGen**                   | Too heavy       | Overkill for our use case           |
| **CrewAI**                    | Too opinionated | Less flexibility for custom routing |
| **PydanticAI**                | Consider later  | Good for structured outputs         |
| **Custom**                    | Unnecessary     | LangChain covers our needs          |

## Implementation

### File Structure

```
src/yavin/
├── llm.py              # Provider-agnostic model configuration
├── agents/
│   ├── base.py         # BaseAgent abstract class
│   └── specialized/
│       └── housing.py  # Housing agent with LangChain tools
```

### Key Dependencies

```toml
[project]
dependencies = [
    "langchain>=0.3.0",
    "langchain-openai>=0.2.0",
    "langgraph>=0.2.0",  # For future complex workflows
]
```

## Consequences

- Consistent patterns from Azure-Samples examples
- Easy to switch between GitHub Models and Azure
- Clear upgrade path to more complex workflows
- Well-supported ecosystem

## References

- [Azure-Samples/python-ai-agent-frameworks-demos](https://github.com/Azure-Samples/python-ai-agent-frameworks-demos)
- [LangChain v1 Documentation](https://docs.langchain.com/oss/python/langchain/overview)
- [LangGraph Documentation](https://docs.langchain.com/oss/python/langgraph/overview)
