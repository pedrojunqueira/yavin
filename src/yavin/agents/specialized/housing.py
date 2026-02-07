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


@tool
def get_metrics_summary() -> dict:
    """
    Get a comprehensive summary of all available metrics in the database.
    
    Returns details about each metric including:
    - Metric name and description
    - Data range (earliest to latest period)
    - Number of data points
    - Latest value
    - Source
    - Unit of measurement
    
    Use this tool to understand what data is available for analysis.
    """
    try:
        from sqlalchemy import select, func, distinct
        from yavin.db.models import DataPoint
        
        with SyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            agent = agent_repo.get_by_name("housing")
            
            if not agent:
                return {"error": "Housing agent not found", "metrics": []}
            
            # Get summary for each metric
            stmt = (
                select(
                    DataPoint.metric_name,
                    func.count(DataPoint.id).label("count"),
                    func.min(DataPoint.period).label("earliest"),
                    func.max(DataPoint.period).label("latest"),
                    DataPoint.source,
                    DataPoint.unit,
                )
                .where(DataPoint.agent_id == agent.id)
                .group_by(DataPoint.metric_name, DataPoint.source, DataPoint.unit)
                .order_by(DataPoint.metric_name)
            )
            result = session.execute(stmt)
            
            metrics = []
            for row in result:
                # Get the latest value for this metric
                latest_stmt = (
                    select(DataPoint.value, DataPoint.period)
                    .where(DataPoint.agent_id == agent.id)
                    .where(DataPoint.metric_name == row.metric_name)
                    .order_by(DataPoint.period.desc())
                    .limit(1)
                )
                latest = session.execute(latest_stmt).first()
                
                metrics.append({
                    "metric_name": row.metric_name,
                    "count": row.count,
                    "earliest_period": row.earliest,
                    "latest_period": row.latest,
                    "latest_value": latest.value if latest else None,
                    "source": row.source,
                    "unit": row.unit,
                })
            
            return {
                "metrics": metrics,
                "total_metrics": len(metrics),
            }
    except Exception as e:
        return {"error": str(e), "metrics": []}


@tool
def analyze_metric_growth(metric_name: str, periods: int = 0) -> dict:
    """
    Analyze growth rates and trends for a specific metric.
    
    Calculates:
    - Year-over-year growth rates
    - Period-over-period changes
    - Total growth and CAGR over the available data range
    - Min/max values and when they occurred
    
    Args:
        metric_name: The name of the metric to analyze
        periods: Number of recent periods to analyze (0 = all available data)
    
    Examples:
        analyze_metric_growth("avg_loan_size_first_home_buyer")
        analyze_metric_growth("interest_rate_cash", 24)
    """
    try:
        from sqlalchemy import select
        from yavin.db.models import DataPoint
        
        with SyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            agent = agent_repo.get_by_name("housing")
            
            if not agent:
                return {"error": "Housing agent not found", "metric": metric_name}
            
            # Get all data points for this metric
            stmt = (
                select(DataPoint)
                .where(DataPoint.agent_id == agent.id)
                .where(DataPoint.metric_name == metric_name)
                .order_by(DataPoint.period.asc())
            )
            result = session.execute(stmt)
            data_points = list(result.scalars().all())
            
            if not data_points:
                return {"error": f"No data found for metric '{metric_name}'", "metric": metric_name}
            
            # Apply period limit if specified
            if periods > 0:
                data_points = data_points[-periods:]
            
            # Extract values
            values = [(dp.period, dp.value) for dp in data_points if dp.value is not None]
            
            if len(values) < 2:
                return {"error": "Insufficient data for analysis", "metric": metric_name}
            
            # Calculate basic stats
            first_period, first_value = values[0]
            last_period, last_value = values[-1]
            
            # Calculate total growth
            total_growth_pct = ((last_value - first_value) / first_value) * 100 if first_value else 0
            
            # Calculate CAGR (approximate based on period format)
            # Assuming periods are like "2020-01" or "2020-03"
            try:
                first_year = int(first_period[:4])
                last_year = int(last_period[:4])
                if len(first_period) > 5:
                    first_month = int(first_period[5:7])
                    last_month = int(last_period[5:7])
                    years = (last_year - first_year) + (last_month - first_month) / 12
                else:
                    years = last_year - first_year
                
                if years > 0 and first_value > 0:
                    cagr = ((last_value / first_value) ** (1 / years) - 1) * 100
                else:
                    cagr = None
            except:
                cagr = None
                years = len(values) - 1
            
            # Calculate period-over-period changes
            changes = []
            for i in range(1, min(len(values), 13)):  # Last 12 changes max
                prev_period, prev_value = values[-(i+1)]
                curr_period, curr_value = values[-i]
                if prev_value:
                    change_pct = ((curr_value - prev_value) / prev_value) * 100
                    changes.append({
                        "from_period": prev_period,
                        "to_period": curr_period,
                        "change": curr_value - prev_value,
                        "change_pct": round(change_pct, 2),
                    })
            
            # Find min and max
            min_val = min(values, key=lambda x: x[1])
            max_val = max(values, key=lambda x: x[1])
            
            return {
                "metric": metric_name,
                "data_points": len(values),
                "period_range": {
                    "from": first_period,
                    "to": last_period,
                    "years": round(years, 1) if years else None,
                },
                "values": {
                    "first": {"period": first_period, "value": first_value},
                    "last": {"period": last_period, "value": last_value},
                    "min": {"period": min_val[0], "value": min_val[1]},
                    "max": {"period": max_val[0], "value": max_val[1]},
                },
                "growth": {
                    "total_change": round(last_value - first_value, 2),
                    "total_pct": round(total_growth_pct, 2),
                    "cagr": round(cagr, 2) if cagr else None,
                },
                "recent_changes": changes[:6],  # Last 6 period changes
                "unit": data_points[0].unit,
                "source": data_points[0].source,
            }
    except Exception as e:
        return {"error": str(e), "metric": metric_name}


