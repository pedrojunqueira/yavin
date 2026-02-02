"""
Tests for data collectors.
"""

import pytest

from yavin.collectors.sources.abs import ABSBuildingApprovalsCollector


class TestABSCollector:
    """Tests for the ABS Building Approvals collector."""

    def test_collector_has_name(self):
        """Collector should have a name."""
        collector = ABSBuildingApprovalsCollector()
        assert collector.name == "ABS Building Approvals"

    def test_collector_has_source_url(self):
        """Collector should have a source URL."""
        collector = ABSBuildingApprovalsCollector()
        assert "abs.gov.au" in collector.source_url

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_collect_returns_data(self):
        """
        Integration test: Collector should fetch real data.
        
        This test makes actual API calls - run with:
        pytest -m integration
        """
        collector = ABSBuildingApprovalsCollector()
        result = await collector.collect()

        assert result.collector_name == "ABS Building Approvals"
        # Note: We don't assert success because API might be down
        # but we verify the structure is correct
        assert hasattr(result, "records")
        assert hasattr(result, "success")
