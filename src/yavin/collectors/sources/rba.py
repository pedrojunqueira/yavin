"""
Reserve Bank of Australia (RBA) data collector.

Fetches interest rate data from the RBA website.
The RBA publishes data in Excel files at predictable URLs.

Data sources:
- Cash Rate Target: https://www.rba.gov.au/statistics/cash-rate/
- Interest Rates: https://www.rba.gov.au/statistics/tables/xls/f01hist.xls
"""

from datetime import datetime
from typing import Any

import httpx

from yavin.collectors.base import BaseCollector, CollectorResult


class RBAInterestRateCollector(BaseCollector):
    """
    Collector for RBA interest rate data.
    
    Fetches the current cash rate target from the RBA website.
    The cash rate is the interest rate on overnight loans between banks.
    """

    name = "RBA Interest Rates"
    source_url = "https://www.rba.gov.au/statistics/cash-rate/"
    
    # RBA cash rate history page (simpler to parse than Excel)
    CASH_RATE_URL = "https://www.rba.gov.au/statistics/cash-rate/"
    
    # Alternative: Excel file with historical rates
    # RATES_EXCEL_URL = "https://www.rba.gov.au/statistics/tables/xls/f01hist.xls"

    async def collect(self) -> CollectorResult:
        """Fetch current interest rate data from RBA."""
        collected_at = datetime.now()
        
        try:
            async with httpx.AsyncClient() as client:
                # Fetch the cash rate page
                response = await client.get(
                    self.CASH_RATE_URL,
                    headers={
                        "User-Agent": "Yavin Data Collector (educational project)",
                    },
                    timeout=30.0,
                    follow_redirects=True,
                )
                response.raise_for_status()
                
                html_content = response.text
                records = self.normalize(html_content)
                
                return CollectorResult(
                    collector_name=self.name,
                    source_url=self.CASH_RATE_URL,
                    success=True,
                    records=records,
                    collected_at=collected_at,
                    metadata={"content_length": len(html_content)},
                )
                
        except httpx.HTTPError as e:
            return CollectorResult(
                collector_name=self.name,
                source_url=self.CASH_RATE_URL,
                success=False,
                records=[],
                collected_at=collected_at,
                error_message=f"HTTP error: {str(e)}",
            )
        except Exception as e:
            return CollectorResult(
                collector_name=self.name,
                source_url=self.CASH_RATE_URL,
                success=False,
                records=[],
                collected_at=collected_at,
                error_message=f"Unexpected error: {str(e)}",
            )

    def normalize(self, html_content: str) -> list[dict[str, Any]]:
        """
        Parse the RBA cash rate page to extract current rate.
        
        The page contains a table with the current cash rate target.
        We use simple string parsing to avoid heavy dependencies like BeautifulSoup.
        """
        records = []
        
        try:
            # Look for the current cash rate in the page
            # The format is typically: "Current cash rate target: X.XX per cent"
            # or shown in a prominent heading/table
            
            # Simple pattern matching for the cash rate value
            import re
            
            # Pattern 1: Look for "X.XX per cent" near "cash rate"
            # The RBA page typically shows "4.35" or similar
            rate_pattern = r'(\d+\.\d+)\s*(?:per\s*cent|%)'
            
            # Find all percentage values
            matches = re.findall(rate_pattern, html_content, re.IGNORECASE)
            
            if matches:
                # The first match is usually the current cash rate
                current_rate = float(matches[0])
                
                records.append({
                    "metric_name": "interest_rate_cash",
                    "value": current_rate,
                    "period": datetime.now().strftime("%Y-%m-%d"),
                    "geography": "Australia",
                    "unit": "percent",
                    "source": "RBA Cash Rate Target",
                })
            
            # Also try to find effective date
            date_pattern = r'(\d{1,2}\s+\w+\s+\d{4})'
            date_matches = re.findall(date_pattern, html_content)
            
            if date_matches and records:
                # Add the effective date to metadata
                records[0]["effective_date"] = date_matches[0]
                
        except Exception as e:
            # Log error but return empty records
            print(f"Error parsing RBA data: {e}")
            
        return records


