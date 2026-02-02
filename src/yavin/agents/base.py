"""
Base classes for Yavin agents.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class CollectionStatus(Enum):
    """Status of a data collection run."""

    SUCCESS = "success"
    PARTIAL = "partial"  # Some sources failed
    FAILED = "failed"


@dataclass
class DataSource:
    """Description of a data source used by an agent."""

    name: str
    source_type: str  # api, rss, web_scrape
    url: str
    update_frequency: str
    description: str


@dataclass
class AgentCapabilities:
    """Description of what an agent can do."""

    name: str
    description: str
    data_sources: list[DataSource]
    metrics_tracked: list[str]
    geographic_scope: str
    update_frequency: str
    example_questions: list[str]


@dataclass
class CollectionResult:
    """Result of a data collection run."""

    agent_name: str
    status: CollectionStatus
    started_at: datetime
    completed_at: datetime
    records_collected: int
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Response from an agent to a query."""

    agent_name: str
    content: str
    confidence: float  # 0.0 to 1.0
    sources_used: list[str] = field(default_factory=list)
    data_points: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Tool:
    """A tool that an agent can use."""

    name: str
    description: str
    parameters: dict[str, Any]
    function: callable  # The actual function to call


class BaseAgent(ABC):
    """
    Abstract base class for all specialized agents.
    
    Each agent is responsible for:
    1. Collecting data from specific sources
    2. Storing data in the database
    3. Answering questions about its domain
    """

    # Subclasses should override these
    name: str = "Base Agent"
    description: str = "Base agent class"
    domain_keywords: list[str] = []

    @abstractmethod
    def get_capabilities(self) -> AgentCapabilities:
        """
        Return a description of this agent's capabilities.
        
        Used by the orchestrator to decide which agents to consult.
        """
        pass

    @abstractmethod
    async def collect(self) -> CollectionResult:
        """
        Execute data collection from all configured sources.
        
        This method should:
        1. Fetch data from each source
        2. Validate and normalize the data
        3. Store in the database
        4. Return a summary of what was collected
        """
        pass

    @abstractmethod
    async def query(self, question: str, context: dict[str, Any] | None = None) -> AgentResponse:
        """
        Answer a question about this agent's domain.
        
        Args:
            question: The user's question in natural language
            context: Optional context (conversation history, user preferences, etc.)
        
        Returns:
            An AgentResponse with the answer and supporting data
        """
        pass

    @abstractmethod
    def get_tools(self) -> list[Tool]:
        """
        Return the tools available to this agent for answering queries.
        
        Tools are functions the LLM can call to retrieve data.
        """
        pass

    def matches_query(self, query: str) -> float:
        """
        Calculate how relevant this agent is to a query.
        
        Returns a score from 0.0 to 1.0.
        Override for more sophisticated matching.
        """
        query_lower = query.lower()
        matches = sum(1 for keyword in self.domain_keywords if keyword in query_lower)
        if not self.domain_keywords:
            return 0.0
        return min(matches / len(self.domain_keywords), 1.0)
