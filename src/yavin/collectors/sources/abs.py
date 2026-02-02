"""
Australian Bureau of Statistics (ABS) collectors.

Fetches building approvals data from ABS.
Source: https://www.abs.gov.au/statistics/industry/building-and-construction/building-approvals-australia/
"""

import io
from datetime import datetime
from typing import Any

import httpx
import pandas as pd

from yavin.collectors.base import BaseCollector, CollectorResult


class ABSBuildingApprovalsHistoryCollector(BaseCollector):
    """
    Collector for historical ABS Building Approvals data.
    
    Downloads Table 06 Excel file containing dwelling approval statistics
    for Australia, providing monthly data going back to 1983.
    """

    name = "ABS Building Approvals History"
    source_url = "https://www.abs.gov.au/statistics/industry/building-and-construction/building-approvals-australia/latest-release"

    # The Australia national data file (Table 06)
    EXCEL_URL = "https://www.abs.gov.au/statistics/industry/building-and-construction/building-approvals-australia/nov-2025/8731006.xlsx"

    async def collect(self) -> CollectorResult:
        """Fetch building approvals historical data from ABS Excel file."""
        collected_at = datetime.now()

        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    self.EXCEL_URL,
                    timeout=60.0,
                    headers={
                        "User-Agent": "Yavin/1.0 (Housing Data Collector)",
                    },
                )
                response.raise_for_status()

                # Parse Excel file
                records = self.normalize(response.content)

                return CollectorResult(
                    collector_name=self.name,
                    source_url=self.EXCEL_URL,
                    success=True,
                    records=records,
                    collected_at=collected_at,
                    metadata={"observation_count": len(records)},
                )

        except httpx.HTTPError as e:
            return CollectorResult(
                collector_name=self.name,
                source_url=self.EXCEL_URL,
                success=False,
                records=[],
                collected_at=collected_at,
                error_message=f"HTTP error: {str(e)}",
            )
        except Exception as e:
            return CollectorResult(
                collector_name=self.name,
                source_url=self.EXCEL_URL,
                success=False,
                records=[],
                collected_at=collected_at,
                error_message=f"Unexpected error: {str(e)}",
            )

    def normalize(self, raw_data: Any) -> list[dict[str, Any]]:
        """
        Parse the ABS Building Approvals Excel file.
        
        The file has multiple sheets. We look for "Data1" which contains
        the main time series data with dates in column A and values in subsequent columns.
        """
        excel_data = io.BytesIO(raw_data) if isinstance(raw_data, bytes) else raw_data
        records = []

        try:
            # Read all sheets to find the right one
            xl = pd.ExcelFile(excel_data)
            
            # Try Data1 sheet first (common ABS pattern)
            sheet_name = None
            for name in xl.sheet_names:
                if "Data1" in name or name.startswith("Data"):
                    sheet_name = name
                    break
            
            if not sheet_name:
                sheet_name = xl.sheet_names[0]

            # ABS files typically have header rows, skip to find data
            excel_data.seek(0)
            df = pd.read_excel(excel_data, sheet_name=sheet_name, header=None)
            
            # Find the header row (contains "Series ID" or date-like values)
            header_row = None
            
            for idx, row in df.iterrows():
                row_vals = row.astype(str).str.lower()
                if row_vals.str.contains("series id|unit|frequency").any():
                    header_row = idx
                    break
            
            if header_row is None:
                # Fallback: look for first row with dates
                header_row = 9  # ABS typical header row
            
            # Read again with proper header
            excel_data.seek(0)
            df = pd.read_excel(
                excel_data,
                sheet_name=sheet_name,
                header=header_row,
                index_col=0,
            )
            
            # ABS format: First column is metadata (Series ID, Unit, etc.)
            # Data rows start after metadata rows
            # Find rows that look like dates
            data_start = None
            for idx, row_label in enumerate(df.index):
                if isinstance(row_label, datetime):
                    data_start = idx
                    break
                elif isinstance(row_label, str) and "-" in row_label:
                    # Could be "Jan-2024" format
                    try:
                        pd.to_datetime(row_label)
                        data_start = idx
                        break
                    except Exception:
                        pass
            
            if data_start is not None:
                df = df.iloc[data_start:]
            
            # Now parse the data - we want total dwellings approved
            # Column names typically describe the series
            for col_name in df.columns:
                col_name_str = str(col_name).lower()
                
                # Look for total dwelling units column (seasonally adjusted preferred)
                if "total" in col_name_str and "dwelling" in col_name_str:
                    is_seasonally_adjusted = "seasonally" in col_name_str
                    metric_name = (
                        "housing_approvals_total_sa" 
                        if is_seasonally_adjusted 
                        else "housing_approvals_total"
                    )
                    
                    for date_val, value in df[col_name].items():
                        if pd.isna(value):
                            continue
                            
                        # Convert date to period string
                        if isinstance(date_val, datetime):
                            period = date_val.strftime("%Y-%m")
                        else:
                            try:
                                dt = pd.to_datetime(date_val)
                                period = dt.strftime("%Y-%m")
                            except Exception:
                                continue
                        
                        records.append({
                            "metric_name": metric_name,
                            "value": float(value),
                            "period": period,
                            "geography": "Australia",
                            "unit": "Number of dwelling units",
                            "source": "ABS Building Approvals",
                            "adjustment": "seasonally_adjusted" if is_seasonally_adjusted else "original",
                        })
            
            # If no records found with header parsing, try alternative approach
            if not records:
                excel_data.seek(0)
                records = self._parse_excel_alternative(excel_data)

        except Exception as e:
            print(f"Error parsing ABS Excel: {e}")
            # Try alternative parsing
            try:
                excel_data.seek(0)
                records = self._parse_excel_alternative(excel_data)
            except Exception as e2:
                print(f"Alternative parsing also failed: {e2}")

        return records


