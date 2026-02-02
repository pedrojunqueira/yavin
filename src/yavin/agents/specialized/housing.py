"""
Housing Market Agent - Monitors Australian housing market indicators.

This is the first specialized agent, focusing on:
- Building approvals (ABS)
- Interest rates (RBA)
- Housing credit (RBA)
- RBA meeting minutes
- Related news coverage
"""

from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool

from yavin.agents.base import (
    AgentCapabilities,
    AgentResponse,
    BaseAgent,
    CollectionResult,
    CollectionStatus,
    DataSource,
    Tool,
)
from yavin.db.session import SyncSessionLocal
from yavin.db.repository import AgentRepository, DataPointRepository, DocumentRepository
from yavin.llm import get_chat_model


# Define tools as module-level functions with @tool decorator
# These will be bound to the LLM for function calling

@tool
def get_latest_metric(metric_name: str) -> dict:
    """
    Get the most recent value for a housing market metric.
    
    Available metrics:
    - housing_approvals_total: Total dwelling unit approvals
    - housing_approvals_houses: House approvals
    - housing_approvals_apartments: Apartment approvals  
    - interest_rate_cash: RBA cash rate target
    - inflation_cpi_annual: Annual CPI inflation
    - inflation_trimmed_mean_annual: Core inflation measure
    - unemployment_rate: Unemployment rate
    - housing_lending_rate_variable_owner_occupier: Variable mortgage rate
    
    Args:
        metric_name: The name of the metric to retrieve
    """
    try:
        with SyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            agent = agent_repo.get_by_name("housing")
            
            if not agent:
                return {"error": "Housing agent not found in database", "metric": metric_name}
            
            dp_repo = DataPointRepository(session)
            latest = dp_repo.get_latest(agent.id, metric_name)
            
            if latest:
                return {
                    "metric": metric_name,
                    "value": latest.value,
                    "period": latest.period,
                    "unit": latest.unit,
                    "source": latest.source,
                    "collected_at": latest.created_at.isoformat(),
                }
            else:
                return {"error": f"No data found for metric '{metric_name}'", "metric": metric_name}
    except Exception as e:
        return {"error": str(e), "metric": metric_name}


@tool
def get_metric_timeseries(metric_name: str, limit: int = 12) -> dict:
    """
    Get historical values for a housing market metric.
    
    Args:
        metric_name: The name of the metric to retrieve
        limit: Number of recent data points to return (default 12)
    """
    try:
        with SyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            agent = agent_repo.get_by_name("housing")
            
            if not agent:
                return {"error": "Housing agent not found in database", "metric": metric_name}
            
            dp_repo = DataPointRepository(session)
            data_points = dp_repo.get_timeseries(agent.id, metric_name, limit=limit)
            
            if data_points:
                # Return in chronological order
                data = [
                    {
                        "period": dp.period,
                        "value": dp.value,
                        "unit": dp.unit,
                    }
                    for dp in reversed(data_points)
                ]
                return {
                    "metric": metric_name,
                    "data": data,
                    "count": len(data),
                    "source": data_points[0].source if data_points else None,
                }
            else:
                return {"error": f"No data found for metric '{metric_name}'", "metric": metric_name}
    except Exception as e:
        return {"error": str(e), "metric": metric_name}


@tool
def get_rba_minutes(limit: int = 3) -> dict:
    """
    Get recent RBA Monetary Policy Board meeting minutes.
    
    Returns summaries of recent RBA meetings including the cash rate decisions
    and key discussion points about economic and financial conditions.
    
    Args:
        limit: Number of recent meetings to return (default 3)
    """
    try:
        with SyncSessionLocal() as session:
            doc_repo = DocumentRepository(session)
            documents = doc_repo.get_by_type("rba_minutes", limit=limit)
            
            if documents:
                meetings = []
                for doc in documents:
                    meetings.append({
                        "meeting_date": doc.external_id,
                        "title": doc.title,
                        "decision_summary": doc.summary[:500] if doc.summary else None,
                        "cash_rate": doc.extra_data.get("cash_rate_decision"),
                        "source_url": doc.source_url,
                    })
                return {
                    "meetings": meetings,
                    "count": len(meetings),
                }
            else:
                return {"error": "No RBA minutes found", "meetings": []}
    except Exception as e:
        return {"error": str(e), "meetings": []}


