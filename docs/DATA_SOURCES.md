# Data Sources

## Overview

This document catalogs data sources for the Yavin system, organized by domain. Each source includes access method, rate limits, data available, and implementation notes.

---

## Australian Economic Data

### Australian Bureau of Statistics (ABS)

**Website**: https://www.abs.gov.au  
**API**: https://api.data.abs.gov.au  
**Documentation**: https://api.data.abs.gov.au/

| Dataset                     | Update Frequency | Key Metrics                       | Notes         |
| --------------------------- | ---------------- | --------------------------------- | ------------- |
| Building Approvals (8731.0) | Monthly          | Dwelling approvals by type, state | Free, no auth |
| Migration (3412.0)          | Quarterly        | Net overseas migration            | Free, no auth |
| Population (3101.0)         | Quarterly        | Population estimates              | Free, no auth |
| Labour Force (6202.0)       | Monthly          | Employment, unemployment          | Free, no auth |
| CPI (6401.0)                | Quarterly        | Inflation measures                | Free, no auth |

**API Notes**:

- Uses SDMX (Statistical Data and Metadata Exchange) format
- REST API with JSON responses available
- No authentication required
- Rate limiting: Be respectful, no official limit

**Example Request**:

```
GET https://api.data.abs.gov.au/data/ABS,BUILDING_APPROVALS/M1.2.AUS.M
```

---

### Reserve Bank of Australia (RBA)

**Website**: https://www.rba.gov.au  
**Statistics**: https://www.rba.gov.au/statistics/

| Dataset                | Update Frequency | Key Metrics               | Notes     |
| ---------------------- | ---------------- | ------------------------- | --------- |
| Cash Rate Target       | As changed       | Official interest rate    | RSS/Web   |
| Lending Rates (F5)     | Monthly          | Mortgage rates            | Excel/CSV |
| Credit Aggregates (D2) | Monthly          | Housing credit growth     | Excel/CSV |
| Housing Loans (E2)     | Monthly          | Loan approvals            | Excel/CSV |
| Meeting Minutes        | 8x per year      | Monetary policy rationale | HTML      |

**Access Notes**:

- No formal API, but structured data available
- Excel files at predictable URLs
- RSS feed for announcements
- Consider caching with monthly refresh

**Meeting Minutes**:

The RBA publishes minutes of Monetary Policy Board meetings two weeks after each meeting (8 times per year). Minutes contain detailed discussion on financial conditions, economic conditions, and monetary policy considerations.

```
https://www.rba.gov.au/monetary-policy/rba-board-minutes/{year}/{year}-{month}-{day}.html
```

**Data URLs**:

```
https://www.rba.gov.au/statistics/tables/xls/f05hist.xls
https://www.rba.gov.au/statistics/tables/xls/d02hist.xls
```

---

## Property Data

### Domain.com.au

**Website**: https://www.domain.com.au  
**API**: https://developer.domain.com.au/

| Data Point      | Access Method | Notes                 |
| --------------- | ------------- | --------------------- |
| Listing counts  | API           | Requires registration |
| Suburb profiles | API           | Free tier available   |
| Price estimates | API           | Paid plans            |

**API Notes**:

- Free tier: 500 calls/day
- Requires OAuth2 authentication
- Good for listing counts and trends

---

### CoreLogic / PropTrack

**Note**: Premium services, may need to evaluate cost-benefit.

| Data Point    | Access Method | Notes |
| ------------- | ------------- | ----- |
| Median prices | API/Reports   | Paid  |
| Price indices | API/Reports   | Paid  |

**Alternative**: Use news articles that cite CoreLogic data.

---

## News & Media

### NewsAPI

**Website**: https://newsapi.org  
**Pricing**: Free tier (100 requests/day, delayed), Paid from $449/mo

| Feature      | Free Tier | Paid         |
| ------------ | --------- | ------------ |
| Requests/day | 100       | 1000+        |
| Historical   | 1 month   | Full archive |
| Delay        | Yes       | Real-time    |

**Best for**: General news monitoring, sentiment tracking

---

### Google News RSS

**Access**: Free, no API key  
**Format**: RSS/Atom

**URL Pattern**:

```
https://news.google.com/rss/search?q=australian+housing+market&hl=en-AU&gl=AU&ceid=AU:en
```

**Notes**:

- Free but limited metadata
- No full article text (titles and snippets only)
- Good for coverage volume tracking

---

### ABC News RSS

**Website**: https://www.abc.net.au/news/feeds/

| Feed        | URL                                            |
| ----------- | ---------------------------------------------- |
| Top Stories | https://www.abc.net.au/news/feed/51120/rss.xml |
| Business    | https://www.abc.net.au/news/feed/51892/rss.xml |

