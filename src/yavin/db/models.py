"""
SQLAlchemy database models for Yavin.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Agent(Base):
    """Agent configuration and status."""

    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "housing", "commodities"
    description: Mapped[str] = mapped_column(Text, nullable=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    data_points: Mapped[list["DataPoint"]] = relationship("DataPoint", back_populates="agent")
    collection_runs: Mapped[list["CollectionRun"]] = relationship("CollectionRun", back_populates="agent")


class DataPoint(Base):
    """A single data point collected by an agent."""

    __tablename__ = "data_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("agents.id"), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=True)
    value_text: Mapped[str] = mapped_column(Text, nullable=True)  # For non-numeric values
    period: Mapped[str] = mapped_column(String(50), nullable=True)  # e.g., "2024-01" for monthly data
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(200), nullable=True)
    geography: Mapped[str] = mapped_column(String(100), nullable=True)
    unit: Mapped[str] = mapped_column(String(100), nullable=True)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # renamed from metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="data_points")


class CollectionRun(Base):
    """Log of data collection runs."""

    __tablename__ = "collection_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("agents.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # success, partial, failed
    records_collected: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list[str]] = mapped_column(JSON, default=list)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # renamed from metadata

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="collection_runs")


class Article(Base):
    """News articles collected for sentiment/coverage tracking."""

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("agents.id"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    source_name: Mapped[str] = mapped_column(String(200), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=True)  # -1 to 1
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # renamed from metadata
    
    # For vector search (if using pgvector)
    # embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=True)


class Document(Base):
    """
    Long-form documents collected by agents (e.g., RBA minutes, policy papers).
    
    Documents are stored whole, with content split into chunks for LLM retrieval.
    Each chunk can have its own embedding for semantic search.
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("agents.id"), nullable=False)
    
    # Document identification
    document_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # e.g., "rba_minutes", "policy_paper"
    external_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)  # e.g., "2025-12-09" for meeting date
    
    # Document metadata
    title: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, index=True)
    
    # Full content
    content: Mapped[str] = mapped_column(Text, nullable=False)  # Full document text
    summary: Mapped[str] = mapped_column(Text, nullable=True)  # LLM-generated or extracted summary
    
    # Structured metadata (for filtering)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # Example for RBA minutes: {"cash_rate": 3.6, "members": [...], "decision": "unchanged"}
    
    # Timestamps
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", 
        back_populates="document",
        cascade="all, delete-orphan"
    )

    # Composite index for deduplication
    __table_args__ = (
        Index('ix_documents_type_external_id', 'document_type', 'external_id', unique=True),
    )


class DocumentChunk(Base):
    """
    A chunk of a document for LLM retrieval.
    
    Documents are split into overlapping chunks for better semantic search
    and to fit within LLM context windows.
    """

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Chunk position and content
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-based index
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Chunk metadata
    section_name: Mapped[str] = mapped_column(String(100), nullable=True)  # e.g., "financial_conditions"
    char_start: Mapped[int] = mapped_column(Integer, nullable=True)  # Start position in original doc
    char_end: Mapped[int] = mapped_column(Integer, nullable=True)  # End position in original doc
    token_count: Mapped[int] = mapped_column(Integer, nullable=True)  # Approximate token count
    
    # Vector embedding for semantic search
    # When using pgvector, uncomment and run: CREATE EXTENSION vector;
    # embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=True)
    embedding_model: Mapped[str] = mapped_column(String(50), nullable=True)  # e.g., "text-embedding-3-small"
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index('ix_document_chunks_doc_index', 'document_id', 'chunk_index'),
    )


class ChatThread(Base):
    """A conversation thread with the orchestrator."""
    
    __tablename__ = "chat_threads"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thread_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    topic: Mapped[str] = mapped_column(String(200), nullable=True)  # User-provided or auto-generated topic
    summary: Mapped[str] = mapped_column(Text, nullable=True)  # Auto-generated summary of conversation
    
    # Thread state
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", 
        back_populates="thread",
        order_by="ChatMessage.sequence_num",
        cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    """A single message in a chat thread."""
    
    __tablename__ = "chat_messages"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thread_id: Mapped[int] = mapped_column(Integer, ForeignKey("chat_threads.id"), nullable=False)
    
    # Message content
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user", "assistant", "system"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sequence_num: Mapped[int] = mapped_column(Integer, nullable=False)  # Order in conversation
    
    # Response metadata (for assistant messages)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=True)
    sources_used: Mapped[list[str]] = mapped_column(JSON, default=list)
    tool_calls: Mapped[int] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    thread: Mapped["ChatThread"] = relationship("ChatThread", back_populates="messages")
    
    __table_args__ = (
        Index('ix_chat_messages_thread_seq', 'thread_id', 'sequence_num'),
    )