class RBAInterestRateHistoryCollector(BaseCollector):
    """
    Collector for historical RBA interest rate data.
    
    Fetches from the F1.1 statistical table (Interest Rates and Yields - Monthly).
    This is an Excel file that requires pandas to parse.
    """
    
    name = "RBA Interest Rate History"
    source_url = "https://www.rba.gov.au/statistics/tables/xls/f01hist.xlsx"
    
    async def collect(self) -> CollectorResult:
        """Fetch historical interest rate data from RBA Excel file."""
        collected_at = datetime.now()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.source_url,
                    headers={
                        "User-Agent": "Yavin Data Collector (educational project)",
                    },
                    timeout=60.0,
                    follow_redirects=True,
                )
                response.raise_for_status()
                
                # Parse Excel file
                records = self.normalize(response.content)
                
                return CollectorResult(
                    collector_name=self.name,
                    source_url=self.source_url,
                    success=True,
                    records=records,
                    collected_at=collected_at,
                    metadata={"file_size": len(response.content)},
                )
                
        except httpx.HTTPError as e:
            return CollectorResult(
                collector_name=self.name,
                source_url=self.source_url,
                success=False,
                records=[],
                collected_at=collected_at,
                error_message=f"HTTP error: {str(e)}",
            )
        except Exception as e:
            return CollectorResult(
                collector_name=self.name,
                source_url=self.source_url,
                success=False,
                records=[],
                collected_at=collected_at,
                error_message=f"Unexpected error: {str(e)}",
            )

    def normalize(self, excel_content: bytes) -> list[dict[str, Any]]:
        """
        Parse RBA Excel file to extract interest rate history.
        
        Note: This requires pandas and openpyxl to be installed.
        """
        records = []
        
        try:
            import io
            import pandas as pd
            
            # Read the Excel file
            # The RBA Excel files typically have metadata rows at the top
            df = pd.read_excel(
                io.BytesIO(excel_content),
                sheet_name=0,
                header=None,
                engine="openpyxl",
            )
            
            # Find the header row (contains "Series ID" or dates)
            header_row = None
            for idx, row in df.iterrows():
                if "Series ID" in str(row.values) or "Cash Rate Target" in str(row.values):
                    header_row = idx
                    break
            
            if header_row is None:
                # Try to find row with dates
                for idx, row in df.iterrows():
                    if any("20" in str(val) for val in row.values if pd.notna(val)):
                        header_row = idx
                        break
            
            if header_row is not None:
                # Re-read with proper header
                df = pd.read_excel(
                    io.BytesIO(excel_content),
                    sheet_name=0,
                    header=header_row,
                    engine="openpyxl",
                )
                
                # Look for cash rate column
                cash_rate_col = None
                for col in df.columns:
                    if "cash" in str(col).lower() and "rate" in str(col).lower():
                        cash_rate_col = col
                        break
                
                if cash_rate_col:
                    # Extract time series
                    for idx, row in df.iterrows():
                        if pd.notna(row.get(cash_rate_col)):
                            try:
                                value = float(row[cash_rate_col])
                                # Try to get date from index or first column
                                date_val = row.get(df.columns[0], idx)
                                if isinstance(date_val, datetime):
                                    period = date_val.strftime("%Y-%m-%d")
                                else:
                                    period = str(date_val)
                                
                                records.append({
                                    "metric_name": "interest_rate_cash",
                                    "value": value,
                                    "period": period,
                                    "geography": "Australia",
                                    "unit": "percent",
                                    "source": "RBA F1 Table",
                                })
                            except (ValueError, TypeError):
                                continue
                                
        except ImportError:
            print("pandas or openpyxl not installed. Install with: uv add pandas openpyxl")
        except Exception as e:
            print(f"Error parsing RBA Excel: {e}")
            
        return records