**Notes**:

- Free, reliable Australian news
- Full articles available via web scraping (respect robots.txt)

---

## Global Economic Data

### FRED (Federal Reserve Economic Data)

**Website**: https://fred.stlouisfed.org  
**API**: https://fred.stlouisfed.org/docs/api/

| Dataset           | Notes                           |
| ----------------- | ------------------------------- |
| US Interest Rates | Fed funds rate, treasury yields |
| Commodity Prices  | Oil, gold, etc.                 |
| Exchange Rates    | Currency pairs                  |

**API Notes**:

- Free API key required
- 120 requests/minute
- Excellent historical data

---

### World Bank Open Data

**Website**: https://data.worldbank.org  
**API**: https://datahelpdesk.worldbank.org/knowledgebase/topics/125589

| Dataset                | Notes                  |
| ---------------------- | ---------------------- |
| GDP                    | By country, historical |
| Population             | Global data            |
| Development Indicators | 1000+ indicators       |

**API Notes**:

- Free, no authentication
- JSON and XML formats
- Annual data (not high frequency)

---

## Commodity Data

### Yahoo Finance

**Access**: yfinance Python library  
**Cost**: Free

| Data Point | Symbol Examples |
| ---------- | --------------- |
| Gold       | GC=F            |
| Oil (WTI)  | CL=F            |
| Iron Ore   | TIOE.SI (proxy) |
| Copper     | HG=F            |

**Notes**:

- Unofficial API via library
- May break occasionally
- Good for daily prices

---

### EIA (U.S. Energy Information Administration)

**Website**: https://www.eia.gov  
**API**: https://www.eia.gov/opendata/

| Dataset          | Notes           |
| ---------------- | --------------- |
| Oil Inventories  | Weekly          |
| Natural Gas      | Prices, storage |
| Renewable Energy | Production data |

**API Notes**:

- Free API key required
- Good rate limits
- Authoritative energy data

---

## Conflict & Geopolitical Data

### ACLED (Armed Conflict Location & Event Data)

**Website**: https://acleddata.com  
**API**: https://acleddata.com/data-export-tool/

| Data Point         | Notes                        |
| ------------------ | ---------------------------- |
| Conflict Events    | Date, location, type, actors |
| Fatality Estimates | Per event                    |
| Geographic Data    | Lat/long coordinates         |

**Access Notes**:

- Free for researchers/non-commercial
- Registration required
- Weekly updates

---

### GDELT (Global Database of Events, Language, and Tone)

**Website**: https://www.gdeltproject.org  
**API**: https://blog.gdeltproject.org/gdelt-2-0-our-global-world-in-realtime/

| Feature       | Notes                     |
| ------------- | ------------------------- |
| Global Events | Real-time event detection |
| Tone Analysis | Sentiment of coverage     |
| Geographic    | Event locations           |

**Notes**:

- Free, massive scale
- Complex to query
- Good for media coverage analysis

---

## Implementation Priority

### Phase 1 (Housing Agent)

| Source                 | Priority    | Difficulty | Notes             |
| ---------------------- | ----------- | ---------- | ----------------- |
| ABS Building Approvals | ⭐⭐⭐ High | Easy       | Core metric       |
| RBA Interest Rates     | ⭐⭐⭐ High | Medium     | Parse Excel       |
| RBA Credit Aggregates  | ⭐⭐⭐ High | Medium     | Parse Excel       |
| Google News RSS        | ⭐⭐ Medium | Easy       | Coverage tracking |
| ABC News RSS           | ⭐⭐ Medium | Easy       | Quality articles  |
| Domain API             | ⭐ Low      | Medium     | Nice to have      |

### Future Phases

Additional data sources will be prioritized based on which specialized agents are developed next. See the other sections in this document for available sources covering commodities, conflicts, global economics, and more.

---

## Rate Limit Management

```python
# Example rate limiter configuration
RATE_LIMITS = {
    "abs_api": {"calls_per_minute": 30},
    "rba_web": {"calls_per_hour": 10},
    "newsapi": {"calls_per_day": 100},
    "domain_api": {"calls_per_day": 500},
}
```

---

## Data Freshness Requirements

| Data Type          | Max Age  | Collection Frequency    |
| ------------------ | -------- | ----------------------- |
| Interest Rates     | 1 day    | Daily                   |
| Building Approvals | 1 month  | Monthly (when released) |
| News Articles      | 1 hour   | Hourly                  |
| Commodity Prices   | 1 day    | Daily                   |
| Migration Data     | 3 months | Quarterly               |
