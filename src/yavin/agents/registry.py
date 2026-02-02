"""
Agent Registry - Central registry for discovering and managing agents.

The registry provides:
- Registration of agents by name
- Discovery of agents by capabilities/domain
- Lazy loading of agent instances
"""

from typing import Callable, TypeVar

from yavin.agents.base import AgentCapabilities, BaseAgent


T = TypeVar("T", bound=BaseAgent)


class AgentRegistry:
    """
    Central registry for all specialized agents.
    
    Agents can be registered either by instance or by factory function
    for lazy loading.
    """
    
    _instance: "AgentRegistry | None" = None
    
    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}
        self._factories: dict[str, Callable[[], BaseAgent]] = {}
    
    @classmethod
    def get_instance(cls) -> "AgentRegistry":
        """Get the singleton instance of the registry."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (useful for testing)."""
        cls._instance = None
    
    def register(self, name: str, agent: BaseAgent) -> None:
        """
        Register an agent instance by name.
        
        Args:
            name: Unique identifier for the agent
            agent: The agent instance to register
        """
        self._agents[name] = agent
    
    def register_factory(self, name: str, factory: Callable[[], BaseAgent]) -> None:
        """
        Register an agent factory for lazy loading.
        
        The agent will only be instantiated when first requested.
        
        Args:
            name: Unique identifier for the agent
            factory: Callable that returns an agent instance
        """
        self._factories[name] = factory
    
    def get(self, name: str) -> BaseAgent | None:
        """
        Get an agent by name.
        
        If the agent was registered via factory, it will be instantiated
        on first access and cached.
        
        Args:
            name: The agent name to look up
            
        Returns:
            The agent instance or None if not found
        """
        # Check if already instantiated
        if name in self._agents:
            return self._agents[name]
        
        # Check if there's a factory
        if name in self._factories:
            agent = self._factories[name]()
            self._agents[name] = agent
            return agent
        
        return None
    
    def get_all(self) -> dict[str, BaseAgent]:
        """
        Get all registered agents, instantiating any pending factories.
        
        Returns:
            Dictionary of agent name to agent instance
        """
        # Instantiate any remaining factories
        for name, factory in self._factories.items():
            if name not in self._agents:
                self._agents[name] = factory()
        
        return self._agents.copy()
    
    def list_agents(self) -> list[str]:
        """
        List all registered agent names.
        
        Returns:
            List of agent names (both instantiated and factories)
        """
        return list(set(self._agents.keys()) | set(self._factories.keys()))
    
    def get_capabilities(self, name: str) -> AgentCapabilities | None:
        """
        Get the capabilities of a specific agent.
        
        Args:
            name: The agent name
            
        Returns:
            AgentCapabilities or None if agent not found
        """
        agent = self.get(name)
        if agent:
            return agent.get_capabilities()
        return None
    
    def get_all_capabilities(self) -> dict[str, AgentCapabilities]:
        """
        Get capabilities of all registered agents.
        
        Returns:
            Dictionary of agent name to capabilities
        """
        agents = self.get_all()
        return {name: agent.get_capabilities() for name, agent in agents.items()}
    
    def find_by_domain(self, query: str) -> list[tuple[str, BaseAgent, float]]:
        """
        Find agents that might handle a query based on domain keywords.
        
        Args:
            query: The user query to match against agent domains
            
        Returns:
            List of (name, agent, score) tuples sorted by relevance
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        results = []
        
        for name, agent in self.get_all().items():
            # Check domain keywords if available
            domain_keywords = getattr(agent, "domain_keywords", [])
            if not domain_keywords:
                continue
            
            # Calculate match score
            score = 0.0
            for keyword in domain_keywords:
                keyword_lower = keyword.lower()
                # Exact match in query
                if keyword_lower in query_lower:
                    score += 1.0
                # Partial word match
                elif any(keyword_lower in word or word in keyword_lower for word in query_words):
                    score += 0.5
            
            if score > 0:
                results.append((name, agent, score))
        
        # Sort by score descending
        results.sort(key=lambda x: x[2], reverse=True)
        return results


def setup_default_registry() -> AgentRegistry:
    """
    Set up the default agent registry with all available agents.
    
    Returns:
        Configured AgentRegistry instance
    """
    registry = AgentRegistry.get_instance()
    
    # Register housing agent (lazy loaded)
    def create_housing_agent():
        from yavin.agents.specialized.housing import HousingAgent
        return HousingAgent()
    
    registry.register_factory("housing", create_housing_agent)
    
    # Future agents would be registered here:
    # registry.register_factory("labour", create_labour_agent)
    # registry.register_factory("trade", create_trade_agent)
    
    return registry


# Convenience function to get the global registry
def get_registry() -> AgentRegistry:
    """Get the global agent registry, setting it up if needed."""
    registry = AgentRegistry.get_instance()
    
    # Check if empty and set up defaults
    if not registry.list_agents():
        setup_default_registry()
    
    return registry