class RBAInflationCollector(BaseCollector):
    """
    Collector for RBA Consumer Price Inflation data.
    
    Fetches from the G1 statistical table (Consumer Price Inflation).
    Quarterly data going back to 1922.
    """
    
    name = "RBA Inflation"
    source_url = "https://www.rba.gov.au/statistics/tables/xls/g01hist.xlsx"
    
    async def collect(self) -> CollectorResult:
        """Fetch inflation data from RBA Excel file."""
        collected_at = datetime.now()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.source_url,
                    headers={
                        "User-Agent": "Yavin Data Collector (educational project)",
                    },
                    timeout=60.0,
                    follow_redirects=True,
                )
                response.raise_for_status()
                
                records = self.normalize(response.content)
                
                return CollectorResult(
                    collector_name=self.name,
                    source_url=self.source_url,
                    success=True,
                    records=records,
                    collected_at=collected_at,
                    metadata={"file_size": len(response.content)},
                )
                
        except httpx.HTTPError as e:
            return CollectorResult(
                collector_name=self.name,
                source_url=self.source_url,
                success=False,
                records=[],
                collected_at=collected_at,
                error_message=f"HTTP error: {str(e)}",
            )
        except Exception as e:
            return CollectorResult(
                collector_name=self.name,
                source_url=self.source_url,
                success=False,
                records=[],
                collected_at=collected_at,
                error_message=f"Unexpected error: {str(e)}",
            )

    def normalize(self, excel_content: bytes) -> list[dict[str, Any]]:
        """
        Parse RBA G1 Excel file to extract inflation data.
        
        Key columns:
        - Column 1: Consumer Price Index (Index, 2011/12=100)
        - Column 2: Year-ended inflation (%)
        - Column 10: Year-ended trimmed mean inflation (%)
        """
        records = []
        
        try:
            import io
            import pandas as pd
            
            df = pd.read_excel(
                io.BytesIO(excel_content),
                sheet_name=0,
                header=None,
                engine="openpyxl",
            )
            
            # Data starts at row 11 (0-indexed), dates are in column 0
            # Row 1 has titles, Row 10 has Series IDs
            data_start = 11
            
            # Column mapping (0-indexed):
            # 0 = Date
            # 1 = CPI Index
            # 2 = Year-ended inflation (headline CPI)
            # 10 = Year-ended trimmed mean inflation (core measure)
            
            column_mapping = {
                2: ("inflation_cpi_annual", "Year-ended CPI inflation", "Per cent"),
                10: ("inflation_trimmed_mean_annual", "Year-ended trimmed mean inflation", "Per cent"),
            }
            
            for idx in range(data_start, len(df)):
                row = df.iloc[idx]
                date_val = row[0]
                
                if pd.isna(date_val):
                    continue
                    
                # Convert date to period string (YYYY-MM)
                if isinstance(date_val, datetime):
                    period = date_val.strftime("%Y-%m")
                else:
                    continue
                
                for col_idx, (metric_name, description, unit) in column_mapping.items():
                    value = row[col_idx]
                    if pd.notna(value):
                        try:
                            records.append({
                                "metric_name": metric_name,
                                "value": float(value),
                                "period": period,
                                "geography": "Australia",
                                "unit": unit,
                                "source": "RBA G1 Table",
                            })
                        except (ValueError, TypeError):
                            continue
                                
        except ImportError:
            print("pandas or openpyxl not installed.")
        except Exception as e:
            print(f"Error parsing RBA G1 Excel: {e}")
            
        return records