@tool
def calculate_affordability(
    loan_type: str = "first_home_buyer",
    dual_income: bool = False,
) -> dict:
    """
    Calculate housing affordability metrics based on current data.
    
    Combines average loan sizes, weekly earnings, and mortgage rates to calculate:
    - Monthly repayment amount
    - Repayment as percentage of income
    - Debt-to-income ratio
    - Mortgage stress level
    
    Args:
        loan_type: Type of loan - "first_home_buyer", "owner_occupier", "investor", or "total"
        dual_income: If True, calculate for dual full-time income household
    
    Returns affordability analysis with stress indicators.
    """
    try:
        from sqlalchemy import select
        from yavin.db.models import DataPoint
        
        with SyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            agent = agent_repo.get_by_name("housing")
            
            if not agent:
                return {"error": "Housing agent not found"}
            
            dp_repo = DataPointRepository(session)
            
            # Map loan type to metric name
            loan_metric_map = {
                "first_home_buyer": "avg_loan_size_first_home_buyer",
                "owner_occupier": "avg_loan_size_owner_occupier",
                "investor": "avg_loan_size_investor",
                "total": "avg_loan_size_total",
            }
            
            loan_metric = loan_metric_map.get(loan_type)
            if not loan_metric:
                return {"error": f"Invalid loan type: {loan_type}"}
            
            # Get latest loan size
            loan_dp = dp_repo.get_latest(agent.id, loan_metric)
            if not loan_dp:
                return {"error": f"No loan data found for {loan_type}"}
            
            # Get latest weekly earnings (full-time adult ordinary)
            earnings_dp = dp_repo.get_latest(agent.id, "fulltime_adultavg_weekly_ordinary_earnings")
            if not earnings_dp:
                return {"error": "No earnings data found"}
            
            # Get latest mortgage rate
            rate_dp = dp_repo.get_latest(agent.id, "housing_lending_rate_variable_owner_occupier")
            if not rate_dp:
                return {"error": "No mortgage rate data found"}
            
            # Calculate values
            loan_amount = loan_dp.value * 1000  # Convert from thousands
            weekly_earnings = earnings_dp.value
            annual_income = weekly_earnings * 52
            if dual_income:
                annual_income *= 2
            
            interest_rate = rate_dp.value
            
            # Calculate monthly repayment (30-year P&I)
            monthly_rate = interest_rate / 100 / 12
            n_payments = 30 * 12
            if monthly_rate > 0:
                monthly_repayment = loan_amount * (monthly_rate * (1 + monthly_rate)**n_payments) / ((1 + monthly_rate)**n_payments - 1)
            else:
                monthly_repayment = loan_amount / n_payments
            
            annual_repayment = monthly_repayment * 12
            repayment_to_income = (annual_repayment / annual_income) * 100
            debt_to_income = loan_amount / annual_income
            
            # Determine stress level
            if repayment_to_income < 25:
                stress_level = "LOW"
                stress_description = "Comfortable - can build savings"
            elif repayment_to_income < 30:
                stress_level = "MODERATE"
                stress_description = "Manageable - limited buffer"
            elif repayment_to_income < 35:
                stress_level = "HIGH"
                stress_description = "Stretched - vulnerable to rate rises"
            else:
                stress_level = "SEVERE"
                stress_description = "Mortgage stress - risk of default"
            
            return {
                "loan_type": loan_type,
                "dual_income": dual_income,
                "inputs": {
                    "loan_amount": loan_amount,
                    "loan_period": loan_dp.period,
                    "weekly_earnings": weekly_earnings,
                    "earnings_period": earnings_dp.period,
                    "annual_income": annual_income,
                    "interest_rate": interest_rate,
                    "rate_period": rate_dp.period,
                },
                "repayment": {
                    "monthly": round(monthly_repayment, 2),
                    "annual": round(annual_repayment, 2),
                    "percent_of_income": round(repayment_to_income, 1),
                },
                "ratios": {
                    "debt_to_income": round(debt_to_income, 2),
                },
                "assessment": {
                    "stress_level": stress_level,
                    "description": stress_description,
                },
            }
    except Exception as e:
        return {"error": str(e)}


