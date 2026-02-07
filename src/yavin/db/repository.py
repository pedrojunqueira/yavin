"""
Repository pattern for database operations.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from yavin.db.models import Agent, CollectionRun, DataPoint, Document, DocumentChunk, ChatThread, ChatMessage


class DataPointRepository:
    """Repository for DataPoint operations."""

    def __init__(self, session: Session):
        self.session = session

    def save_data_point(
        self,
        agent_id: int,
        metric_name: str,
        value: float | None,
        period: str,
        source: str | None = None,
        geography: str | None = None,
        unit: str | None = None,
        value_text: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DataPoint:
        """Save a single data point."""
        data_point = DataPoint(
            agent_id=agent_id,
            metric_name=metric_name,
            value=value,
            value_text=value_text,
            period=period,
            timestamp=datetime.utcnow(),
            source=source,
            geography=geography,
            unit=unit,
            extra_data=metadata or {},
        )
        self.session.add(data_point)
        self.session.flush()
        return data_point

    def save_data_points(
        self,
        agent_id: int,
        records: list[dict[str, Any]],
        skip_existing: bool = True,
    ) -> tuple[list[DataPoint], int]:
        """
        Save multiple data points from collector records.
        
        Args:
            agent_id: The agent ID to associate with records
            records: List of record dicts from collector
            skip_existing: If True, skip records that already exist (by metric_name + period)
            
        Returns:
            Tuple of (saved_data_points, skipped_count)
        """
        data_points = []
        skipped = 0
        
        # Get existing periods for deduplication if needed
        existing_periods: set[tuple[str, str]] = set()
        if skip_existing:
            existing_periods = self.get_existing_periods(agent_id, records)
        
        for record in records:
            metric_name = record.get("metric_name", "unknown")
            period = record.get("period", "")
            
            # Skip if already exists
            if skip_existing and (metric_name, period) in existing_periods:
                skipped += 1
                continue
                
            dp = self.save_data_point(
                agent_id=agent_id,
                metric_name=metric_name,
                value=record.get("value"),
                period=period,
                source=record.get("source"),
                geography=record.get("geography"),
                unit=record.get("unit"),
                value_text=record.get("value_text"),
                metadata={k: v for k, v in record.items() 
                         if k not in ("metric_name", "value", "period", "source", "geography", "unit", "value_text")},
            )
            data_points.append(dp)
        return data_points, skipped

    def get_existing_periods(
        self,
        agent_id: int,
        records: list[dict[str, Any]],
    ) -> set[tuple[str, str]]:
        """
        Get set of (metric_name, period) tuples that already exist in DB.
        
        Used for deduplication before saving new records.
        """
        # Extract unique metric names from records
        metric_names = {r.get("metric_name", "unknown") for r in records}
        
        stmt = (
            select(DataPoint.metric_name, DataPoint.period)
            .where(DataPoint.agent_id == agent_id)
            .where(DataPoint.metric_name.in_(metric_names))
        )
        result = self.session.execute(stmt)
        return {(row.metric_name, row.period) for row in result}

    def get_latest(self, agent_id: int, metric_name: str) -> DataPoint | None:
        """Get the most recent data point for a metric by period (not by collection time)."""
        stmt = (
            select(DataPoint)
            .where(DataPoint.agent_id == agent_id)
            .where(DataPoint.metric_name == metric_name)
            .order_by(DataPoint.period.desc())
            .limit(1)
        )
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()

    def get_timeseries(
        self,
        agent_id: int,
        metric_name: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
    ) -> list[DataPoint]:
        """Get time series data for a metric."""
        stmt = (
            select(DataPoint)
            .where(DataPoint.agent_id == agent_id)
            .where(DataPoint.metric_name == metric_name)
        )
        
        if start_date:
            stmt = stmt.where(DataPoint.timestamp >= start_date)
        if end_date:
            stmt = stmt.where(DataPoint.timestamp <= end_date)
            
        stmt = stmt.order_by(DataPoint.timestamp.desc()).limit(limit)
        
        result = self.session.execute(stmt)
        return list(result.scalars().all())


class AgentRepository:
    """Repository for Agent operations."""

    def __init__(self, session: Session):
        self.session = session

    def get_or_create(self, name: str, agent_type: str, description: str = "") -> Agent:
        """Get an existing agent or create a new one."""
        stmt = select(Agent).where(Agent.name == name)
        result = self.session.execute(stmt)
        agent = result.scalar_one_or_none()
        
        if agent is None:
            agent = Agent(
                name=name,
                agent_type=agent_type,
                description=description,
                enabled=True,
            )
            self.session.add(agent)
            self.session.flush()
            
        return agent

    def get_by_name(self, name: str) -> Agent | None:
        """Get an agent by name."""
        stmt = select(Agent).where(Agent.name == name)
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()


class CollectionRunRepository:
    """Repository for CollectionRun operations."""

    def __init__(self, session: Session):
        self.session = session

    def start_run(self, agent_id: int) -> CollectionRun:
        """Start a new collection run."""
        run = CollectionRun(
            agent_id=agent_id,
            started_at=datetime.utcnow(),
            status="running",
        )
        self.session.add(run)
        self.session.flush()
        return run

    def complete_run(
        self,
        run: CollectionRun,
        status: str,
        records_collected: int,
        errors: list[str] | None = None,
    ) -> CollectionRun:
        """Complete a collection run."""
        run.completed_at = datetime.utcnow()
        run.status = status
        run.records_collected = records_collected
        run.errors = errors or []
        self.session.flush()
        return run


class DocumentRepository:
    """
    Repository for Document operations.
    
    Handles storing long-form documents with automatic chunking for LLM retrieval.
    """

    def __init__(self, session: Session):
        self.session = session
        # Default chunking parameters
        self.chunk_size = 1000  # Target characters per chunk
        self.chunk_overlap = 200  # Overlap between chunks

    def save_document(
        self,
        agent_id: int,
        document_type: str,
        title: str,
        content: str,
        external_id: str | None = None,
        source_url: str | None = None,
        published_at: datetime | None = None,
        summary: str | None = None,
        extra_data: dict[str, Any] | None = None,
        sections: dict[str, str] | None = None,
    ) -> Document:
        """
        Save a document and automatically create chunks for LLM retrieval.
        
        Args:
            agent_id: The agent that collected this document
            document_type: Type of document (e.g., "rba_minutes")
            title: Document title
            content: Full document text
            external_id: External identifier for deduplication
            source_url: URL where document was collected from
            published_at: When the document was originally published
            summary: Optional summary of the document
            extra_data: Structured metadata for filtering
            sections: Optional dict of section_name -> section_content for section-aware chunking
            
        Returns:
            The saved Document with chunks
        """
        # Check for existing document
        if external_id:
            existing = self.get_by_external_id(document_type, external_id)
            if existing:
                # Update existing document
                existing.title = title
                existing.content = content
                existing.source_url = source_url
                existing.published_at = published_at
                existing.summary = summary
                existing.extra_data = extra_data or {}
                existing.updated_at = datetime.utcnow()
                
                # Delete old chunks and recreate
                for chunk in existing.chunks:
                    self.session.delete(chunk)
                self.session.flush()
                
                # Create new chunks
                self._create_chunks(existing, content, sections)
                self.session.flush()
                return existing
        
        # Create new document
        doc = Document(
            agent_id=agent_id,
            document_type=document_type,
            external_id=external_id,
            title=title,
            content=content,
            source_url=source_url,
            published_at=published_at,
            summary=summary,
            extra_data=extra_data or {},
            collected_at=datetime.utcnow(),
        )
        self.session.add(doc)
        self.session.flush()
        
        # Create chunks
        self._create_chunks(doc, content, sections)
        self.session.flush()
        
        return doc

    def _create_chunks(
        self,
        document: Document,
        content: str,
        sections: dict[str, str] | None = None,
    ) -> list[DocumentChunk]:
        """
        Create chunks from document content.
        
        If sections are provided, chunks are created per-section to preserve context.
        Otherwise, content is split with overlap.
        """
        chunks = []
        chunk_index = 0
        
        if sections:
            # Section-aware chunking
            for section_name, section_content in sections.items():
                if not section_content:
                    continue
                    
                section_chunks = self._split_text(section_content)
                for chunk_text in section_chunks:
                    chunk = DocumentChunk(
                        document_id=document.id,
                        chunk_index=chunk_index,
                        content=chunk_text,
                        section_name=section_name,
                        token_count=self._estimate_tokens(chunk_text),
                    )
                    self.session.add(chunk)
                    chunks.append(chunk)
                    chunk_index += 1
        else:
            # Simple chunking with overlap
            text_chunks = self._split_text(content)
            char_pos = 0
            
            for chunk_text in text_chunks:
                chunk = DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk_index,
                    content=chunk_text,
                    char_start=char_pos,
                    char_end=char_pos + len(chunk_text),
                    token_count=self._estimate_tokens(chunk_text),
                )
                self.session.add(chunk)
                chunks.append(chunk)
                chunk_index += 1
                char_pos += len(chunk_text) - self.chunk_overlap
        
        return chunks

    def _split_text(self, text: str) -> list[str]:
        """
        Split text into overlapping chunks.
        
        Tries to split at sentence boundaries when possible.
        """
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            if end >= len(text):
                chunks.append(text[start:])
                break
            
            # Try to find a sentence boundary (. ! ?) near the end
            best_split = end
            for sep in ['. ', '! ', '? ', '\n\n', '\n', ' ']:
                # Look for separator in the last 20% of the chunk
                search_start = start + int(self.chunk_size * 0.8)
                idx = text.rfind(sep, search_start, end)
                if idx != -1:
                    best_split = idx + len(sep)
                    break
            
            chunks.append(text[start:best_split])
            start = best_split - self.chunk_overlap
            
            # Prevent infinite loop
            if start >= len(text) - self.chunk_overlap:
                if best_split < len(text):
                    chunks.append(text[best_split:])
                break
        
        return chunks

    def _estimate_tokens(self, text: str) -> int:
        """Rough estimate of token count (avg 4 chars per token for English)."""
        return len(text) // 4

    def get_by_external_id(self, document_type: str, external_id: str) -> Document | None:
        """Get a document by its type and external ID."""
        stmt = (
            select(Document)
            .where(Document.document_type == document_type)
            .where(Document.external_id == external_id)
        )
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()

    def get_by_type(
        self,
        document_type: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Document]:
        """Get documents by type, ordered by published date."""
        stmt = (
            select(Document)
            .where(Document.document_type == document_type)
            .order_by(Document.published_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    def get_chunks_for_retrieval(
        self,
        document_type: str | None = None,
        section_name: str | None = None,
        limit: int = 20,
    ) -> list[DocumentChunk]:
        """
        Get document chunks for LLM retrieval.
        
        This is a basic implementation. For production, you'd want:
        - Vector similarity search using embeddings
        - Keyword/BM25 search
        - Hybrid search combining both
        """
        stmt = select(DocumentChunk).join(Document)
        
        if document_type:
            stmt = stmt.where(Document.document_type == document_type)
        if section_name:
            stmt = stmt.where(DocumentChunk.section_name == section_name)
        
        stmt = stmt.order_by(Document.published_at.desc()).limit(limit)
        
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    def search_documents(
        self,
        query: str,
        document_type: str | None = None,
        limit: int = 10,
    ) -> list[Document]:
        """
        Basic text search in documents.
        
        For production, use PostgreSQL full-text search or vector search.
        """
        stmt = select(Document).where(Document.content.ilike(f"%{query}%"))
        
        if document_type:
            stmt = stmt.where(Document.document_type == document_type)
        
        stmt = stmt.order_by(Document.published_at.desc()).limit(limit)
        
        result = self.session.execute(stmt)
        return list(result.scalars().all())


class ChatRepository:
    """Repository for chat thread and message operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_thread(
        self,
        thread_id: str,
        topic: str | None = None,
    ) -> ChatThread:
        """Create a new chat thread."""
        thread = ChatThread(
            thread_id=thread_id,
            topic=topic,
        )
        self.session.add(thread)
        self.session.flush()
        return thread
    
    def get_thread_by_id(self, thread_id: str) -> ChatThread | None:
        """Get a thread by its string ID."""
        stmt = select(ChatThread).where(ChatThread.thread_id == thread_id)
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    def get_or_create_thread(
        self,
        thread_id: str,
        topic: str | None = None,
    ) -> tuple[ChatThread, bool]:
        """
        Get existing thread or create new one.
        
        Returns:
            Tuple of (thread, created) where created is True if new thread was created
        """
        thread = self.get_thread_by_id(thread_id)
        if thread:
            return thread, False
        return self.create_thread(thread_id, topic), True
    
    def list_threads(
        self,
        active_only: bool = True,
        limit: int = 20,
    ) -> list[ChatThread]:
        """List recent chat threads."""
        stmt = select(ChatThread)
        
        if active_only:
            stmt = stmt.where(ChatThread.is_active == True)
        
        stmt = stmt.order_by(ChatThread.updated_at.desc()).limit(limit)
        
        result = self.session.execute(stmt)
        return list(result.scalars().all())
    
    def update_thread_topic(self, thread_id: str, topic: str) -> ChatThread | None:
        """Update the topic of a thread."""
        thread = self.get_thread_by_id(thread_id)
        if thread:
            thread.topic = topic
            thread.updated_at = datetime.utcnow()
            self.session.flush()
        return thread
    
    def update_thread_summary(self, thread_id: str, summary: str) -> ChatThread | None:
        """Update the auto-generated summary of a thread."""
        thread = self.get_thread_by_id(thread_id)
        if thread:
            thread.summary = summary
            thread.updated_at = datetime.utcnow()
            self.session.flush()
        return thread
    
    def archive_thread(self, thread_id: str) -> ChatThread | None:
        """Mark a thread as inactive/archived."""
        thread = self.get_thread_by_id(thread_id)
        if thread:
            thread.is_active = False
            thread.updated_at = datetime.utcnow()
            self.session.flush()
        return thread
    
    def add_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        agent_name: str | None = None,
        confidence: float | None = None,
        sources_used: list[str] | None = None,
        tool_calls: int | None = None,
    ) -> ChatMessage | None:
        """Add a message to a thread."""
        thread = self.get_thread_by_id(thread_id)
        if not thread:
            return None
        
        # Get next sequence number
        sequence_num = thread.message_count
        
        message = ChatMessage(
            thread_id=thread.id,
            role=role,
            content=content,
            sequence_num=sequence_num,
            agent_name=agent_name,
            confidence=confidence,
            sources_used=sources_used or [],
            tool_calls=tool_calls,
        )
        self.session.add(message)
        
        # Update thread stats
        thread.message_count = sequence_num + 1
        thread.updated_at = datetime.utcnow()
        
        self.session.flush()
        return message
    
    def get_thread_messages(
        self,
        thread_id: str,
        limit: int | None = None,
    ) -> list[ChatMessage]:
        """Get all messages for a thread in order."""
        thread = self.get_thread_by_id(thread_id)
        if not thread:
            return []
        
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.thread_id == thread.id)
            .order_by(ChatMessage.sequence_num)
        )
        
        if limit:
            stmt = stmt.limit(limit)
        
        result = self.session.execute(stmt)
        return list(result.scalars().all())
    
    def get_recent_messages(
        self,
        thread_id: str,
        count: int = 10,
    ) -> list[ChatMessage]:
        """Get the most recent N messages for context window."""
        thread = self.get_thread_by_id(thread_id)
        if not thread:
            return []
        
        # Get last N messages by sequence
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.thread_id == thread.id)
            .order_by(ChatMessage.sequence_num.desc())
            .limit(count)
        )
        
        result = self.session.execute(stmt)
        messages = list(result.scalars().all())
        
        # Reverse to get chronological order
        return list(reversed(messages))
    
    def delete_thread(self, thread_id: str) -> bool:
        """Delete a thread and all its messages."""
        thread = self.get_thread_by_id(thread_id)
        if thread:
            self.session.delete(thread)
            self.session.flush()
            return True
        return False