@tool  
def search_rba_minutes(query: str, limit: int = 5) -> dict:
    """
    Search RBA meeting minutes for specific topics.
    
    Useful for finding what the RBA has said about specific economic topics
    like inflation, employment, housing, or global conditions.
    
    Args:
        query: Search query (e.g., "inflation", "housing", "employment")
        limit: Maximum number of results
    """
    try:
        with SyncSessionLocal() as session:
            doc_repo = DocumentRepository(session)
            documents = doc_repo.search_documents(query, document_type="rba_minutes", limit=limit)
            
            if documents:
                results = []
                for doc in documents:
                    # Find relevant chunks containing the query
                    relevant_text = ""
                    for chunk in doc.chunks:
                        if query.lower() in chunk.content.lower():
                            relevant_text = chunk.content[:500]
                            break
                    
                    results.append({
                        "meeting_date": doc.external_id,
                        "title": doc.title,
                        "relevant_excerpt": relevant_text or doc.summary[:300] if doc.summary else None,
                        "cash_rate": doc.extra_data.get("cash_rate_decision"),
                    })
                return {
                    "query": query,
                    "results": results,
                    "count": len(results),
                }
            else:
                return {"query": query, "results": [], "count": 0}
    except Exception as e:
        return {"error": str(e), "query": query, "results": []}


@tool
def list_available_metrics() -> dict:
    """
    List all available housing market metrics that can be queried.
    
    Use this to discover what data is available before querying specific metrics.
    """
    try:
        from sqlalchemy import select, distinct
        from yavin.db.models import DataPoint
        
        with SyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            agent = agent_repo.get_by_name("housing")
            
            if not agent:
                return {"error": "Housing agent not found", "metrics": []}
            
            # Get distinct metric names
            stmt = (
                select(distinct(DataPoint.metric_name))
                .where(DataPoint.agent_id == agent.id)
            )
            result = session.execute(stmt)
            metrics = [row[0] for row in result]
            
            return {
                "metrics": metrics,
                "count": len(metrics),
            }
    except Exception as e:
        return {"error": str(e), "metrics": []}