class ABSWeeklyEarningsCollector(BaseCollector):
    """
    Collector for ABS Average Weekly Earnings data.
    
    Downloads Table 1 Excel file containing average weekly earnings
    for Australia (trend data). This is a semi-annual release (May and November).
    """

    name = "ABS Average Weekly Earnings"
    source_url = "https://www.abs.gov.au/statistics/labour/earnings-and-working-conditions/average-weekly-earnings-australia/latest-release"

    # Table 1: Average weekly earnings, Australia (dollars) - trend
    EXCEL_URL = "https://www.abs.gov.au/statistics/labour/earnings-and-working-conditions/average-weekly-earnings-australia/may-2025/6302001.xlsx"

    async def collect(self) -> CollectorResult:
        """Fetch average weekly earnings data from ABS Excel file."""
        collected_at = datetime.now()

        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    self.EXCEL_URL,
                    timeout=60.0,
                    headers={
                        "User-Agent": "Yavin/1.0 (Housing Data Collector)",
                    },
                )
                response.raise_for_status()

                records = self.normalize(response.content)

                return CollectorResult(
                    collector_name=self.name,
                    source_url=self.EXCEL_URL,
                    success=True,
                    records=records,
                    collected_at=collected_at,
                    metadata={"observation_count": len(records)},
                )

        except httpx.HTTPError as e:
            return CollectorResult(
                collector_name=self.name,
                source_url=self.EXCEL_URL,
                success=False,
                records=[],
                collected_at=collected_at,
                error_message=f"HTTP error: {str(e)}",
            )
        except Exception as e:
            return CollectorResult(
                collector_name=self.name,
                source_url=self.EXCEL_URL,
                success=False,
                records=[],
                collected_at=collected_at,
                error_message=f"Unexpected error: {str(e)}",
            )

    def normalize(self, raw_data: Any) -> list[dict[str, Any]]:
        """
        Parse the ABS Average Weekly Earnings Excel file.
        
        ABS structure:
        - Row 0: Series descriptions (e.g., "Earnings; Males; Full Time; Adult; Ordinary time earnings ;")
        - Rows 1-9: Metadata (Unit, Series Type, Data Type, Frequency, etc.)
        - Row 10+: Data (dates in column A, values in subsequent columns)
        
        Key metrics:
        - Full-time adult average weekly ordinary time earnings
        - Full-time adult average weekly total earnings
        - All employees average weekly total earnings
        """
        excel_data = io.BytesIO(raw_data) if isinstance(raw_data, bytes) else raw_data
        records = []

        try:
            # Read raw to get the structure
            df_raw = pd.read_excel(excel_data, sheet_name="Data1", header=None)
            
            # Row 0 has the series descriptions
            series_descriptions = df_raw.iloc[0].tolist()
            
            # Data starts at row 10 (after metadata rows)
            data_start_row = 10
            
            # Parse each column
            for col_idx in range(1, len(series_descriptions)):
                desc = str(series_descriptions[col_idx]).lower() if pd.notna(series_descriptions[col_idx]) else ""
                
                if not desc or desc == "nan":
                    continue
                
                # Parse the description: "Earnings; Males; Full Time; Adult; Ordinary time earnings ;"
                parts = [p.strip().lower() for p in desc.split(";") if p.strip()]
                
                # Determine sex
                sex_suffix = ""
                if "males" in parts:
                    sex_suffix = "_male"
                elif "females" in parts:
                    sex_suffix = "_female"
                elif "persons" in parts:
                    sex_suffix = ""  # Persons = combined, no suffix
                
                # Determine employment type
                is_fulltime = "full time" in parts or "full-time" in parts
                
                # Determine earnings type
                if "ordinary time earnings" in parts:
                    earnings_type = "avg_weekly_ordinary_earnings"
                elif "total earnings" in parts:
                    earnings_type = "avg_weekly_total_earnings"
                else:
                    continue  # Skip if not earnings data
                
                # Build metric name
                if is_fulltime and "adult" in parts:
                    metric_name = f"fulltime_adult{earnings_type}{sex_suffix}"
                else:
                    metric_name = f"all_employees{earnings_type}{sex_suffix}"
                
                # Extract data from this column
                for row_idx in range(data_start_row, len(df_raw)):
                    date_val = df_raw.iloc[row_idx, 0]
                    value = df_raw.iloc[row_idx, col_idx]
                    
                    if pd.isna(date_val) or pd.isna(value):
                        continue
                    
                    try:
                        val = float(value)
                    except (ValueError, TypeError):
                        continue
                    
                    # Convert date to period string
                    if isinstance(date_val, datetime):
                        period = date_val.strftime("%Y-%m")
                    else:
                        try:
                            dt = pd.to_datetime(date_val)
                            period = dt.strftime("%Y-%m")
                        except Exception:
                            continue
                    
                    records.append({
                        "metric_name": metric_name,
                        "value": val,
                        "period": period,
                        "geography": "Australia",
                        "unit": "AUD",
                        "source": "ABS Average Weekly Earnings",
                        "adjustment": "trend",
                    })

        except Exception as e:
            print(f"Error parsing ABS Weekly Earnings Excel: {e}")
            import traceback
            traceback.print_exc()

        return records

    def _parse_excel_alternative(self, excel_data: io.BytesIO) -> list[dict[str, Any]]:
        """
        Alternative parsing approach for ABS Excel files.
        
        ABS files have a specific structure:
        - Row 1-9: Metadata (Series ID, Description, etc.)  
        - Row 10+: Data with dates in column A
        """
        records = []
        
        excel_data.seek(0)
        xl = pd.ExcelFile(excel_data)
        
        # Find Data1 sheet
        sheet_name = None
        for name in xl.sheet_names:
            if "Data1" in name:
                sheet_name = name
                break
        
        if not sheet_name and xl.sheet_names:
            sheet_name = xl.sheet_names[0]
        
        if not sheet_name:
            return records
        
        # Read raw data
        df = pd.read_excel(excel_data, sheet_name=sheet_name, header=None)
        
        # Row 0 typically has column headers (Series ID or descriptions)
        # Row 1 might have unit info
        # Find the data start (first row with a date)
        data_start = None
        for idx in range(10, min(20, len(df))):
            val = df.iloc[idx, 0]
            if isinstance(val, datetime):
                data_start = idx
                break
        
        if data_start is None:
            return records
        
        # Get series descriptions from row 1 or nearby
        series_row = 0
        series_names = df.iloc[series_row].tolist()
        
        # Parse data rows
        for idx in range(data_start, len(df)):
            row = df.iloc[idx]
            date_val = row.iloc[0]
            
            if not isinstance(date_val, datetime):
                continue
            
            period = date_val.strftime("%Y-%m")
            
            # Column 1 onwards are data series
            for col_idx in range(1, len(row)):
                value = row.iloc[col_idx]
                series_name = str(series_names[col_idx]) if col_idx < len(series_names) else ""
                
                if pd.isna(value):
                    continue
                
                # Focus on total dwelling approvals
                series_lower = series_name.lower()
                if "total" in series_lower and "dwelling" in series_lower:
                    is_sa = "seasonally adjusted" in series_lower
                    metric = "housing_approvals_total_sa" if is_sa else "housing_approvals_total"
                    
                    records.append({
                        "metric_name": metric,
                        "value": float(value),
                        "period": period,
                        "geography": "Australia",
                        "unit": "Number of dwelling units",
                        "source": "ABS Building Approvals",
                        "series_description": series_name[:200],  # Truncate long descriptions
                    })
        
        return records


