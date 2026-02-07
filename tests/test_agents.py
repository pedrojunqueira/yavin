"""
Tests for agent functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from yavin.agents.specialized.housing import HousingAgent


class TestHousingAgent:
    """Tests for the Housing Agent."""

    def test_agent_has_name(self):
        """Agent should have a name."""
        agent = HousingAgent()
        assert agent.name == "Housing Agent"

    def test_agent_has_domain_keywords(self):
        """Agent should have domain keywords for routing."""
        agent = HousingAgent()
        assert len(agent.domain_keywords) > 0
        assert "housing" in agent.domain_keywords

    def test_get_capabilities(self):
        """Agent should return its capabilities."""
        agent = HousingAgent()
        caps = agent.get_capabilities()

        assert caps.name == "Housing Agent"
        assert len(caps.data_sources) > 0
        assert len(caps.metrics_tracked) > 0
        assert len(caps.example_questions) > 0

    def test_matches_query_relevant(self):
        """Agent should match relevant queries."""
        agent = HousingAgent()

        score = agent.matches_query("What's happening with housing prices?")
        assert score > 0

    def test_matches_query_irrelevant(self):
        """Agent should not match irrelevant queries."""
        agent = HousingAgent()

        score = agent.matches_query("What's the weather in Tokyo?")
        assert score == 0

    def test_get_tools(self):
        """Agent should have tools defined."""
        agent = HousingAgent()
        tools = agent.get_tools()

        assert len(tools) > 0
        tool_names = [t.name for t in tools]
        assert "get_latest_metric" in tool_names

    @pytest.mark.asyncio
    async def test_query_returns_response(self):
        """Query should return an AgentResponse."""
        from langchain_core.messages import AIMessage
        
        # Mock the LLM to avoid API calls during tests
        with patch('yavin.agents.specialized.housing.get_chat_model') as mock_get_model:
            mock_model = MagicMock()
            mock_bound = MagicMock()
            
            # Create a mock AI response
            mock_ai_message = AIMessage(content="The current interest rate is 3.85%.")
            mock_bound.ainvoke = AsyncMock(return_value=mock_ai_message)
            mock_model.bind_tools = MagicMock(return_value=mock_bound)
            mock_get_model.return_value = mock_model
            
            agent = HousingAgent()
            response = await agent.query("What's the current interest rate?")

        assert response.agent_name == "Housing Agent"
        assert response.content is not None

    @pytest.mark.asyncio
    async def test_collect_returns_result(self):
        """Collect should return a CollectionResult."""
        agent = HousingAgent()
        result = await agent.collect()

        assert result.agent_name == "Housing Agent"
        assert result.status is not None
