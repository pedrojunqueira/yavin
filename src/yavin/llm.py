"""
LLM client configuration for Yavin.

Supports multiple providers:
- GitHub Models (free tier with GitHub token)
- Azure OpenAI (production, higher limits)
- OpenAI Direct (alternative)

Based on patterns from: https://github.com/Azure-Samples/python-ai-agent-frameworks-demos
"""

import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv(override=True)


def get_chat_model() -> ChatOpenAI:
    """
    Get a ChatOpenAI model configured for the current API_HOST.
    
    Supports:
    - github: GitHub Models (free tier)
    - azure: Azure OpenAI
    - openai: OpenAI direct
    
    Returns:
        ChatOpenAI configured for the selected provider
    """
    api_host = os.getenv("API_HOST", "github")
    
    if api_host == "azure":
        # Azure OpenAI with DefaultAzureCredential
        import azure.identity
        
        token_provider = azure.identity.get_bearer_token_provider(
            azure.identity.DefaultAzureCredential(),
            "https://cognitiveservices.azure.com/.default",
        )
        return ChatOpenAI(
            model=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o"),
            base_url=os.environ["AZURE_OPENAI_ENDPOINT"] + "/openai/v1",
            api_key=token_provider,
        )
    
    elif api_host == "github":
        # GitHub Models (free tier)
        return ChatOpenAI(
            model=os.getenv("GITHUB_MODEL", "gpt-4o"),
            base_url="https://models.inference.ai.azure.com",
            api_key=os.environ["GITHUB_TOKEN"],
        )
    
    elif api_host == "ollama":
        # Local Ollama (optional, for offline development)
        return ChatOpenAI(
            model=os.getenv("OLLAMA_MODEL", "llama3.1:latest"),
            base_url=os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434/v1"),
            api_key="none",
        )
    
    else:
        # OpenAI direct
        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.environ.get("OPENAI_API_KEY"),
        )


@lru_cache
def get_cached_chat_model() -> ChatOpenAI:
    """Get a cached chat model instance."""
    return get_chat_model()