class RBAHousingLendingRatesCollector(BaseCollector):
    """
    Collector for RBA Housing Lending Rates data.
    
    Fetches from the F6 statistical table (Housing Lending Rates).
    Monthly data from July 2019.
    
    Key metrics:
    - Variable rate for owner-occupied housing (outstanding loans)
    - Variable rate for investment housing (outstanding loans)
    """
    
    name = "RBA Housing Lending Rates"
    source_url = "https://www.rba.gov.au/statistics/tables/xls/f06hist.xlsx"
    
    async def collect(self) -> CollectorResult:
        """Fetch housing lending rates from RBA Excel file."""
        collected_at = datetime.now()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.source_url,
                    headers={
                        "User-Agent": "Yavin Data Collector (educational project)",
                    },
                    timeout=60.0,
                    follow_redirects=True,
                )
                response.raise_for_status()
                
                records = self.normalize(response.content)
                
                return CollectorResult(
                    collector_name=self.name,
                    source_url=self.source_url,
                    success=True,
                    records=records,
                    collected_at=collected_at,
                    metadata={"file_size": len(response.content)},
                )
                
        except httpx.HTTPError as e:
            return CollectorResult(
                collector_name=self.name,
                source_url=self.source_url,
                success=False,
                records=[],
                collected_at=collected_at,
                error_message=f"HTTP error: {str(e)}",
            )
        except Exception as e:
            return CollectorResult(
                collector_name=self.name,
                source_url=self.source_url,
                success=False,
                records=[],
                collected_at=collected_at,
                error_message=f"Unexpected error: {str(e)}",
            )

    def normalize(self, excel_content: bytes) -> list[dict[str, Any]]:
        """
        Parse RBA F6 Excel file to extract housing lending rates.
        
        Key columns (0-indexed):
        - 4: Owner-occupied variable rate (all institutions, outstanding)
        - 25: Investment variable rate (all institutions, outstanding)
        """
        records = []
        
        try:
            import io
            import pandas as pd
            
            df = pd.read_excel(
                io.BytesIO(excel_content),
                sheet_name=0,
                header=None,
                engine="openpyxl",
            )
            
            # Data starts at row 11 (0-indexed)
            data_start = 11
            
            # Column mapping based on exploration:
            # Col 4: Owner-occupied variable rate (all institutions)
            # Col 25: Investment variable rate (all institutions)
            column_mapping = {
                4: ("housing_lending_rate_variable_owner_occupier", "Variable rate, owner-occupied, all institutions"),
                25: ("housing_lending_rate_variable_investor", "Variable rate, investment, all institutions"),
            }
            
            for idx in range(data_start, len(df)):
                row = df.iloc[idx]
                date_val = row[0]
                
                if pd.isna(date_val):
                    continue
                    
                if isinstance(date_val, datetime):
                    period = date_val.strftime("%Y-%m")
                else:
                    continue
                
                for col_idx, (metric_name, description) in column_mapping.items():
                    value = row[col_idx]
                    if pd.notna(value):
                        try:
                            records.append({
                                "metric_name": metric_name,
                                "value": float(value),
                                "period": period,
                                "geography": "Australia",
                                "unit": "Per cent per annum",
                                "source": "RBA F6 Table",
                            })
                        except (ValueError, TypeError):
                            continue
                                
        except ImportError:
            print("pandas or openpyxl not installed.")
        except Exception as e:
            print(f"Error parsing RBA F6 Excel: {e}")
            
        return records