@tool
def compare_metrics(metric_names: str, limit: int = 12) -> dict:
    """
    Compare multiple metrics side by side over time.
    
    Useful for analyzing relationships between different economic indicators.
    
    Args:
        metric_names: Comma-separated list of metric names to compare
                     (e.g., "interest_rate_cash,inflation_cpi_annual,unemployment_rate")
        limit: Number of recent periods per metric (default 12)
    
    Returns aligned time series data for comparison.
    """
    try:
        from sqlalchemy import select
        from yavin.db.models import DataPoint
        
        metrics = [m.strip() for m in metric_names.split(",")]
        
        with SyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            agent = agent_repo.get_by_name("housing")
            
            if not agent:
                return {"error": "Housing agent not found"}
            
            dp_repo = DataPointRepository(session)
            
            result = {}
            for metric in metrics:
                data_points = dp_repo.get_timeseries(agent.id, metric, limit=limit)
                if data_points:
                    result[metric] = {
                        "data": [
                            {"period": dp.period, "value": dp.value}
                            for dp in reversed(data_points)
                        ],
                        "unit": data_points[0].unit,
                        "latest": {
                            "period": data_points[0].period,
                            "value": data_points[0].value,
                        }
                    }
                else:
                    result[metric] = {"error": f"No data found for {metric}"}
            
            return {
                "metrics": result,
                "count": len(metrics),
            }
    except Exception as e:
        return {"error": str(e)}


@tool
def query_metric_by_period(metric_name: str, start_period: str, end_period: str = "") -> dict:
    """
    Query metric data for a specific period range.
    
    Args:
        metric_name: The metric to query
        start_period: Start period in format "YYYY-MM" (e.g., "2020-01")
        end_period: End period in format "YYYY-MM" (optional, defaults to latest)
    
    Returns all data points within the specified range.
    """
    try:
        from sqlalchemy import select
        from yavin.db.models import DataPoint
        
        with SyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            agent = agent_repo.get_by_name("housing")
            
            if not agent:
                return {"error": "Housing agent not found", "metric": metric_name}
            
            # Build query
            stmt = (
                select(DataPoint)
                .where(DataPoint.agent_id == agent.id)
                .where(DataPoint.metric_name == metric_name)
                .where(DataPoint.period >= start_period)
            )
            
            if end_period:
                stmt = stmt.where(DataPoint.period <= end_period)
            
            stmt = stmt.order_by(DataPoint.period.asc())
            
            result = session.execute(stmt)
            data_points = list(result.scalars().all())
            
            if not data_points:
                return {
                    "error": f"No data found for {metric_name} in period {start_period} to {end_period or 'now'}",
                    "metric": metric_name,
                }
            
            return {
                "metric": metric_name,
                "period_range": {
                    "from": start_period,
                    "to": end_period or data_points[-1].period,
                },
                "data": [
                    {
                        "period": dp.period,
                        "value": dp.value,
                    }
                    for dp in data_points
                ],
                "count": len(data_points),
                "unit": data_points[0].unit,
                "source": data_points[0].source,
            }
    except Exception as e:
        return {"error": str(e), "metric": metric_name}


