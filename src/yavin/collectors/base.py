"""
Base class for data collectors.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CollectorResult:
    """Result of a single collector run."""

    collector_name: str
    source_url: str
    success: bool
    records: list[dict[str, Any]]
    collected_at: datetime
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseCollector(ABC):
    """
    Abstract base class for data collectors.
    
    Each collector is responsible for fetching data from a single source.
    """

    name: str = "Base Collector"
    source_url: str = ""

    @abstractmethod
    async def collect(self) -> CollectorResult:
        """
        Fetch data from the source.
        
        Returns:
            CollectorResult with the fetched data
        """
        pass

    @abstractmethod
    def normalize(self, raw_data: Any) -> list[dict[str, Any]]:
        """
        Normalize raw data into a standard format.
        
        Args:
            raw_data: The raw data from the source
            
        Returns:
            List of normalized records
        """
        pass
