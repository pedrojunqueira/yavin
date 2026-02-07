"""
Orchestrator Agent - Routes queries to specialized agents and synthesizes responses.

The orchestrator is responsible for:
1. Analyzing user queries to determine intent and domain
2. Routing to appropriate specialized agents
3. Managing conversation context/thread
4. Synthesizing responses from multiple agents if needed
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from yavin.agents.base import AgentResponse, BaseAgent
from yavin.llm import get_chat_model


@dataclass
class ConversationThread:
    """A conversation thread with context."""
    
    thread_id: str
    topic: str | None = None
    messages: list[HumanMessage | AIMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingDecision:
    """Result of query routing analysis."""
    
    agents: list[tuple[BaseAgent, float]]  # (agent, relevance_score)
    reasoning: str
    requires_multi_agent: bool = False


class Orchestrator:
    """
    Orchestrator that routes queries to specialized agents.
    
    Uses LLM to understand query intent and match to agent capabilities,
    then delegates to the appropriate agent(s) for response.
    """

    def __init__(self, agents: list[BaseAgent] | None = None, persist: bool = True):
        """
        Initialize the orchestrator.
        
        Args:
            agents: List of specialized agents to route to
            persist: Whether to persist conversations to database
        """
        self.agents: dict[str, BaseAgent] = {}
        self.threads: dict[str, ConversationThread] = {}
        self.model = get_chat_model()
        self.persist = persist
        
        # Register provided agents
        if agents:
            for agent in agents:
                self.register_agent(agent)
        
        # System prompt for the orchestrator
        self.system_prompt = """You are the Yavin orchestrator, a helpful AI assistant that monitors 
trends and topics that often disappear from mainstream media attention.

You have access to specialized agents that collect and analyze data on specific domains.
When a user asks a question, you should:

1. Determine which specialist agent(s) can best answer the question
2. Route the query to the appropriate agent(s)
3. Synthesize the response in a clear, informative way
4. Always cite the data sources when providing statistics

Available agents:
{agent_descriptions}

Current date: {current_date}

If the question is outside the scope of available agents, acknowledge this honestly
and suggest what topics you can help with.