# SQL keywords that modify data - BLOCKED
FORBIDDEN_SQL_KEYWORDS = [
    'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 'TRUNCATE',
    'REPLACE', 'GRANT', 'REVOKE', 'EXECUTE', 'EXEC', 'CALL', 'MERGE',
    'UPSERT', 'RENAME', 'MODIFY', 'VACUUM', 'REINDEX', 'CLUSTER',
    'COPY', 'LOAD', 'IMPORT', 'EXPORT', 'BACKUP', 'RESTORE',
    'COMMIT', 'ROLLBACK', 'SAVEPOINT', 'SET', 'LOCK', 'UNLOCK',
    'KILL', 'SHUTDOWN', 'PRAGMA',
]

# Tables the agent is allowed to query
ALLOWED_TABLES = ['data_points', 'documents', 'document_chunks']


def _validate_sql_query(sql: str) -> tuple[bool, str]:
    """
    Validate that a SQL query is safe to execute (read-only).
    
    Returns:
        (is_valid, error_message) - is_valid is True if query is safe
    """
    # Normalize the query for checking
    sql_upper = sql.upper().strip()
    
    # Must start with SELECT or WITH (for CTEs)
    if not sql_upper.startswith('SELECT') and not sql_upper.startswith('WITH'):
        return False, "Only SELECT queries are allowed. Query must start with SELECT or WITH."
    
    # Check for forbidden keywords
    # We check for whole words by looking for word boundaries
    import re
    for keyword in FORBIDDEN_SQL_KEYWORDS:
        # Match the keyword as a whole word (not part of another word)
        pattern = rf'\b{keyword}\b'
        if re.search(pattern, sql_upper):
            return False, f"Forbidden SQL keyword detected: {keyword}. Only SELECT queries are allowed."
    
    # Check for semicolons (to prevent multiple statements)
    # Allow one at the end, but not in the middle
    sql_stripped = sql.strip().rstrip(';')
    if ';' in sql_stripped:
        return False, "Multiple SQL statements are not allowed. Please use a single SELECT query."
    
    # Check for comments that might hide malicious code
    if '--' in sql or '/*' in sql:
        return False, "SQL comments are not allowed."
    
    return True, ""