class RBAMinutesCollector(BaseCollector):
    """
    Collector for RBA Monetary Policy Board Meeting Minutes.
    
    The Reserve Bank publishes minutes of the Monetary Policy Board meetings 
    two weeks after each meeting. These meetings are held eight times each year.
    
    Minutes contain detailed discussion on:
    - Financial conditions
    - Economic conditions  
    - Considerations for monetary policy
    - The decision (cash rate target)
    
    URL pattern: https://www.rba.gov.au/monetary-policy/rba-board-minutes/{year}/{year}-{month}-{day}.html
    """

    name = "RBA Meeting Minutes"
    source_url = "https://www.rba.gov.au/monetary-policy/rba-board-minutes/"
    
    # Base URL for minutes pages
    MINUTES_BASE_URL = "https://www.rba.gov.au/monetary-policy/rba-board-minutes/"

    async def collect(self, year: int | None = None) -> CollectorResult:
        """
        Fetch RBA meeting minutes.
        
        Args:
            year: Specific year to fetch. If None, fetches current year.
        """
        import re
        
        collected_at = datetime.now()
        target_year = year or collected_at.year
        
        try:
            async with httpx.AsyncClient() as client:
                # First, get the list of minutes for the year
                year_url = f"{self.MINUTES_BASE_URL}{target_year}/"
                
                response = await client.get(
                    year_url,
                    headers={
                        "User-Agent": "Yavin Data Collector (educational project)",
                    },
                    timeout=30.0,
                    follow_redirects=True,
                )
                response.raise_for_status()
                
                # Extract links to individual minutes
                html_content = response.text
                
                # Pattern to find minutes links like /2025/2025-12-09.html
                pattern = rf'href="[^"]*/{target_year}/({target_year}-\d{{2}}-\d{{2}})\.html"'
                matches = re.findall(pattern, html_content)
                
                # Remove duplicates and sort
                meeting_dates = sorted(set(matches), reverse=True)
                
                if not meeting_dates:
                    return CollectorResult(
                        collector_name=self.name,
                        source_url=year_url,
                        success=True,
                        records=[],
                        collected_at=collected_at,
                        metadata={"year": target_year, "message": "No minutes found for this year"},
                    )
                
                # Fetch each minutes page
                records = []
                for date_str in meeting_dates:
                    minutes_url = f"{self.MINUTES_BASE_URL}{target_year}/{date_str}.html"
                    
                    try:
                        minutes_response = await client.get(
                            minutes_url,
                            headers={
                                "User-Agent": "Yavin Data Collector (educational project)",
                            },
                            timeout=30.0,
                            follow_redirects=True,
                        )
                        minutes_response.raise_for_status()
                        
                        # Parse the minutes content
                        parsed = self._parse_minutes_page(minutes_response.text, date_str, minutes_url)
                        if parsed:
                            records.append(parsed)
                            
                    except httpx.HTTPError as e:
                        # Log but continue with other minutes
                        print(f"Failed to fetch minutes for {date_str}: {e}")
                        continue
                
                return CollectorResult(
                    collector_name=self.name,
                    source_url=year_url,
                    success=True,
                    records=records,
                    collected_at=collected_at,
                    metadata={
                        "year": target_year,
                        "minutes_count": len(records),
                        "meeting_dates": meeting_dates,
                    },
                )
                
        except httpx.HTTPError as e:
            return CollectorResult(
                collector_name=self.name,
                source_url=self.source_url,
                success=False,
                records=[],
                collected_at=collected_at,
                error_message=f"HTTP error: {str(e)}",
            )
        except Exception as e:
            return CollectorResult(
                collector_name=self.name,
                source_url=self.source_url,
                success=False,
                records=[],
                collected_at=collected_at,
                error_message=f"Unexpected error: {str(e)}",
            )

    def _parse_minutes_page(self, html_content: str, date_str: str, url: str) -> dict[str, Any] | None:
        """
        Parse a single minutes page to extract key content.
        
        Extracts:
        - Meeting date
        - Members participating
        - Key sections (Financial conditions, Economic conditions, etc.)
        - The decision (cash rate)
        """
        import html
        import re
        
        def clean_html(text: str) -> str:
            """Remove HTML tags and decode HTML entities."""
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', ' ', text)
            # Decode HTML entities like &nbsp;, &amp;, etc.
            text = html.unescape(text)
            # Normalize whitespace
            text = ' '.join(text.split())
            return text.strip()
        
        try:
            # Extract meeting date
            meeting_date = datetime.strptime(date_str, "%Y-%m-%d")
            
            # Extract members participating
            members_match = re.search(
                r'Members participating.*?</h2>\s*<p>(.*?)</p>',
                html_content,
                re.DOTALL | re.IGNORECASE
            )
            members = ""
            if members_match:
                members = clean_html(members_match.group(1))
            
            # Extract the decision section
            decision_match = re.search(
                r'The decision.*?</h2>\s*<p>(.*?)</p>',
                html_content,
                re.DOTALL | re.IGNORECASE
            )
            decision_text = ""
            cash_rate = None
            if decision_match:
                decision_text = clean_html(decision_match.group(1))
                # Try to extract cash rate value - look for patterns like:
                # "3.60 per cent", "4.10 per cent", "unchanged at 4.35 per cent"
                rate_patterns = [
                    r'at\s+(\d+\.\d+)\s*per\s*cent',  # "at 3.60 per cent"
                    r'to\s+(\d+\.\d+)\s*per\s*cent',  # "to 3.85 per cent"
                    r'(\d+\.\d+)\s*per\s*cent',       # fallback: any X.XX per cent
                ]
                for pattern in rate_patterns:
                    rate_match = re.search(pattern, decision_text, re.IGNORECASE)
                    if rate_match:
                        cash_rate = float(rate_match.group(1))
                        break
            
            # Extract main content sections
            sections = {}
            section_names = [
                "Financial conditions",
                "Economic conditions", 
                "Considerations for monetary policy",
                "International economic conditions",
                "Domestic economic conditions",
            ]
            
            for section_name in section_names:
                # Look for section header and extract following paragraphs
                pattern = rf'{section_name}.*?</h2>\s*(.*?)(?=<h2|$)'
                match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
                if match:
                    content = clean_html(match.group(1))
                    sections[section_name.lower().replace(" ", "_")] = content[:5000]  # Limit size
            
            # Build the record
            record = {
                "metric_name": "rba_meeting_minutes",
                "meeting_date": meeting_date.strftime("%Y-%m-%d"),
                "period": meeting_date.strftime("%Y-%m"),
                "geography": "Australia",
                "source": "RBA Monetary Policy Board Minutes",
                "source_url": url,
                "members_participating": members,
                "decision_text": decision_text,
                "cash_rate_decision": cash_rate,
                "sections": sections,
                # Full text for embedding/search (combine key sections)
                "full_text": f"RBA Meeting Minutes {date_str}\n\n{decision_text}\n\n" + 
                           "\n\n".join(f"{k}: {v}" for k, v in sections.items()),
            }
            
            return record
            
        except Exception as e:
            print(f"Error parsing minutes for {date_str}: {e}")
            return None

    def normalize(self, raw_data: Any) -> list[dict[str, Any]]:
        """
        Normalize is handled inline in collect() for this collector.
        """
        return []


