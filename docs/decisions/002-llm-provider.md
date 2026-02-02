# ADR-002: LLM Provider Selection

## Status

**Accepted** | Date: 2026-01-25

## Context

We need to choose an LLM provider for:

1. Agent query handling (answering questions about collected data)
2. Orchestrator routing (determining which agents to consult)
3. Response synthesis (combining multi-agent responses)

## Requirements

- Good tool/function calling support
- **Free or low cost for development** (personal project)
- Reliable availability
- Good quality for data analysis questions
- Easy migration path to production

## Decision

**GitHub Models** for development, with easy migration to **Azure OpenAI** for production.

## Rationale

### Why GitHub Models?

1. **Free tier** - Generous daily allowance for development
2. **Same models** - Access to GPT-4o, same as Azure/OpenAI
3. **Easy migration** - Just change `API_HOST` env var to switch providers
4. **No credit card** - Only need a GitHub account

### Migration Path

```
Development          Staging/Production
─────────────────────────────────────────
GitHub Models   →    Azure OpenAI
(free tier)          (higher limits, SLA)

API_HOST=github      API_HOST=azure
```

## Provider Configuration

### GitHub Models (Development - Default)

```bash
API_HOST=github
GITHUB_TOKEN=ghp_your-token
GITHUB_MODEL=gpt-4o
```

- **Endpoint**: `https://models.inference.ai.azure.com`
- **Rate limits**: [See GitHub docs](https://docs.github.com/github-models/prototyping-with-ai-models#rate-limits)
- **Models**: gpt-4o, gpt-4o-mini, and others

### Azure OpenAI (Production)

```bash
API_HOST=azure
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o
```

- Higher rate limits
- Enterprise SLA
- Data residency options

### OpenAI Direct (Alternative)

```bash
API_HOST=openai
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4o-mini
```

### Local Ollama (Offline Development)

```bash
API_HOST=ollama
OLLAMA_MODEL=llama3.1:latest
OLLAMA_ENDPOINT=http://localhost:11434/v1
```

## Implementation

Using LangChain's `ChatOpenAI` which supports all providers:

```python
# src/yavin/llm.py
from langchain_openai import ChatOpenAI

def get_chat_model() -> ChatOpenAI:
    api_host = os.getenv("API_HOST", "github")

    if api_host == "github":
        return ChatOpenAI(
            model=os.getenv("GITHUB_MODEL", "gpt-4o"),
            base_url="https://models.inference.ai.azure.com",
            api_key=os.environ["GITHUB_TOKEN"],
        )
    elif api_host == "azure":
        # Azure with DefaultAzureCredential
        ...
```

## Consequences

- Development is free with GitHub Models
- Same code works across all providers
- Easy to test locally with Ollama
- Production-ready with Azure OpenAI

## References

- [GitHub Models](https://github.com/marketplace/models)
- [Azure-Samples/python-ai-agent-frameworks-demos](https://github.com/Azure-Samples/python-ai-agent-frameworks-demos)
- [Azure AI Foundry](https://azure.microsoft.com/products/ai-studio)