@tool
def query_database(sql_query: str) -> dict:
    """
    Execute a read-only SQL query against the database for flexible data analysis.
    
    This tool allows you to run custom SQL queries for ad-hoc analysis that isn't
    covered by other tools. ONLY SELECT queries are allowed - any attempt to modify
    data will be blocked.
    
    DATABASE SCHEMA:
    
    Table: data_points
    - id (int): Primary key
    - metric_name (str): Name of the metric (e.g., 'housing_approvals_total')
    - value (float): Numeric value
    - value_text (str): Text value for non-numeric data
    - period (str): Time period in format 'YYYY-MM' (e.g., '2025-09')
    - timestamp (datetime): When the data was collected
    - source (str): Data source (e.g., 'ABS', 'RBA')
    - geography (str): Geographic region (e.g., 'Australia', 'NSW')
    - unit (str): Unit of measurement (e.g., '$', '%', 'number')
    - extra_data (json): Additional metadata
    - created_at (datetime): When the record was created
    
    Table: documents
    - id (int): Primary key
    - document_type (str): Type of document (e.g., 'rba_minutes', 'rba_statement')
    - external_id (str): External identifier (e.g., meeting date '2025-02-17')
    - title (str): Document title
    - source_url (str): URL of the source document
    - published_at (datetime): Publication date
    - content (text): Full document text
    - summary (text): Summary of the document
    - extra_data (json): Additional metadata (e.g., cash_rate, decision)
    - collected_at (datetime): When the document was collected
    
    EXAMPLE QUERIES:
    
    1. Get all distinct metrics:
       SELECT DISTINCT metric_name FROM data_points ORDER BY metric_name
    
    2. Get average loan size by year:
       SELECT 
           SUBSTRING(period, 1, 4) as year,
           metric_name,
           AVG(value) as avg_value
       FROM data_points 
       WHERE metric_name LIKE '%avg_loan_size%'
       GROUP BY SUBSTRING(period, 1, 4), metric_name
       ORDER BY year, metric_name
    
    3. Compare cash rate vs inflation over time:
       SELECT period, metric_name, value 
       FROM data_points 
       WHERE metric_name IN ('interest_rate_cash', 'inflation_cpi_annual')
       ORDER BY period DESC, metric_name
       LIMIT 24
    
    4. Calculate year-over-year growth:
       SELECT 
           a.period,
           a.metric_name,
           a.value,
           LAG(a.value, 12) OVER (PARTITION BY a.metric_name ORDER BY a.period) as prev_year,
           ROUND(((a.value / NULLIF(LAG(a.value, 12) OVER (PARTITION BY a.metric_name ORDER BY a.period), 0)) - 1) * 100, 2) as yoy_growth_pct
       FROM data_points a
       WHERE metric_name = 'housing_approvals_total'
       ORDER BY period DESC
       LIMIT 24
    
    5. Get RBA meeting decisions:
       SELECT published_at, title, extra_data->>'decision' as decision, extra_data->>'cash_rate' as cash_rate
       FROM documents 
       WHERE document_type = 'rba_minutes'
       ORDER BY published_at DESC
       LIMIT 10
    
    Args:
        sql_query: A SELECT SQL query to execute. Must be read-only.
    
    Returns:
        Query results as a list of dictionaries, or an error message.
    """
    from sqlalchemy import text
    
    # Validate the query is safe (read-only)
    is_valid, error_msg = _validate_sql_query(sql_query)
    if not is_valid:
        return {
            "error": error_msg,
            "query": sql_query,
            "hint": "This tool only allows SELECT queries. To modify data, use the collection commands.",
        }
    
    try:
        with SyncSessionLocal() as session:
            # Set a statement timeout for safety (30 seconds)
            session.execute(text("SET statement_timeout = '30s'"))
            
            # Execute the query
            result = session.execute(text(sql_query))
            
            # Fetch results
            rows = result.fetchall()
            columns = result.keys()
            
            # Limit results to prevent memory issues
            MAX_ROWS = 500
            if len(rows) > MAX_ROWS:
                rows = rows[:MAX_ROWS]
                truncated = True
            else:
                truncated = False
            
            # Convert to list of dicts
            data = []
            for row in rows:
                row_dict = {}
                for col, val in zip(columns, row):
                    # Handle datetime serialization
                    if hasattr(val, 'isoformat'):
                        row_dict[col] = val.isoformat()
                    elif isinstance(val, (dict, list)):
                        row_dict[col] = val
                    else:
                        row_dict[col] = val
                data.append(row_dict)
            
            return {
                "success": True,
                "query": sql_query,
                "row_count": len(data),
                "truncated": truncated,
                "max_rows": MAX_ROWS if truncated else None,
                "columns": list(columns),
                "data": data,
            }
            
    except Exception as e:
        error_str = str(e)
        # Provide helpful hints for common errors
        hints = []
        if 'column' in error_str.lower() and 'does not exist' in error_str.lower():
            hints.append("Check the column name spelling. Use the schema description above for valid column names.")
        if 'relation' in error_str.lower() and 'does not exist' in error_str.lower():
            hints.append("Only 'data_points' and 'documents' tables are available.")
        if 'syntax error' in error_str.lower():
            hints.append("Check SQL syntax. Common issues: missing quotes, incorrect JOIN syntax.")
        
        return {
            "error": f"Query execution failed: {error_str}",
            "query": sql_query,
            "hints": hints if hints else ["Check your SQL syntax and column/table names."],
        }


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
- Australian Bureau of Statistics (ABS): Building approvals, housing starts, lending indicators, earnings
- Reserve Bank of Australia (RBA): Interest rates, inflation, lending rates, cash rate
- RBA Meeting Minutes: Full text of recent monetary policy board meetings
- Economic indicators: Unemployment, CPI, credit growth

