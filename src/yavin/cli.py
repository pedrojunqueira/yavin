"""
Command-line interface for Yavin.
"""

import asyncio
from datetime import datetime
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from yavin import __version__
from yavin.agents.specialized.housing import HousingAgent

app = typer.Typer(
    name="yavin",
    help="Multi-agent system for monitoring trends that fade from media attention.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def version():
    """Show the version."""
    console.print(f"[bold blue]Yavin[/] version {__version__}")


@app.command()
def agents():
    """List available agents."""
    table = Table(title="Available Agents")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Status", style="green")

    # TODO: Load from registry
    housing = HousingAgent()
    caps = housing.get_capabilities()
    table.add_row(caps.name, caps.description, "✓ Active")

    console.print(table)


@app.command()
def ask(
    question: str = typer.Argument(..., help="Your question"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Specific agent to query"),
):
    """Ask a question to the agents."""

    async def _ask():
        console.print(f"\n[bold]Question:[/] {question}\n")

        if agent == "housing" or agent is None:
            housing_agent = HousingAgent()
            response = await housing_agent.query(question)

            console.print(
                Panel(
                    response.content,
                    title=f"[bold cyan]{response.agent_name}[/]",
                    border_style="blue",
                )
            )
        else:
            console.print(f"[red]Unknown agent: {agent}[/]")

    asyncio.run(_ask())


@app.command()
def collect(
    agent: str = typer.Argument(..., help="Agent to run collection for"),
):
    """Run data collection for an agent."""

    async def _collect():
        if agent == "housing":
            housing_agent = HousingAgent()
            console.print(f"[bold]Running collection for {housing_agent.name}...[/]\n")

            result = await housing_agent.collect()

            if result.status.value == "success":
                console.print(f"[green]✓ Collection completed successfully[/]")
            else:
                console.print(f"[red]✗ Collection failed[/]")

            console.print(f"  Records collected: {result.records_collected}")
            console.print(f"  Duration: {result.completed_at - result.started_at}")

            if result.errors:
                console.print("\n[red]Errors:[/]")
                for error in result.errors:
                    console.print(f"  - {error}")
        else:
            console.print(f"[red]Unknown agent: {agent}[/]")

    asyncio.run(_collect())


@app.command()
def test_abs(
    save: bool = typer.Option(False, "--save", "-s", help="Save data to database"),
    force: bool = typer.Option(False, "--force", "-f", help="Force fetch even if data exists in DB"),
):
    """Test the ABS Building Approvals collector and optionally save to DB."""
    from yavin.collectors.sources.abs import ABSBuildingApprovalsHistoryCollector
    from yavin.db.session import SyncSessionLocal, init_db_sync
    from yavin.db.repository import (
        AgentRepository,
        DataPointRepository,
        CollectionRunRepository,
    )

    async def _test():
        console.print("[bold]ABS Building Approvals Collection[/]\n")

        # Check database first
        init_db_sync()
        
        with SyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            agent = agent_repo.get_or_create(
                name="housing",
                agent_type="specialized",
                description="Australian Housing Market Agent",
            )
            
            dp_repo = DataPointRepository(session)
            
            # Check what data we already have
            existing = dp_repo.get_latest(agent.id, "housing_approvals_total")
            
            if existing and not force:
                console.print(f"[cyan]Data already in database:[/]")
                console.print(f"  Latest period: [bold]{existing.period}[/]")
                console.print(f"  Latest value: [bold]{existing.value:,.0f} dwelling units[/]")
                console.print(f"  Collected at: {existing.created_at.strftime('%Y-%m-%d %H:%M')}")
                console.print(f"\n[dim]Use --force to fetch from ABS anyway[/]")
                return
            
            session.commit()

        # Fetch from ABS
        console.print("[cyan]Fetching Building Approvals data from ABS...[/]")
        collector = ABSBuildingApprovalsHistoryCollector()
        result = await collector.collect()

        if result.success:
            console.print(f"[green]✓ Successfully fetched data[/]")
            console.print(f"  Records: {len(result.records)}\n")

            if result.records:
                # Show last 12 records
                table = Table(title="Building Approvals (Australia)")
                table.add_column("Period", style="cyan")
                table.add_column("Dwelling Units", style="green")

                # Show last 12 records
                for record in result.records[-12:]:
                    table.add_row(
                        record.get("period", "?"),
                        f"{record.get('value', 0):,.0f}",
                    )

                console.print(table)
        else:
            console.print(f"[red]✗ Collection failed: {result.error_message}[/]")
            return

        # Save to database if requested
        if save:
            console.print("\n[bold]Saving to database...[/]")
            try:
                with SyncSessionLocal() as session:
                    # Get or create Housing agent
                    agent_repo = AgentRepository(session)
                    agent = agent_repo.get_or_create(
                        name="housing",
                        agent_type="specialized",
                        description="Australian Housing Market Agent",
                    )

                    # Start collection run
                    run_repo = CollectionRunRepository(session)
                    run = run_repo.start_run(agent.id)

                    # Save data points (skip existing records)
                    dp_repo = DataPointRepository(session)
                    saved, skipped = dp_repo.save_data_points(agent.id, result.records)

                    # Complete the run
                    run_repo.complete_run(
                        run,
                        status="success",
                        records_collected=len(saved),
                    )

                    session.commit()

                    console.print(f"[green]✓ Saved {len(saved)} new records to database[/]")
                    if skipped > 0:
                        console.print(f"  [dim]Skipped {skipped} existing records[/]")
                    console.print(f"  Agent ID: {agent.id}")
                    console.print(f"  Collection Run ID: {run.id}")

            except Exception as e:
                console.print(f"[red]✗ Failed to save: {e}[/]")
                raise

    asyncio.run(_test())


@app.command()
def test_rba(
    save: bool = typer.Option(False, "--save", "-s", help="Save data to database"),
    force: bool = typer.Option(False, "--force", "-f", help="Force fetch even if data exists in DB"),
):
    """Test the RBA interest rate collector and optionally save to DB."""
    from yavin.collectors.sources.rba import (
        RBAInterestRateCollector,
        RBAInterestRateHistoryCollector,
    )
    from yavin.db.session import SyncSessionLocal, init_db_sync
    from yavin.db.repository import (
        AgentRepository,
        DataPointRepository,
        CollectionRunRepository,
    )

    async def _test():
        console.print("[bold]RBA Interest Rate Collection[/]\n")

        # Check database first
        init_db_sync()
        
        with SyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            agent = agent_repo.get_or_create(
                name="housing",
                agent_type="specialized",
                description="Australian Housing Market Agent",
            )
            
            dp_repo = DataPointRepository(session)
            
            # Check what data we already have
            existing = dp_repo.get_latest(agent.id, "interest_rate_cash")
            
            if existing and not force:
                console.print(f"[cyan]Data already in database:[/]")
                console.print(f"  Latest period: [bold]{existing.period}[/]")
                console.print(f"  Latest rate: [bold]{existing.value}%[/]")
                console.print(f"  Collected at: {existing.created_at.strftime('%Y-%m-%d %H:%M')}")
                console.print(f"\n[dim]Use --force to fetch from RBA anyway[/]")
                return
            
            session.commit()

        # If no data or force=True, fetch from RBA
        console.print("[cyan]1. Current Cash Rate[/]")
        current_collector = RBAInterestRateCollector()
        current_result = await current_collector.collect()

        if current_result.success:
            console.print(f"[green]✓ Successfully fetched current rate[/]")
            if current_result.records:
                record = current_result.records[0]
                console.print(f"  Rate: [bold]{record.get('value')}%[/]")
                console.print(f"  Period: {record.get('period')}")
        else:
            console.print(f"[red]✗ Failed: {current_result.error_message}[/]")

        console.print()

        # Test historical rates collector
        console.print("[cyan]2. Historical Rates (last 12 months)[/]")
        history_collector = RBAInterestRateHistoryCollector()
        history_result = await history_collector.collect()

        if history_result.success:
            console.print(f"[green]✓ Successfully fetched historical data[/]")
            console.print(f"  Records: {len(history_result.records)}\n")

            if history_result.records:
                # Show last 12 records
                table = Table(title="Cash Rate History")
                table.add_column("Period", style="cyan")
                table.add_column("Rate (%)", style="green")

                for record in history_result.records[-12:]:
                    table.add_row(
                        record.get("period", "?"),
                        str(record.get("value", "?")),
                    )

                console.print(table)
        else:
            console.print(f"[red]✗ Failed: {history_result.error_message}[/]")

        # Save to database if requested
        if save:
            console.print("\n[bold]Saving to database...[/]")
            try:
                with SyncSessionLocal() as session:
                    # Get or create Housing agent
                    agent_repo = AgentRepository(session)
                    agent = agent_repo.get_or_create(
                        name="housing",
                        agent_type="specialized",
                        description="Australian Housing Market Agent",
                    )

                    # Start collection run
                    run_repo = CollectionRunRepository(session)
                    run = run_repo.start_run(agent.id)

                    # Save data points (skip existing records)
                    dp_repo = DataPointRepository(session)
                    all_records = []

                    if current_result.success and current_result.records:
                        all_records.extend(current_result.records)

                    if history_result.success and history_result.records:
                        all_records.extend(history_result.records)

                    saved, skipped = dp_repo.save_data_points(agent.id, all_records)

                    # Complete the run
                    errors = []
                    if not current_result.success:
                        errors.append(current_result.error_message or "Current rate fetch failed")
                    if not history_result.success:
                        errors.append(history_result.error_message or "History fetch failed")

                    run_repo.complete_run(
                        run,
                        status="success" if not errors else "partial",
                        records_collected=len(saved),
                        errors=errors if errors else None,
                    )

                    session.commit()

                    console.print(f"[green]✓ Saved {len(saved)} new records to database[/]")
                    if skipped > 0:
                        console.print(f"  [dim]Skipped {skipped} existing records[/]")
                    console.print(f"  Agent ID: {agent.id}")
                    console.print(f"  Collection Run ID: {run.id}")

            except Exception as e:
                console.print(f"[red]✗ Failed to save: {e}[/]")
                raise

    asyncio.run(_test())


@app.command()
def test_rba_minutes(
    year: int = typer.Option(None, "--year", "-y", help="Year to fetch minutes for (default: current year)"),
    save: bool = typer.Option(False, "--save", "-s", help="Save data to database"),
):
    """Test the RBA Meeting Minutes collector."""
    from yavin.collectors.sources.rba import RBAMinutesCollector
    from datetime import datetime as dt

    async def _test():
        target_year = year or dt.now().year
        console.print(f"[bold]RBA Meeting Minutes Collection - {target_year}[/]\n")

        collector = RBAMinutesCollector()
        result = await collector.collect(year=target_year)

        if result.success:
            console.print(f"[green]✓ Successfully fetched minutes[/]")
            console.print(f"  Meetings found: {len(result.records)}\n")

            if result.records:
                table = Table(title=f"RBA Meeting Minutes - {target_year}")
                table.add_column("Meeting Date", style="cyan")
                table.add_column("Cash Rate", style="green")
                table.add_column("Decision", style="white", max_width=60)

                for record in result.records:
                    cash_rate = record.get("cash_rate_decision")
                    rate_str = f"{cash_rate}%" if cash_rate else "N/A"
                    decision = record.get("decision_text", "")[:60]
                    if len(record.get("decision_text", "")) > 60:
                        decision += "..."
                    
                    table.add_row(
                        record.get("meeting_date", "?"),
                        rate_str,
                        decision,
                    )

                console.print(table)
                
                # Show preview of latest minutes content
                if result.records:
                    latest = result.records[0]
                    console.print(f"\n[bold cyan]Latest Meeting ({latest.get('meeting_date')}):[/]")
                    console.print(f"  Members: {latest.get('members_participating', 'N/A')[:100]}...")
                    
                    sections = latest.get("sections", {})
                    if sections:
                        console.print(f"\n  [dim]Sections available:[/]")
                        for section_name in sections.keys():
                            console.print(f"    - {section_name}")
        else:
            console.print(f"[red]✗ Collection failed: {result.error_message}[/]")

        # Save to database if requested
        if save and result.success and result.records:
            from yavin.db.session import SyncSessionLocal, init_db_sync
            from yavin.db.repository import AgentRepository, DocumentRepository
            
            console.print("\n[bold]Saving minutes to database...[/]")
            try:
                init_db_sync()
                
                with SyncSessionLocal() as session:
                    # Get or create the housing agent (RBA minutes are relevant to housing)
                    agent_repo = AgentRepository(session)
                    agent = agent_repo.get_or_create(
                        name="housing",
                        agent_type="specialized",
                        description="Australian Housing Market Agent",
                    )
                    
                    doc_repo = DocumentRepository(session)
                    saved_count = 0
                    updated_count = 0
                    
                    for record in result.records:
                        meeting_date = record.get("meeting_date")
                        
                        # Check if already exists
                        existing = doc_repo.get_by_external_id("rba_minutes", meeting_date)
                        
                        # Build document extra_data
                        extra_data = {
                            "cash_rate_decision": record.get("cash_rate_decision"),
                            "members_participating": record.get("members_participating"),
                            "decision_text": record.get("decision_text"),
                        }
                        
                        # Parse published date
                        published_at = None
                        if meeting_date:
                            try:
                                published_at = dt.strptime(meeting_date, "%Y-%m-%d")
                            except ValueError:
                                pass
                        
                        # Save document with section-aware chunking
                        doc_repo.save_document(
                            agent_id=agent.id,
                            document_type="rba_minutes",
                            external_id=meeting_date,
                            title=f"RBA Monetary Policy Board Minutes - {meeting_date}",
                            content=record.get("full_text", ""),
                            source_url=record.get("source_url"),
                            published_at=published_at,
                            summary=record.get("decision_text"),
                            extra_data=extra_data,
                            sections=record.get("sections"),
                        )
                        
                        if existing:
                            updated_count += 1
                        else:
                            saved_count += 1
                    
                    session.commit()
                    
                    console.print(f"[green]✓ Saved {saved_count} new documents[/]")
                    if updated_count > 0:
                        console.print(f"  [dim]Updated {updated_count} existing documents[/]")
                    
                    # Show chunk info for latest document
                    latest_date = result.records[0].get("meeting_date")
                    latest_doc = doc_repo.get_by_external_id("rba_minutes", latest_date)
                    if latest_doc:
                        console.print(f"\n  [cyan]Latest document chunks: {len(latest_doc.chunks)}[/]")
                        for chunk in latest_doc.chunks[:3]:
                            preview = chunk.content[:80].replace('\n', ' ')
                            console.print(f"    [{chunk.section_name or 'main'}] {preview}...")
                    
            except Exception as e:
                console.print(f"[red]✗ Failed to save: {e}[/]")
                raise

    asyncio.run(_test())


@app.command()
def init_db():
    """Initialize the database schema."""
    from yavin.db.session import init_db_sync

    console.print("[bold]Initializing database...[/]")
    try:
        init_db_sync()
        console.print("[green]✓ Database schema created successfully[/]")
    except Exception as e:
        console.print(f"[red]✗ Failed to initialize database: {e}[/]")
        raise


@app.command()
def test_awe(
    save: bool = typer.Option(False, "--save", "-s", help="Save data to database"),
    force: bool = typer.Option(False, "--force", "-f", help="Force fetch even if data exists in DB"),
):
    """Test the ABS Average Weekly Earnings collector and optionally save to DB."""
    from yavin.collectors.sources.abs import ABSWeeklyEarningsCollector
    from yavin.db.session import SyncSessionLocal, init_db_sync
    from yavin.db.repository import (
        AgentRepository,
        DataPointRepository,
        CollectionRunRepository,
    )

    async def _test():
        console.print("[bold]ABS Average Weekly Earnings Collection[/]\n")

        # Check database first
        init_db_sync()
        
        with SyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            agent = agent_repo.get_or_create(
                name="housing",
                agent_type="specialized",
                description="Australian Housing Market Agent",
            )
            
            dp_repo = DataPointRepository(session)
            
            # Check what data we already have (use one of the main metrics)
            existing = dp_repo.get_latest(agent.id, "fulltime_adultavg_weekly_ordinary_earnings")
            
            if existing and not force:
                console.print(f"[cyan]Data already in database:[/]")
                console.print(f"  Latest period: [bold]{existing.period}[/]")
                console.print(f"  Latest value: [bold]${existing.value:,.2f}[/]")
                console.print(f"  Collected at: {existing.created_at.strftime('%Y-%m-%d %H:%M')}")
                console.print(f"\n[dim]Use --force to fetch from ABS anyway[/]")
                return
            
            session.commit()

        # Fetch from ABS
        console.print("[cyan]Fetching Average Weekly Earnings data from ABS...[/]")
        collector = ABSWeeklyEarningsCollector()
        result = await collector.collect()

        if result.success:
            console.print(f"[green]✓ Successfully fetched data[/]")
            console.print(f"  Records: {len(result.records)}\n")

            if result.records:
                # Group by metric name to show summary
                metrics = {}
                for record in result.records:
                    metric = record.get("metric_name", "unknown")
                    if metric not in metrics:
                        metrics[metric] = []
                    metrics[metric].append(record)

                # Show summary for each metric
                for metric_name, recs in sorted(metrics.items()):
                    latest = recs[-1] if recs else None
                    if latest:
                        console.print(
                            f"  [cyan]{metric_name}[/]: ${latest['value']:,.2f} ({latest['period']})"
                            f" - {len(recs)} periods"
                        )

                # Show last 12 records for full-time ordinary earnings
                table = Table(title="Full-Time Adult Average Weekly Ordinary Earnings (Trend)")
                table.add_column("Period", style="cyan")
                table.add_column("Earnings (AUD)", style="green")

                # Filter to the main metric
                main_records = [
                    r for r in result.records
                    if "ordinary" in r.get("metric_name", "") and "fulltime" in r.get("metric_name", "")
                    and "_male" not in r.get("metric_name", "") and "_female" not in r.get("metric_name", "")
                ]
                for record in main_records[-12:]:
                    table.add_row(
                        record.get("period", "?"),
                        f"${record.get('value', 0):,.2f}",
                    )

                console.print()
                console.print(table)
        else:
            console.print(f"[red]✗ Collection failed: {result.error_message}[/]")
            return

        # Save to database if requested
        if save:
            console.print("\n[bold]Saving to database...[/]")
            try:
                with SyncSessionLocal() as session:
                    # Get or create Housing agent
                    agent_repo = AgentRepository(session)
                    agent = agent_repo.get_or_create(
                        name="housing",
                        agent_type="specialized",
                        description="Australian Housing Market Agent",
                    )

                    # Start collection run
                    run_repo = CollectionRunRepository(session)
                    run = run_repo.start_run(agent.id)

                    # Save data points (skip existing records)
                    dp_repo = DataPointRepository(session)
                    saved, skipped = dp_repo.save_data_points(agent.id, result.records)

                    # Complete the run
                    run_repo.complete_run(
                        run,
                        status="success",
                        records_collected=len(saved),
                    )

                    session.commit()

                    console.print(f"[green]✓ Saved {len(saved)} new records to database[/]")
                    if skipped > 0:
                        console.print(f"  [dim]Skipped {skipped} existing records[/]")
                    console.print(f"  Agent ID: {agent.id}")
                    console.print(f"  Collection Run ID: {run.id}")

            except Exception as e:
                console.print(f"[red]✗ Failed to save: {e}[/]")
                raise

    asyncio.run(_test())


@app.command()
def test_lending(
    save: bool = typer.Option(False, "--save", "-s", help="Save data to database"),
    force: bool = typer.Option(False, "--force", "-f", help="Force fetch even if data exists in DB"),
):
    """Test the ABS Lending Indicators collector and optionally save to DB."""
    from yavin.collectors.sources.abs import ABSLendingIndicatorsCollector
    from yavin.db.session import SyncSessionLocal, init_db_sync
    from yavin.db.repository import (
        AgentRepository,
        DataPointRepository,
        CollectionRunRepository,
    )

    async def _test():
        console.print("[bold]ABS Lending Indicators Collection[/]\n")

        # Check database first
        init_db_sync()
        
        with SyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            agent = agent_repo.get_or_create(
                name="housing",
                agent_type="specialized",
                description="Australian Housing Market Agent",
            )
            
            dp_repo = DataPointRepository(session)
            
            # Check what data we already have
            existing = dp_repo.get_latest(agent.id, "avg_loan_size_total")
            
            if existing and not force:
                console.print(f"[cyan]Data already in database:[/]")
                console.print(f"  Latest period: [bold]{existing.period}[/]")
                console.print(f"  Avg loan size (total): [bold]${existing.value:,.0f}k[/]")
                console.print(f"  Collected at: {existing.created_at.strftime('%Y-%m-%d %H:%M')}")
                console.print(f"\n[dim]Use --force to fetch from ABS anyway[/]")
                return
            
            session.commit()

        # Fetch from ABS
        console.print("[cyan]Fetching Lending Indicators data from ABS...[/]")
        collector = ABSLendingIndicatorsCollector()
        result = await collector.collect()

        if result.success:
            console.print(f"[green]✓ Successfully fetched data[/]")
            console.print(f"  Records: {len(result.records)}\n")

            if result.records:
                # Group by metric name to show summary
                metrics = {}
                for record in result.records:
                    metric = record.get("metric_name", "unknown")
                    if metric not in metrics:
                        metrics[metric] = []
                    metrics[metric].append(record)

                # Show average loan size metrics
                console.print("[bold]Average Loan Sizes (Latest):[/]")
                for metric_name in ["avg_loan_size_total", "avg_loan_size_owner_occupier", 
                                    "avg_loan_size_investor", "avg_loan_size_first_home_buyer"]:
                    if metric_name in metrics:
                        # Sort by period to get the actual latest
                        sorted_records = sorted(metrics[metric_name], key=lambda x: x.get("period", ""))
                        if sorted_records:
                            latest = sorted_records[-1]
                            label = metric_name.replace("avg_loan_size_", "").replace("_", " ").title()
                            console.print(f"  {label}: [bold]${latest['value']:,.0f}k[/] ({latest['period']})")
                
                console.print()
                
                # Show loan commitments
                console.print("[bold]Loan Commitments (Latest):[/]")
                for metric_name in ["loan_commitments_total_number", "loan_commitments_total_value"]:
                    if metric_name in metrics:
                        latest = metrics[metric_name][-1]
                        if "number" in metric_name:
                            console.print(f"  Total Number: [bold]{latest['value']:,.0f}[/] ({latest['period']})")
                        else:
                            console.print(f"  Total Value: [bold]${latest['value']:,.0f}M[/] ({latest['period']})")

                # Show average loan size trend table
                table = Table(title="Average Loan Size - Total (Last 12 Quarters)")
                table.add_column("Period", style="cyan")
                table.add_column("Avg Loan Size", style="green")

                avg_records = metrics.get("avg_loan_size_total", [])
                for record in avg_records[-12:]:
                    table.add_row(
                        record.get("period", "?"),
                        f"${record.get('value', 0):,.0f}k",
                    )

                console.print()
                console.print(table)
        else:
            console.print(f"[red]✗ Collection failed: {result.error_message}[/]")
            return

        # Save to database if requested
        if save:
            console.print("\n[bold]Saving to database...[/]")
            try:
                with SyncSessionLocal() as session:
                    # Get or create Housing agent
                    agent_repo = AgentRepository(session)
                    agent = agent_repo.get_or_create(
                        name="housing",
                        agent_type="specialized",
                        description="Australian Housing Market Agent",
                    )

                    # Start collection run
                    run_repo = CollectionRunRepository(session)
                    run = run_repo.start_run(agent.id)

                    # Save data points (skip existing records)
                    dp_repo = DataPointRepository(session)
                    saved, skipped = dp_repo.save_data_points(agent.id, result.records)

                    # Complete the run
                    run_repo.complete_run(
                        run,
                        status="success",
                        records_collected=len(saved),
                    )

                    session.commit()

                    console.print(f"[green]✓ Saved {len(saved)} new records to database[/]")
                    if skipped > 0:
                        console.print(f"  [dim]Skipped {skipped} existing records[/]")
                    console.print(f"  Agent ID: {agent.id}")
                    console.print(f"  Collection Run ID: {run.id}")

            except Exception as e:
                console.print(f"[red]✗ Failed to save: {e}[/]")
                raise

    asyncio.run(_test())


@app.command()
def test_inflation(
    save: bool = typer.Option(False, "--save", "-s", help="Save data to database"),
    force: bool = typer.Option(False, "--force", "-f", help="Force fetch even if data exists in DB"),
):
    """Test the RBA Inflation (CPI) collector and optionally save to DB."""
    from yavin.collectors.sources.rba import RBAInflationCollector
    from yavin.db.session import SyncSessionLocal, init_db_sync
    from yavin.db.repository import (
        AgentRepository,
        DataPointRepository,
        CollectionRunRepository,
    )

    async def _test():
        console.print("[bold]RBA Inflation (CPI) Collection[/]\n")

        init_db_sync()
        
        with SyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            agent = agent_repo.get_or_create(
                name="housing",
                agent_type="specialized",
                description="Australian Housing Market Agent",
            )
            
            dp_repo = DataPointRepository(session)
            existing = dp_repo.get_latest(agent.id, "inflation_cpi_annual")
            
            if existing and not force:
                console.print(f"[cyan]Data already in database:[/]")
                console.print(f"  Latest period: [bold]{existing.period}[/]")
                console.print(f"  CPI inflation: [bold]{existing.value:.2f}%[/]")
                console.print(f"  Collected at: {existing.created_at.strftime('%Y-%m-%d %H:%M')}")
                console.print(f"\n[dim]Use --force to fetch from RBA anyway[/]")
                return
            
            session.commit()

        console.print("[cyan]Fetching Inflation data from RBA...[/]")
        collector = RBAInflationCollector()
        result = await collector.collect()

        if result.success:
            console.print(f"[green]✓ Successfully fetched data[/]")
            console.print(f"  Records: {len(result.records)}\n")

            if result.records:
                # Group by metric
                metrics = {}
                for record in result.records:
                    metric = record.get("metric_name", "unknown")
                    if metric not in metrics:
                        metrics[metric] = []
                    metrics[metric].append(record)

                # Show latest values
                console.print("[bold]Latest Values:[/]")
                for metric_name in ["inflation_cpi_annual", "inflation_trimmed_mean_annual"]:
                    if metric_name in metrics:
                        sorted_records = sorted(metrics[metric_name], key=lambda x: x.get("period", ""))
                        if sorted_records:
                            latest = sorted_records[-1]
                            label = "CPI (Year-ended)" if "cpi" in metric_name else "Trimmed Mean (Year-ended)"
                            console.print(f"  {label}: [bold]{latest['value']:.2f}%[/] ({latest['period']})")

                # Show trend table
                table = Table(title="Annual CPI Inflation (Last 12 Quarters)")
                table.add_column("Period", style="cyan")
                table.add_column("CPI %", style="green")
                table.add_column("Trimmed Mean %", style="yellow")

                cpi_records = {r["period"]: r["value"] for r in metrics.get("inflation_cpi_annual", [])}
                tm_records = {r["period"]: r["value"] for r in metrics.get("inflation_trimmed_mean_annual", [])}
                
                periods = sorted(set(cpi_records.keys()) | set(tm_records.keys()))[-12:]
                for period in periods:
                    cpi = cpi_records.get(period)
                    tm = tm_records.get(period)
                    table.add_row(
                        period,
                        f"{cpi:.2f}" if cpi else "-",
                        f"{tm:.2f}" if tm else "-",
                    )

                console.print()
                console.print(table)
        else:
            console.print(f"[red]✗ Collection failed: {result.error_message}[/]")
            return

        if save:
            console.print("\n[bold]Saving to database...[/]")
            try:
                with SyncSessionLocal() as session:
                    agent_repo = AgentRepository(session)
                    agent = agent_repo.get_or_create(
                        name="housing",
                        agent_type="specialized",
                        description="Australian Housing Market Agent",
                    )

                    run_repo = CollectionRunRepository(session)
                    run = run_repo.start_run(agent.id)

                    dp_repo = DataPointRepository(session)
                    saved, skipped = dp_repo.save_data_points(agent.id, result.records)

                    run_repo.complete_run(run, status="success", records_collected=len(saved))
                    session.commit()

                    console.print(f"[green]✓ Saved {len(saved)} new records to database[/]")
                    if skipped > 0:
                        console.print(f"  [dim]Skipped {skipped} existing records[/]")
                    console.print(f"  Agent ID: {agent.id}")
                    console.print(f"  Collection Run ID: {run.id}")

            except Exception as e:
                console.print(f"[red]✗ Failed to save: {e}[/]")
                raise

    asyncio.run(_test())


@app.command()
def test_housing_rates(
    save: bool = typer.Option(False, "--save", "-s", help="Save data to database"),
    force: bool = typer.Option(False, "--force", "-f", help="Force fetch even if data exists in DB"),
):
    """Test the RBA Housing Lending Rates (variable rate) collector and optionally save to DB."""
    from yavin.collectors.sources.rba import RBAHousingLendingRatesCollector
    from yavin.db.session import SyncSessionLocal, init_db_sync
    from yavin.db.repository import (
        AgentRepository,
        DataPointRepository,
        CollectionRunRepository,
    )

    async def _test():
        console.print("[bold]RBA Housing Lending Rates Collection[/]\n")

        init_db_sync()
        
        with SyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            agent = agent_repo.get_or_create(
                name="housing",
                agent_type="specialized",
                description="Australian Housing Market Agent",
            )
            
            dp_repo = DataPointRepository(session)
            existing = dp_repo.get_latest(agent.id, "housing_lending_rate_variable_owner_occupier")
            
            if existing and not force:
                console.print(f"[cyan]Data already in database:[/]")
                console.print(f"  Latest period: [bold]{existing.period}[/]")
                console.print(f"  Variable rate (owner-occupier): [bold]{existing.value:.2f}%[/]")
                console.print(f"  Collected at: {existing.created_at.strftime('%Y-%m-%d %H:%M')}")
                console.print(f"\n[dim]Use --force to fetch from RBA anyway[/]")
                return
            
            session.commit()

        console.print("[cyan]Fetching Housing Lending Rates from RBA...[/]")
        collector = RBAHousingLendingRatesCollector()
        result = await collector.collect()

        if result.success:
            console.print(f"[green]✓ Successfully fetched data[/]")
            console.print(f"  Records: {len(result.records)}\n")

            if result.records:
                metrics = {}
                for record in result.records:
                    metric = record.get("metric_name", "unknown")
                    if metric not in metrics:
                        metrics[metric] = []
                    metrics[metric].append(record)

                console.print("[bold]Latest Variable Rates:[/]")
                for metric_name in ["housing_lending_rate_variable_owner_occupier", 
                                    "housing_lending_rate_variable_investor"]:
                    if metric_name in metrics:
                        sorted_records = sorted(metrics[metric_name], key=lambda x: x.get("period", ""))
                        if sorted_records:
                            latest = sorted_records[-1]
                            label = "Owner Occupier" if "owner" in metric_name else "Investor"
                            console.print(f"  {label}: [bold]{latest['value']:.2f}%[/] ({latest['period']})")

                table = Table(title="Variable Housing Rates (Last 12 Months)")
                table.add_column("Period", style="cyan")
                table.add_column("Owner Occupier", style="green")
                table.add_column("Investor", style="yellow")

                oo_records = {r["period"]: r["value"] for r in metrics.get("housing_lending_rate_variable_owner_occupier", [])}
                inv_records = {r["period"]: r["value"] for r in metrics.get("housing_lending_rate_variable_investor", [])}
                
                periods = sorted(set(oo_records.keys()) | set(inv_records.keys()))[-12:]
                for period in periods:
                    oo = oo_records.get(period)
                    inv = inv_records.get(period)
                    table.add_row(
                        period,
                        f"{oo:.2f}%" if oo else "-",
                        f"{inv:.2f}%" if inv else "-",
                    )

                console.print()
                console.print(table)
        else:
            console.print(f"[red]✗ Collection failed: {result.error_message}[/]")
            return

        if save:
            console.print("\n[bold]Saving to database...[/]")
            try:
                with SyncSessionLocal() as session:
                    agent_repo = AgentRepository(session)
                    agent = agent_repo.get_or_create(
                        name="housing",
                        agent_type="specialized",
                        description="Australian Housing Market Agent",
                    )

                    run_repo = CollectionRunRepository(session)
                    run = run_repo.start_run(agent.id)

                    dp_repo = DataPointRepository(session)
                    saved, skipped = dp_repo.save_data_points(agent.id, result.records)

                    run_repo.complete_run(run, status="success", records_collected=len(saved))
                    session.commit()

                    console.print(f"[green]✓ Saved {len(saved)} new records to database[/]")
                    if skipped > 0:
                        console.print(f"  [dim]Skipped {skipped} existing records[/]")
                    console.print(f"  Agent ID: {agent.id}")
                    console.print(f"  Collection Run ID: {run.id}")

            except Exception as e:
                console.print(f"[red]✗ Failed to save: {e}[/]")
                raise

    asyncio.run(_test())


@app.command()
def test_unemployment(
    save: bool = typer.Option(False, "--save", "-s", help="Save data to database"),
    force: bool = typer.Option(False, "--force", "-f", help="Force fetch even if data exists in DB"),
):
    """Test the RBA Unemployment Rate collector and optionally save to DB."""
    from yavin.collectors.sources.rba import RBAUnemploymentCollector
    from yavin.db.session import SyncSessionLocal, init_db_sync
    from yavin.db.repository import (
        AgentRepository,
        DataPointRepository,
        CollectionRunRepository,
    )

    async def _test():
        console.print("[bold]RBA Unemployment Rate Collection[/]\n")

        init_db_sync()
        
        with SyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            agent = agent_repo.get_or_create(
                name="housing",
                agent_type="specialized",
                description="Australian Housing Market Agent",
            )
            
            dp_repo = DataPointRepository(session)
            existing = dp_repo.get_latest(agent.id, "unemployment_rate")
            
            if existing and not force:
                console.print(f"[cyan]Data already in database:[/]")
                console.print(f"  Latest period: [bold]{existing.period}[/]")
                console.print(f"  Unemployment rate: [bold]{existing.value:.2f}%[/]")
                console.print(f"  Collected at: {existing.created_at.strftime('%Y-%m-%d %H:%M')}")
                console.print(f"\n[dim]Use --force to fetch from RBA anyway[/]")
                return
            
            session.commit()

        console.print("[cyan]Fetching Unemployment data from RBA...[/]")
        collector = RBAUnemploymentCollector()
        result = await collector.collect()

        if result.success:
            console.print(f"[green]✓ Successfully fetched data[/]")
            console.print(f"  Records: {len(result.records)}\n")

            if result.records:
                metrics = {}
                for record in result.records:
                    metric = record.get("metric_name", "unknown")
                    if metric not in metrics:
                        metrics[metric] = []
                    metrics[metric].append(record)

                console.print("[bold]Latest Values:[/]")
                for metric_name in ["unemployment_rate", "labour_force_participation_rate", 
                                    "employment_to_population_ratio"]:
                    if metric_name in metrics:
                        sorted_records = sorted(metrics[metric_name], key=lambda x: x.get("period", ""))
                        if sorted_records:
                            latest = sorted_records[-1]
                            labels = {
                                "unemployment_rate": "Unemployment Rate",
                                "labour_force_participation_rate": "Participation Rate",
                                "employment_to_population_ratio": "Employment/Population Ratio",
                            }
                            console.print(f"  {labels[metric_name]}: [bold]{latest['value']:.2f}%[/] ({latest['period']})")

                table = Table(title="Unemployment Rate (Last 12 Months)")
                table.add_column("Period", style="cyan")
                table.add_column("Unemployment %", style="red")
                table.add_column("Participation %", style="green")

                ur_records = {r["period"]: r["value"] for r in metrics.get("unemployment_rate", [])}
                pr_records = {r["period"]: r["value"] for r in metrics.get("labour_force_participation_rate", [])}
                
                periods = sorted(set(ur_records.keys()) | set(pr_records.keys()))[-12:]
                for period in periods:
                    ur = ur_records.get(period)
                    pr = pr_records.get(period)
                    table.add_row(
                        period,
                        f"{ur:.2f}" if ur else "-",
                        f"{pr:.2f}" if pr else "-",
                    )

                console.print()
                console.print(table)
        else:
            console.print(f"[red]✗ Collection failed: {result.error_message}[/]")
            return

        if save:
            console.print("\n[bold]Saving to database...[/]")
            try:
                with SyncSessionLocal() as session:
                    agent_repo = AgentRepository(session)
                    agent = agent_repo.get_or_create(
                        name="housing",
                        agent_type="specialized",
                        description="Australian Housing Market Agent",
                    )

                    run_repo = CollectionRunRepository(session)
                    run = run_repo.start_run(agent.id)

                    dp_repo = DataPointRepository(session)
                    saved, skipped = dp_repo.save_data_points(agent.id, result.records)

                    run_repo.complete_run(run, status="success", records_collected=len(saved))
                    session.commit()

                    console.print(f"[green]✓ Saved {len(saved)} new records to database[/]")
                    if skipped > 0:
                        console.print(f"  [dim]Skipped {skipped} existing records[/]")
                    console.print(f"  Agent ID: {agent.id}")
                    console.print(f"  Collection Run ID: {run.id}")

            except Exception as e:
                console.print(f"[red]✗ Failed to save: {e}[/]")
                raise

    asyncio.run(_test())


@app.command()
def threads(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of threads to show"),
    all_threads: bool = typer.Option(False, "--all", "-a", help="Include archived threads"),
):
    """List recent chat threads."""
    from yavin.db.session import SyncSessionLocal
    from yavin.db.repository import ChatRepository
    
    with SyncSessionLocal() as session:
        repo = ChatRepository(session)
        thread_list = repo.list_threads(active_only=not all_threads, limit=limit)
        
        if not thread_list:
            console.print("[dim]No chat threads found. Start a new chat with 'yavin chat'[/]")
            return
        
        table = Table(title="Chat Threads")
        table.add_column("Thread ID", style="cyan")
        table.add_column("Topic", style="white")
        table.add_column("Messages", style="green")
        table.add_column("Last Active", style="yellow")
        table.add_column("Status", style="dim")
        
        for thread in thread_list:
            status = "Active" if thread.is_active else "Archived"
            topic = thread.topic or "[dim]No topic[/]"
            last_active = thread.updated_at.strftime("%Y-%m-%d %H:%M") if thread.updated_at else "-"
            
            table.add_row(
                thread.thread_id,
                topic[:40] + "..." if len(topic) > 40 else topic,
                str(thread.message_count),
                last_active,
                status,
            )
        
        console.print(table)
        console.print(f"\n[dim]Resume a thread with: yavin chat --resume <thread_id>[/]")


@app.command()
def chat(
    message: Optional[str] = typer.Argument(None, help="Initial message (or start interactive mode)"),
    resume: Optional[str] = typer.Option(None, "--resume", "-r", help="Resume an existing thread by ID"),
    topic: Optional[str] = typer.Option(None, "--topic", "-t", help="Set a topic for new thread"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug information"),
):
    """
    Start an interactive chat with the Yavin orchestrator.
    
    The orchestrator will route your questions to the appropriate specialized agents
    and provide responses based on collected data.
    
    Examples:
        yavin chat                          # Start new interactive chat
        yavin chat "What is the cash rate?" # Ask single question
        yavin chat --topic "RBA Analysis"   # New chat with topic name
        yavin chat --resume thread_123      # Resume existing thread
    """
    from yavin.agents import Orchestrator, get_registry
    from yavin.db.session import SyncSessionLocal
    from yavin.db.repository import ChatRepository
    
    async def _chat():
        # Set up the orchestrator with registered agents
        registry = get_registry()
        orchestrator = Orchestrator(persist=True)
        
        # Register all agents with the orchestrator
        for name, agent in registry.get_all().items():
            orchestrator.register_agent(agent)
        
        # Handle thread resumption or creation
        thread_id = resume
        resuming = False
        
        if resume:
            # Check if thread exists
            with SyncSessionLocal() as session:
                repo = ChatRepository(session)
                existing_thread = repo.get_thread_by_id(resume)
                if existing_thread:
                    resuming = True
                    console.print()
                    console.print(Panel(
                        f"[bold green]Resuming thread:[/] {resume}\n"
                        f"[dim]Topic: {existing_thread.topic or 'No topic'}[/]\n"
                        f"[dim]Messages: {existing_thread.message_count}[/]",
                        border_style="green",
                    ))
                    
                    # Show recent messages for context
                    if existing_thread.message_count > 0:
                        messages = repo.get_recent_messages(resume, count=4)
                        console.print("\n[dim]Recent messages:[/]")
                        for msg in messages:
                            role_style = "green" if msg.role == "user" else "cyan"
                            prefix = "You" if msg.role == "user" else msg.agent_name or "Assistant"
                            content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                            console.print(f"  [{role_style}]{prefix}:[/] {content_preview}")
                        console.print()
                else:
                    console.print(f"[yellow]Thread '{resume}' not found. Starting new thread.[/]")
                    thread_id = None
        
        if not resuming:
            console.print()
            console.print(Panel(
                "[bold blue]Yavin Chat[/]\n\n"
                "I'm your assistant for Australian economic data. I can answer questions about:\n"
                "• Housing market (building approvals, interest rates)\n"
                "• RBA monetary policy (meeting minutes, cash rate decisions)\n"
                "• Inflation and economic indicators\n\n"
                "[dim]Type 'exit' or 'quit' to end the conversation.[/]",
                border_style="blue",
            ))
            console.print()
        
        # If topic provided, set it when creating thread
        if topic and not resume:
            # Pre-create thread with topic
            with SyncSessionLocal() as session:
                repo = ChatRepository(session)
                new_thread_id = f"thread_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                repo.create_thread(new_thread_id, topic)
                session.commit()
                thread_id = new_thread_id
                console.print(f"[dim]Thread: {thread_id} | Topic: {topic}[/]\n")
        
        # Track if we've shown the auto-generated topic
        shown_topic = topic is not None
        
        # If message provided, answer it directly
        if message:
            console.print(f"[bold]You:[/] {message}\n")
            response = await orchestrator.chat(message, thread_id=thread_id)
            thread_id = response.metadata.get("thread_id") if response.metadata else None
            
            # Show auto-generated topic on first message
            if not shown_topic and response.metadata:
                auto_topic = response.metadata.get("topic")
                if auto_topic:
                    console.print(f"[dim]Topic: {auto_topic}[/]")
                    shown_topic = True
            
            if debug:
                console.print(f"[dim]Agent: {response.agent_name} | "
                            f"Confidence: {response.confidence:.0%}[/]")
            
            console.print(Panel(
                response.content,
                title=f"[bold cyan]{response.agent_name}[/]",
                border_style="cyan",
            ))
            console.print()
        
        # Interactive loop
        while True:
            try:
                user_input = console.input("[bold green]You:[/] ")
            except (KeyboardInterrupt, EOFError):
                if thread_id:
                    console.print(f"\n[dim]Thread saved: {thread_id}[/]")
                    console.print(f"[dim]Resume with: yavin chat --resume {thread_id}[/]")
                console.print("[dim]Goodbye![/]")
                break
            
            if not user_input.strip():
                continue
            
            if user_input.lower() in ("exit", "quit", "bye", "q"):
                if thread_id:
                    console.print(f"[dim]Thread saved: {thread_id}[/]")
                    console.print(f"[dim]Resume with: yavin chat --resume {thread_id}[/]")
                console.print("[dim]Goodbye![/]")
                break
            
            console.print()
            
            # Show thinking indicator
            with console.status("[bold blue]Thinking...", spinner="dots"):
                response = await orchestrator.chat(user_input, thread_id=thread_id)
            
            thread_id = response.metadata.get("thread_id") if response.metadata else None
            
            # Show auto-generated topic on first message
            if not shown_topic and response.metadata:
                auto_topic = response.metadata.get("topic")
                if auto_topic:
                    console.print(f"[dim]Topic: {auto_topic}[/]")
                    shown_topic = True
            
            if debug:
                tool_calls = response.metadata.get("tool_calls", 0) if response.metadata else 0
                console.print(f"[dim]Agent: {response.agent_name} | "
                            f"Confidence: {response.confidence:.0%} | "
                            f"Tools: {tool_calls}[/]")
            
            console.print(Panel(
                response.content,
                title=f"[bold cyan]{response.agent_name}[/]",
                border_style="cyan",
            ))
            console.print()
    
    asyncio.run(_chat())


if __name__ == "__main__":
    app()