class HousingAgent(BaseAgent):
    """
    Specialized agent for monitoring the Australian housing market.
    
    Uses LangChain tools to query collected data and provide analysis.
    """

    name = "Housing Agent"
    description = "Monitors Australian housing market indicators including building approvals, interest rates, lending, and RBA monetary policy decisions."
    domain_keywords = [
        "housing",
        "property",
        "real estate",
        "mortgage",
        "home loan",
        "dwelling",
        "apartment",
        "house price",
        "rent",
        "rental",
        "building approval",
        "interest rate",
        "rba",
        "reserve bank",
        "cash rate",
        "housing affordability",
        "inflation",
        "cpi",
        "minutes",
        "meeting",
        "monetary policy",
        "board",
    ]

    SYSTEM_PROMPT = """You are the Housing Agent, a specialized analyst monitoring the Australian housing market.

IMPORTANT: You have access to a LOCAL DATABASE with real, up-to-date data. DO NOT rely on your training data.
ALWAYS use the available tools to retrieve current information before answering.

Available data sources in your database:
- Australian Bureau of Statistics (ABS): Building approvals, housing starts
- Reserve Bank of Australia (RBA): Interest rates, inflation, lending rates
- RBA Meeting Minutes: Full text of recent monetary policy board meetings (use get_rba_minutes or search_rba_minutes)
- Economic indicators: Unemployment, CPI, credit growth

CRITICAL INSTRUCTIONS:
1. ALWAYS call tools first to get data - never answer from memory
2. Use get_rba_minutes to retrieve the actual RBA meeting minutes from the database
3. Use search_rba_minutes to search for specific topics in the minutes
4. Use get_latest_metric or get_metric_timeseries for numerical data
5. Use list_available_metrics if unsure what data is available
6. Cite specific numbers, dates, and sources from tool results
7. If a tool returns an error, tell the user what data is missing

Current date: {current_date}

Be concise but informative. Focus on facts from the data."""

    def __init__(self) -> None:
        """Initialize the housing agent with LLM and tools."""
        self.model = get_chat_model()
        self.tools = [
            get_latest_metric,
            get_metric_timeseries,
            get_rba_minutes,
            search_rba_minutes,
            list_available_metrics,
        ]
        # Bind tools to the model
        self.model_with_tools = self.model.bind_tools(self.tools)

    def get_capabilities(self) -> AgentCapabilities:
        """Return housing agent capabilities."""
        return AgentCapabilities(
            name=self.name,
            description=self.description,
            data_sources=[
                DataSource(
                    name="ABS Building Approvals",
                    source_type="api",
                    url="https://api.data.abs.gov.au",
                    update_frequency="Monthly",
                    description="Official dwelling approval statistics by type and state",
                ),
                DataSource(
                    name="RBA Interest Rates",
                    source_type="web",
                    url="https://www.rba.gov.au/statistics/",
                    update_frequency="As changed",
                    description="Official cash rate and lending rates",
                ),
                DataSource(
                    name="RBA Meeting Minutes",
                    source_type="web",
                    url="https://www.rba.gov.au/monetary-policy/rba-board-minutes/",
                    update_frequency="8x per year",
                    description="Monetary Policy Board meeting minutes and decisions",
                ),
                DataSource(
                    name="RBA Inflation Data",
                    source_type="web",
                    url="https://www.rba.gov.au/statistics/",
                    update_frequency="Quarterly",
                    description="CPI and trimmed mean inflation measures",
                ),
            ],
            metrics_tracked=[
                "housing_approvals_total",
                "housing_approvals_houses",
                "housing_approvals_apartments",
                "interest_rate_cash",
                "inflation_cpi_annual",
                "inflation_trimmed_mean_annual",
                "unemployment_rate",
                "housing_lending_rate_variable_owner_occupier",
            ],
            geographic_scope="Australia",
            update_frequency="Daily (news), Monthly (statistics)",
            example_questions=[
                "What is the current RBA cash rate?",
                "How have building approvals trended over the last 12 months?",
                "What did the RBA say about inflation in their last meeting?",
                "What's the current unemployment rate?",
                "How have interest rates changed this year?",
            ],
        )

    async def collect(self) -> CollectionResult:
        """
        Collect data from all housing-related sources.
        """
        started_at = datetime.now()
        errors = []
        records_collected = 0
        
        # Import collectors
        from yavin.collectors.sources.abs import ABSBuildingApprovalsHistoryCollector
        from yavin.collectors.sources.rba import (
            RBAInterestRateCollector,
            RBAInflationCollector,
            RBAMinutesCollector,
        )
        
        collectors = [
            ABSBuildingApprovalsHistoryCollector(),
            RBAInterestRateCollector(),
            RBAInflationCollector(),
            RBAMinutesCollector(),
        ]
        
        for collector in collectors:
            try:
                result = await collector.collect()
                if result.success:
                    records_collected += len(result.records)
                else:
                    errors.append(f"{collector.name}: {result.error_message}")
            except Exception as e:
                errors.append(f"{collector.name}: {str(e)}")
        
        completed_at = datetime.now()
        
        return CollectionResult(
            agent_name=self.name,
            status=CollectionStatus.SUCCESS if not errors else CollectionStatus.PARTIAL,
            started_at=started_at,
            completed_at=completed_at,
            records_collected=records_collected,
            errors=errors,
            metadata={},
        )

    async def query(self, question: str, context: dict[str, Any] | None = None) -> AgentResponse:
        """
        Answer a question about the housing market using LLM with tools.
        """
        from langchain_core.messages import AIMessage, ToolMessage
        
        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT.format(
                current_date=datetime.now().strftime("%Y-%m-%d")
            )),
            HumanMessage(content=question),
        ]
        
        # Keep track of sources and data used
        sources_used = []
        data_points = []
        
        # Run the agent loop - allow multiple tool calls
        max_iterations = 5
        for _ in range(max_iterations):
            response = await self.model_with_tools.ainvoke(messages)
            messages.append(response)
            
            # Check if there are tool calls
            if not response.tool_calls:
                # No more tool calls, we have the final response
                break
            
            # Execute tool calls
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                # Find and execute the tool
                tool_result = None
                for t in self.tools:
                    if t.name == tool_name:
                        tool_result = t.invoke(tool_args)
                        sources_used.append(tool_name)
                        if isinstance(tool_result, dict):
                            data_points.append({
                                "tool": tool_name,
                                "args": tool_args,
                                "result": tool_result,
                            })
                        break
                
                if tool_result is None:
                    tool_result = {"error": f"Unknown tool: {tool_name}"}
                
                # Add tool result to messages
                messages.append(ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_call["id"],
                ))
        
        # Extract final response
        final_response = messages[-1]
        if isinstance(final_response, AIMessage):
            content = final_response.content
        else:
            content = "I was unable to generate a response."
        
        return AgentResponse(
            agent_name=self.name,
            content=content,
            confidence=0.9 if data_points else 0.5,
            sources_used=list(set(sources_used)),
            data_points=data_points,
            metadata={
                "tool_calls": len(data_points),
                "iterations": len([m for m in messages if isinstance(m, AIMessage)]),
            },
        )

    def get_tools(self) -> list[Tool]:
        """Return tools available to this agent (for introspection)."""
        return [
            Tool(
                name=t.name,
                description=t.description,
                parameters={},
                function=t.func,
            )
            for t in self.tools
        ]