AVAILABLE TOOLS:
Data Retrieval:
- get_latest_metric: Get the most recent value for a metric
- get_metric_timeseries: Get historical values for a metric
- list_available_metrics: List all metrics in the database
- get_metrics_summary: Get comprehensive summary of all metrics with ranges and latest values
- query_metric_by_period: Query data for a specific date range

Analysis Tools:
- analyze_metric_growth: Calculate growth rates, CAGR, and trends for any metric
- calculate_affordability: Calculate housing affordability (repayment %, stress level, DTI)
- compare_metrics: Compare multiple metrics side by side

RBA Documents:
- get_rba_minutes: Get recent RBA meeting minutes
- search_rba_minutes: Search minutes for specific topics

Flexible SQL (read-only):
- query_database: Execute custom SQL queries for ad-hoc analysis (SELECT only)
  Use this for complex queries not covered by other tools (aggregations, joins, window functions)

CRITICAL INSTRUCTIONS:
1. ALWAYS call tools first to get data - never answer from memory
2. For analysis questions, use analyze_metric_growth or calculate_affordability
3. Use get_metrics_summary to discover available data
4. Cite specific numbers, dates, and sources from tool results
5. If a tool returns an error, tell the user what data is missing

Current date: {current_date}"""

    # System prompt when pre-fetched data is provided
    SYSTEM_PROMPT_WITH_DATA = """You are the Housing Agent, a specialized analyst monitoring the Australian housing market.

You have been provided with CURRENT DATA from your local database below. Use this data to answer the question.
DO NOT rely on your training data - use ONLY the provided data and tool results.

=== PRE-FETCHED DATA (from database) ===
{prefetched_data}
=== END PRE-FETCHED DATA ===

You still have access to tools for additional queries if needed:

Data Retrieval:
- get_latest_metric: Get the most recent value for a metric
- get_metric_timeseries: Get historical values for a metric
- list_available_metrics: List all metrics in the database
- get_metrics_summary: Get comprehensive summary of all metrics with ranges and latest values
- query_metric_by_period: Query data for a specific date range

Analysis Tools:
- analyze_metric_growth: Calculate growth rates, CAGR, and trends for any metric
- calculate_affordability: Calculate housing affordability (repayment %, stress level, DTI)
- compare_metrics: Compare multiple metrics side by side

RBA Documents:
- get_rba_minutes: Get recent RBA meeting minutes
- search_rba_minutes: Search minutes for specific topics

Flexible SQL (read-only):
- query_database: Execute custom SQL queries for ad-hoc analysis (SELECT only)
  Use this for complex queries not covered by other tools (aggregations, joins, window functions)

INSTRUCTIONS:
1. Answer based on the pre-fetched data above
2. Call additional tools (especially analysis tools) if deeper analysis is needed
3. Use calculate_affordability for affordability questions
4. Use analyze_metric_growth for growth/trend questions
5. Cite specific numbers, dates, and sources
6. If data is missing, acknowledge what you don't have

Be concise but informative. Focus on facts from the data.