For general greetings or meta-questions about yourself, respond directly without
routing to any agent."""

    def register_agent(self, agent: BaseAgent) -> None:
        """Register a specialized agent."""
        self.agents[agent.name] = agent

    def get_agent(self, name: str) -> BaseAgent | None:
        """Get an agent by name."""
        return self.agents.get(name)

    def list_agents(self) -> list[BaseAgent]:
        """List all registered agents."""
        return list(self.agents.values())

    async def generate_topic(self, message: str) -> str:
        """Generate a short 3-4 word topic from the first message."""
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""Generate a very short topic title (3-4 words max) that summarizes what this question is about.
Reply with ONLY the topic, nothing else. No quotes, no punctuation at the end.
Examples:
- "What is the current interest rate?" -> "Current Interest Rates"
- "How has inflation changed over the last year?" -> "Inflation Trends"
- "What did the RBA say about housing?" -> "RBA Housing Discussion"
"""),
            HumanMessage(content=message),
        ])
        
        chain = prompt | self.model
        response = await chain.ainvoke({})
        
        # Clean up the response
        topic = response.content.strip().strip('"').strip("'")
        # Limit length
        if len(topic) > 50:
            topic = topic[:47] + "..."
        return topic

    def _update_thread_topic(self, thread_id: str, topic: str) -> None:
        """Update the topic for a thread in the database."""
        if not self.persist:
            return
        
        from yavin.db.session import SyncSessionLocal
        from yavin.db.repository import ChatRepository
        
        with SyncSessionLocal() as session:
            repo = ChatRepository(session)
            repo.update_thread_topic(thread_id, topic)
            session.commit()

    def _get_agent_descriptions(self) -> str:
        """Get formatted descriptions of all agents for the system prompt."""
        descriptions = []
        for agent in self.agents.values():
            caps = agent.get_capabilities()
            desc = f"""- **{agent.name}**: {agent.description}
  - Metrics: {', '.join(caps.metrics_tracked[:5])}{'...' if len(caps.metrics_tracked) > 5 else ''}
  - Example questions: {caps.example_questions[0] if caps.example_questions else 'N/A'}"""
            descriptions.append(desc)
        return "\n".join(descriptions) if descriptions else "No agents registered yet."

    def _get_or_create_thread(self, thread_id: str | None = None, topic: str | None = None) -> ConversationThread:
        """Get an existing thread or create a new one."""
        # Check in-memory cache first
        if thread_id and thread_id in self.threads:
            thread = self.threads[thread_id]
            thread.last_active = datetime.now()
            return thread
        
        # Try to load from database if persisting
        if self.persist and thread_id:
            from yavin.db.session import SyncSessionLocal
            from yavin.db.repository import ChatRepository
            
            with SyncSessionLocal() as session:
                repo = ChatRepository(session)
                db_thread = repo.get_thread_by_id(thread_id)
                
                if db_thread:
                    # Load messages from database
                    messages = repo.get_thread_messages(thread_id)
                    thread = ConversationThread(
                        thread_id=db_thread.thread_id,
                        topic=db_thread.topic,
                        created_at=db_thread.created_at,
                        last_active=db_thread.updated_at,
                    )
                    
                    # Reconstruct message history
                    for msg in messages:
                        if msg.role == "user":
                            thread.messages.append(HumanMessage(content=msg.content))
                        else:
                            thread.messages.append(AIMessage(content=msg.content))
                    
                    self.threads[thread_id] = thread
                    return thread
        
        # Create new thread
        new_id = thread_id or f"thread_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        thread = ConversationThread(thread_id=new_id, topic=topic)
        self.threads[new_id] = thread
        
        # Save to database if persisting
        if self.persist:
            from yavin.db.session import SyncSessionLocal
            from yavin.db.repository import ChatRepository
            
            with SyncSessionLocal() as session:
                repo = ChatRepository(session)
                repo.create_thread(new_id, topic)
                session.commit()
        
        return thread

    def _persist_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        agent_name: str | None = None,
        confidence: float | None = None,
        sources_used: list[str] | None = None,
        tool_calls: int | None = None,
    ) -> None:
        """Persist a message to the database."""
        if not self.persist:
            return
        
        from yavin.db.session import SyncSessionLocal
        from yavin.db.repository import ChatRepository
        
        with SyncSessionLocal() as session:
            repo = ChatRepository(session)
            repo.add_message(
                thread_id=thread_id,
                role=role,
                content=content,
                agent_name=agent_name,
                confidence=confidence,
                sources_used=sources_used,
                tool_calls=tool_calls,
            )
            session.commit()

    async def route_query(self, question: str) -> RoutingDecision:
        """
        Determine which agents should handle this query.
        
        Uses both keyword matching and LLM analysis for routing.
        """
        matching_agents: list[tuple[BaseAgent, float]] = []
        
        # First pass: keyword matching
        for agent in self.agents.values():
            score = agent.matches_query(question)
            if score > 0:
                matching_agents.append((agent, score))
        
        # Sort by relevance
        matching_agents.sort(key=lambda x: x[1], reverse=True)
        
        # Determine if multi-agent response is needed
        requires_multi = len([a for a, s in matching_agents if s > 0.3]) > 1
        
        reasoning = ""
        if matching_agents:
            top_agent = matching_agents[0][0]
            reasoning = f"Routing to {top_agent.name} based on domain keywords."
        else:
            reasoning = "No specific agent matched. Will provide general response."
        
        return RoutingDecision(
            agents=matching_agents,
            reasoning=reasoning,
            requires_multi_agent=requires_multi,
        )

    # Threshold for "fresh" vs "established" conversation
    FRESH_THREAD_THRESHOLD = 6  # messages

    async def chat(
        self,
        message: str,
        thread_id: str | None = None,
        auto_topic: bool = True,
    ) -> AgentResponse:
        """
        Process a user message and return a response.
        
        Routing strategy:
        - Fresh threads (< 6 messages): ALWAYS delegate to specialized agent with force_fetch
          to minimize hallucination and ground responses in real data
        - Established threads (6+ messages): Use normal routing, rely on conversation context
        
        Args:
            message: The user's message
            thread_id: Optional thread ID for conversation continuity
            auto_topic: Whether to auto-generate a topic from the first message
            
        Returns:
            AgentResponse with the orchestrator's response
        """
        thread = self._get_or_create_thread(thread_id)
        
        # Determine if this is a fresh or established conversation
        is_fresh_thread = len(thread.messages) < self.FRESH_THREAD_THRESHOLD
        
        # Auto-generate topic from first message if none set
        is_first_message = len(thread.messages) == 0
        if auto_topic and is_first_message and not thread.topic:
            topic = await self.generate_topic(message)
            thread.topic = topic
            self._update_thread_topic(thread.thread_id, topic)
        
        # Add user message to thread
        thread.messages.append(HumanMessage(content=message))
        
        # Persist user message
        self._persist_message(
            thread_id=thread.thread_id,
            role="user",
            content=message,
        )
        
        # Route the query to determine which agent(s) to use
        routing = await self.route_query(message)
        
        # Fresh threads: ALWAYS delegate to an agent (prefer grounded responses)
        # Even if routing score is low, try to find an agent
        if is_fresh_thread:
            if routing.agents:
                # Use the best matching agent with force_fetch
                top_agent, score = routing.agents[0]
            elif self.agents:
                # No routing match, but we have agents - use the first one
                # This ensures we always ground in data for fresh threads
                top_agent = list(self.agents.values())[0]
                score = 0.0
                routing.reasoning = f"Fresh thread: defaulting to {top_agent.name} for data grounding."
            else:
                top_agent = None
                score = 0.0
            
            if top_agent:
                # Build context with force_fetch flag for fresh threads
                context = {
                    "thread_id": thread.thread_id,
                    "message_count": len(thread.messages),
                    "routing_score": score,
                    "force_fetch": True,  # Force data pre-fetch for fresh threads
                }
                
                # Get response from specialized agent
                agent_response = await top_agent.query(message, context)
                
                # Add response to thread
                thread.messages.append(AIMessage(content=agent_response.content))
                
                # Persist assistant response
                self._persist_message(
                    thread_id=thread.thread_id,
                    role="assistant",
                    content=agent_response.content,
                    agent_name=top_agent.name,
                    confidence=agent_response.confidence,
                    sources_used=agent_response.sources_used,
                    tool_calls=agent_response.metadata.get("tool_calls"),
                )
                
                return AgentResponse(
                    agent_name="Orchestrator",
                    content=agent_response.content,
                    confidence=agent_response.confidence,
                    sources_used=agent_response.sources_used,
                    data_points=agent_response.data_points,
                    metadata={
                        "thread_id": thread.thread_id,
                        "topic": thread.topic,
                        "routed_to": top_agent.name,
                        "routing_score": score,
                        "routing_reasoning": routing.reasoning,
                        "fresh_thread": True,
                        "force_fetch": True,
                        **agent_response.metadata,
                    },
                )
        
        # Established threads: normal routing logic
        if routing.agents:
            # Route to the most relevant agent
            top_agent, score = routing.agents[0]
            
            # Build context from conversation history
            context = {
                "thread_id": thread.thread_id,
                "message_count": len(thread.messages),
                "routing_score": score,
            }
            
            # Get response from specialized agent
            agent_response = await top_agent.query(message, context)
            
            # Add response to thread
            thread.messages.append(AIMessage(content=agent_response.content))
            
            # Persist assistant response
            self._persist_message(
                thread_id=thread.thread_id,
                role="assistant",
                content=agent_response.content,
                agent_name=top_agent.name,
                confidence=agent_response.confidence,
                sources_used=agent_response.sources_used,
                tool_calls=agent_response.metadata.get("tool_calls"),
            )
            
            return AgentResponse(
                agent_name="Orchestrator",
                content=agent_response.content,
                confidence=agent_response.confidence,
                sources_used=agent_response.sources_used,
                data_points=agent_response.data_points,
                metadata={
                    "thread_id": thread.thread_id,
                    "topic": thread.topic,
                    "routed_to": top_agent.name,
                    "routing_score": score,
                    "routing_reasoning": routing.reasoning,
                    "fresh_thread": False,
                    "force_fetch": False,
                    **agent_response.metadata,
                },
            )
        else:
            # No agent matched - respond directly
            response = await self._respond_directly(message, thread)
            thread.messages.append(AIMessage(content=response))
            
            # Persist direct response
            self._persist_message(
                thread_id=thread.thread_id,
                role="assistant",
                content=response,
                agent_name="Orchestrator",
                confidence=0.8,
            )
            
            return AgentResponse(
                agent_name="Orchestrator",
                content=response,
                confidence=0.8,
                sources_used=[],
                data_points=[],
                metadata={
                    "thread_id": thread.thread_id,
                    "topic": thread.topic,
                    "routed_to": None,
                    "routing_reasoning": routing.reasoning,
                    "fresh_thread": False,
                    "force_fetch": False,
                    "direct_response": True,
                },
            )

    async def _respond_directly(self, message: str, thread: ConversationThread) -> str:
        """Respond directly without routing to a specialized agent."""
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=self.system_prompt.format(
                agent_descriptions=self._get_agent_descriptions(),
                current_date=datetime.now().strftime("%Y-%m-%d"),
            )),
            MessagesPlaceholder(variable_name="history"),
            HumanMessage(content=message),
        ])
        
        # Build message history (last 10 messages for context)
        history = thread.messages[-10:] if len(thread.messages) > 1 else []
        
        chain = prompt | self.model
        response = await chain.ainvoke({"history": history})
        
        return response.content

    def get_thread_history(self, thread_id: str) -> list[dict[str, str]]:
        """Get the message history for a thread."""
        thread = self.threads.get(thread_id)
        if not thread:
            return []
        
        return [
            {
                "role": "user" if isinstance(msg, HumanMessage) else "assistant",
                "content": msg.content,
            }
            for msg in thread.messages
        ]

    def clear_thread(self, thread_id: str) -> bool:
        """Clear a conversation thread."""
        if thread_id in self.threads:
            del self.threads[thread_id]
            return True
        return False