class ABSBuildingApprovalsCollector(BaseCollector):
    """
    Collector for ABS Building Approvals data via SDMX API.
    
    Fetches dwelling approval statistics from the ABS SDMX API.
    Note: The API can be slow/unreliable. Consider using 
    ABSBuildingApprovalsHistoryCollector for historical data.
    """

    name = "ABS Building Approvals"
    source_url = "https://api.data.abs.gov.au/data/ABS,BUILDING_APPROVALS"

    # ABS API endpoints
    BASE_URL = "https://api.data.abs.gov.au/data"
    DATAFLOW = "ABS,BUILDING_APPROVALS,1.0.0"

    async def collect(self) -> CollectorResult:
        """Fetch building approvals data from ABS API."""
        collected_at = datetime.now()

        try:
            async with httpx.AsyncClient() as client:
                # Fetch total dwelling approvals for Australia
                # M1 = Number of dwelling units, 2 = Total, AUS = Australia, M = Monthly
                url = f"{self.BASE_URL}/{self.DATAFLOW}/M1.2.AUS.M"
                
                response = await client.get(
                    url,
                    params={"format": "jsondata", "detail": "dataonly"},
                    headers={"Accept": "application/json"},
                    timeout=30.0,
                )
                response.raise_for_status()

                raw_data = response.json()
                records = self.normalize(raw_data)

                return CollectorResult(
                    collector_name=self.name,
                    source_url=url,
                    success=True,
                    records=records,
                    collected_at=collected_at,
                    metadata={"observation_count": len(records)},
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

    def normalize(self, raw_data: Any) -> list[dict[str, Any]]:
        """
        Normalize ABS SDMX JSON data.
        
        The ABS API returns data in SDMX-JSON format which is quite complex.
        We extract the observations and convert to simple dicts.
        """
        records = []

        try:
            # Navigate SDMX-JSON structure
            data_sets = raw_data.get("dataSets", [])
            if not data_sets:
                return records

            observations = data_sets[0].get("observations", {})
            
            # Get dimension values (time periods)
            structure = raw_data.get("structure", {})
            dimensions = structure.get("dimensions", {}).get("observation", [])
            
            # Find time dimension
            time_dimension = None
            for dim in dimensions:
                if dim.get("id") == "TIME_PERIOD":
                    time_dimension = dim
                    break

            if not time_dimension:
                return records

            time_values = time_dimension.get("values", [])

            # Extract observations
            for key, values in observations.items():
                # Key is the index into time dimension
                time_idx = int(key)
                if time_idx < len(time_values):
                    time_period = time_values[time_idx].get("id", "")
                    value = values[0] if values else None

                    records.append({
                        "metric_name": "housing_approvals_total",
                        "value": value,
                        "period": time_period,
                        "geography": "Australia",
                        "unit": "Number of dwelling units",
                        "source": "ABS Building Approvals",
                    })

        except (KeyError, IndexError, TypeError) as e:
            # Log error but return what we have
            print(f"Error normalizing ABS data: {e}")

        return records


class ABSLendingIndicatorsCollector(BaseCollector):
    """
    Collector for ABS Lending Indicators data.
    
    Downloads Table 1 Excel file containing housing finance statistics
    including loan commitments (number and value) for owner occupiers,
    investors, and first home buyers. Average loan size can be derived.
    
    Data is quarterly and goes back to 2002.
    """

    name = "ABS Lending Indicators"
    source_url = "https://www.abs.gov.au/statistics/economy/finance/lending-indicators/latest-release"

    # Table 1: Total dwellings by property purpose - values
    EXCEL_URL = "https://www.abs.gov.au/statistics/economy/finance/lending-indicators/sep-quarter-2025/560101.xlsx"

    async def collect(self) -> CollectorResult:
        """Fetch lending indicators data from ABS Excel file."""
        collected_at = datetime.now()

        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    self.EXCEL_URL,
                    timeout=60.0,
                    headers={
                        "User-Agent": "Yavin/1.0 (Housing Data Collector)",
                    },
                )
                response.raise_for_status()

                records = self.normalize(response.content)

                return CollectorResult(
                    collector_name=self.name,
                    source_url=self.EXCEL_URL,
                    success=True,
                    records=records,
                    collected_at=collected_at,
                    metadata={"observation_count": len(records)},
                )

        except httpx.HTTPError as e:
            return CollectorResult(
                collector_name=self.name,
                source_url=self.EXCEL_URL,
                success=False,
                records=[],
                collected_at=collected_at,
                error_message=f"HTTP error: {str(e)}",
            )
        except Exception as e:
            return CollectorResult(
                collector_name=self.name,
                source_url=self.EXCEL_URL,
                success=False,
                records=[],
                collected_at=collected_at,
                error_message=f"Unexpected error: {str(e)}",
            )

    def normalize(self, raw_data: Any) -> list[dict[str, Any]]:
        """
        Parse the ABS Lending Indicators Excel file.
        
        Structure:
        - Row 0: Series descriptions
        - Rows 1-9: Metadata (Unit, Series Type, etc.)
        - Row 10+: Data (dates in column A, values in subsequent columns)
        
        Key metrics to extract:
        - Number of loan commitments (total, owner occupier, investor, first home buyer)
        - Value of loan commitments ($ millions)
        - Average loan size (calculated: value / number * 1,000,000)
        """
        excel_data = io.BytesIO(raw_data) if isinstance(raw_data, bytes) else raw_data
        records = []

        try:
            df_raw = pd.read_excel(excel_data, sheet_name="Data1", header=None)
            
            # Row 0 has series descriptions
            series_descriptions = df_raw.iloc[0].tolist()
            # Row 1 has units
            units = df_raw.iloc[1].tolist()
            # Row 2 has series type (Original, Seasonally Adjusted, Trend)
            series_types = df_raw.iloc[2].tolist()
            
            # Data starts at row 10
            data_start_row = 10
            
            # Define which columns to extract and their metric names
            # Columns 1-10 are Original series:
            # 1: Total dwellings - Number
            # 2: Owner occupier - Number  
            # 3: Investor - Number
            # 4: Non-First Home Buyers - Number
            # 5: First home buyers - Number
            # 6: Total dwellings - Value ($ Millions)
            # 7: Owner occupier - Value
            # 8: Investor - Value
            # 9: Non-First Home Buyers - Value
            # 10: First home buyers - Value
            
            column_mapping = {
                1: ("loan_commitments_total_number", "Number"),
                2: ("loan_commitments_owner_occupier_number", "Number"),
                3: ("loan_commitments_investor_number", "Number"),
                5: ("loan_commitments_first_home_buyer_number", "Number"),
                6: ("loan_commitments_total_value", "$ Millions"),
                7: ("loan_commitments_owner_occupier_value", "$ Millions"),
                8: ("loan_commitments_investor_value", "$ Millions"),
                10: ("loan_commitments_first_home_buyer_value", "$ Millions"),
            }
            
            # Store data for calculating averages
            period_data = {}
            
            # Parse each column
            for col_idx, (metric_name, unit) in column_mapping.items():
                if col_idx >= len(series_descriptions):
                    continue
                    
                series_type = str(series_types[col_idx]).lower() if col_idx < len(series_types) and pd.notna(series_types[col_idx]) else "original"
                
                # Extract data
                for row_idx in range(data_start_row, len(df_raw)):
                    date_val = df_raw.iloc[row_idx, 0]
                    value = df_raw.iloc[row_idx, col_idx]
                    
                    if pd.isna(date_val) or pd.isna(value):
                        continue
                    
                    try:
                        val = float(value)
                    except (ValueError, TypeError):
                        continue
                    
                    # Convert date to period string (quarterly format)
                    if isinstance(date_val, datetime):
                        period = date_val.strftime("%Y-%m")
                    else:
                        try:
                            dt = pd.to_datetime(date_val)
                            period = dt.strftime("%Y-%m")
                        except Exception:
                            continue
                    
                    # Store for average calculation
                    if period not in period_data:
                        period_data[period] = {}
                    period_data[period][metric_name] = val
                    
                    records.append({
                        "metric_name": metric_name,
                        "value": val,
                        "period": period,
                        "geography": "Australia",
                        "unit": unit,
                        "source": "ABS Lending Indicators",
                        "adjustment": series_type,
                    })
            
            # Calculate average loan sizes
            # Average = (Value in $ Millions) / Number * 1,000,000 = Value / Number * 1000 (in $thousands)
            avg_mapping = {
                ("loan_commitments_total_value", "loan_commitments_total_number"): "avg_loan_size_total",
                ("loan_commitments_owner_occupier_value", "loan_commitments_owner_occupier_number"): "avg_loan_size_owner_occupier",
                ("loan_commitments_investor_value", "loan_commitments_investor_number"): "avg_loan_size_investor",
                ("loan_commitments_first_home_buyer_value", "loan_commitments_first_home_buyer_number"): "avg_loan_size_first_home_buyer",
            }
            
            for period, metrics in period_data.items():
                for (val_key, num_key), avg_name in avg_mapping.items():
                    if val_key in metrics and num_key in metrics and metrics[num_key] > 0:
                        avg_value = (metrics[val_key] / metrics[num_key]) * 1000  # Convert to $thousands
                        records.append({
                            "metric_name": avg_name,
                            "value": round(avg_value, 2),
                            "period": period,
                            "geography": "Australia",
                            "unit": "$ Thousands",
                            "source": "ABS Lending Indicators (calculated)",
                            "adjustment": "original",
                        })

        except Exception as e:
            print(f"Error parsing ABS Lending Indicators Excel: {e}")
            import traceback
            traceback.print_exc()

        return records