Current date: {current_date}"""

    def __init__(self) -> None:
        """Initialize the housing agent with LLM and tools."""
        self.model = get_chat_model()
        self.tools = [
            # Basic data retrieval
            get_latest_metric,
            get_metric_timeseries,
            list_available_metrics,
            # Enhanced analysis tools
            get_metrics_summary,
            analyze_metric_growth,
            calculate_affordability,
            compare_metrics,
            query_metric_by_period,
            # RBA documents
            get_rba_minutes,
            search_rba_minutes,
            # Flexible SQL queries (read-only)
            query_database,
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

    def _prefetch_relevant_data(self) -> tuple[str, list[dict]]:
        """
        Pre-fetch key data from the database to ground the response.
        
        Returns:
            Tuple of (formatted_data_string, raw_data_points)
        """
        from yavin.db.session import SyncSessionLocal
        from yavin.db.models import Document
        from sqlalchemy import select
        
        data_sections = []
        data_points = []
        
        # Key metrics to always fetch
        key_metrics = [
            ("interest_rate_cash", "RBA Cash Rate"),
            ("inflation_cpi_annual", "Annual CPI Inflation"),
            ("inflation_trimmed_mean_annual", "Trimmed Mean Inflation"),
            ("unemployment_rate", "Unemployment Rate"),
        ]
        
        # Fetch latest metrics
        metrics_data = []
        for metric_name, label in key_metrics:
            result = get_latest_metric.invoke({"metric_name": metric_name})
            if "error" not in result:
                metrics_data.append(f"  • {label}: {result['value']}% ({result['period']})")
                data_points.append({"tool": "get_latest_metric", "args": {"metric_name": metric_name}, "result": result})
        
        if metrics_data:
            data_sections.append("KEY ECONOMIC INDICATORS:\n" + "\n".join(metrics_data))
        
        # Fetch latest RBA monetary policy statement (most recent meeting decision)
        try:
            with SyncSessionLocal() as session:
                latest_statement = session.execute(
                    select(Document)
                    .where(Document.document_type == "rba_statement")
                    .order_by(Document.published_at.desc())
                    .limit(1)
                ).scalar()
                
                if latest_statement:
                    statement_data = [
                        "LATEST RBA MONETARY POLICY DECISION:",
                        f"  • Meeting date: {latest_statement.published_at.strftime('%Y-%m-%d') if latest_statement.published_at else 'N/A'}",
                        f"  • Decision: {latest_statement.summary or 'N/A'}",
                    ]
                    if latest_statement.extra_data:
                        if latest_statement.extra_data.get("cash_rate"):
                            statement_data.append(f"  • Cash rate: {latest_statement.extra_data['cash_rate']}%")
                        if latest_statement.extra_data.get("decision_type"):
                            statement_data.append(f"  • Action: {latest_statement.extra_data['decision_type'].upper()}")
                        if latest_statement.extra_data.get("basis_points_change"):
                            bp = latest_statement.extra_data['basis_points_change']
                            statement_data.append(f"  • Change: {bp:+d} basis points")
                    
                    data_sections.append("\n".join(statement_data))
                    data_points.append({
                        "source": "rba_statement",
                        "meeting_date": latest_statement.published_at.strftime('%Y-%m-%d') if latest_statement.published_at else None,
                        "summary": latest_statement.summary,
                        "extra_data": latest_statement.extra_data,
                    })
        except Exception as e:
            # If statement fetch fails, continue without it
            pass
        
        # Fetch recent RBA minutes summaries (for detailed meeting discussions)
        minutes_result = get_rba_minutes.invoke({"limit": 2})
        if "error" not in minutes_result and minutes_result.get("meetings"):
            minutes_data = ["RECENT RBA MEETING MINUTES (detailed discussions):"]
            for meeting in minutes_result["meetings"]:
                minutes_data.append(f"  • {meeting['meeting_date']}: Cash rate {meeting.get('cash_rate', 'N/A')}%")
                if meeting.get("decision_summary"):
                    summary = meeting["decision_summary"][:200]
                    minutes_data.append(f"    Summary: {summary}...")
            data_sections.append("\n".join(minutes_data))
            data_points.append({"tool": "get_rba_minutes", "args": {"limit": 2}, "result": minutes_result})
        
        return "\n\n".join(data_sections), data_points

    async def query(self, question: str, context: dict[str, Any] | None = None) -> AgentResponse:
        """
        Answer a question about the housing market using LLM with tools.
        
        Args:
            question: The user's question
            context: Optional context dict. If context["force_fetch"] is True,
                    data will be pre-fetched and injected into the prompt.
        """
        from langchain_core.messages import AIMessage, ToolMessage
        
        context = context or {}
        force_fetch = context.get("force_fetch", False)
        
        # Keep track of sources and data used
        sources_used = []
        data_points = []
        
        # Determine which system prompt to use
        if force_fetch:
            # Pre-fetch relevant data and inject into prompt
            prefetched_data, prefetch_data_points = self._prefetch_relevant_data()
            data_points.extend(prefetch_data_points)
            sources_used.append("prefetch")
            
            system_prompt = self.SYSTEM_PROMPT_WITH_DATA.format(
                prefetched_data=prefetched_data if prefetched_data else "(No data available)",
                current_date=datetime.now().strftime("%Y-%m-%d"),
            )
        else:
            system_prompt = self.SYSTEM_PROMPT.format(
                current_date=datetime.now().strftime("%Y-%m-%d"),
            )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=question),
        ]
        
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