class RBAUnemploymentCollector(BaseCollector):
    """
    Collector for RBA Labour Force / Unemployment data.
    
    Fetches from the H5 statistical table (Labour Force).
    Monthly data from February 1978.
    
    Key metrics:
    - Unemployment rate (seasonally adjusted)
    - Labour force participation rate
    - Employment to population ratio
    """
    
    name = "RBA Unemployment"
    source_url = "https://www.rba.gov.au/statistics/tables/xls/h05hist.xlsx"
    
    async def collect(self) -> CollectorResult:
        """Fetch unemployment data from RBA Excel file."""
        collected_at = datetime.now()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.source_url,
                    headers={
                        "User-Agent": "Yavin Data Collector (educational project)",
                    },
                    timeout=60.0,
                    follow_redirects=True,
                )
                response.raise_for_status()
                
                records = self.normalize(response.content)
                
                return CollectorResult(
                    collector_name=self.name,
                    source_url=self.source_url,
                    success=True,
                    records=records,
                    collected_at=collected_at,
                    metadata={"file_size": len(response.content)},
                )
                
        except httpx.HTTPError as e:
            return CollectorResult(
                collector_name=self.name,
                source_url=self.source_url,
                success=False,
                records=[],
                collected_at=collected_at,
                error_message=f"HTTP error: {str(e)}",
            )
        except Exception as e:
            return CollectorResult(
                collector_name=self.name,
                source_url=self.source_url,
                success=False,
                records=[],
                collected_at=collected_at,
                error_message=f"Unexpected error: {str(e)}",
            )

    def normalize(self, excel_content: bytes) -> list[dict[str, Any]]:
        """
        Parse RBA H5 Excel file to extract unemployment data.
        
        Key columns (0-indexed):
        - 2: Participation rate (%)
        - 8: Employment to population ratio (%)
        - 10: Unemployment rate (%)
        """
        records = []
        
        try:
            import io
            import pandas as pd
            
            df = pd.read_excel(
                io.BytesIO(excel_content),
                sheet_name=0,
                header=None,
                engine="openpyxl",
            )
            
            # Data starts at row 11 (0-indexed)
            data_start = 11
            
            # Column mapping based on exploration:
            column_mapping = {
                2: ("labour_force_participation_rate", "Participation rate"),
                8: ("employment_to_population_ratio", "Employment to population ratio"),
                10: ("unemployment_rate", "Unemployment rate"),
            }
            
            for idx in range(data_start, len(df)):
                row = df.iloc[idx]
                date_val = row[0]
                
                if pd.isna(date_val):
                    continue
                    
                if isinstance(date_val, datetime):
                    period = date_val.strftime("%Y-%m")
                else:
                    continue
                
                for col_idx, (metric_name, description) in column_mapping.items():
                    value = row[col_idx]
                    if pd.notna(value):
                        try:
                            records.append({
                                "metric_name": metric_name,
                                "value": float(value),
                                "period": period,
                                "geography": "Australia",
                                "unit": "Per cent",
                                "source": "RBA H5 Table",
                            })
                        except (ValueError, TypeError):
                            continue
                                
        except ImportError:
            print("pandas or openpyxl not installed.")
        except Exception as e:
            print(f"Error parsing RBA H5 Excel: {e}")
            
        return records
