# AlphaLedger

An autonomous Python agent that retrieves SEC EDGAR 10-K filings for major equity indices, extracts key financial metrics, and predicts future earnings performance — with a full Streamlit web UI.

No paid API keys required. All financial data is sourced directly from the [SEC EDGAR public APIs](https://www.sec.gov/developer).

---

## Features

- **Multi-index support** — Russell 3000, S&P 500, Russell 2000, or any custom CSV
- **Free SEC EDGAR data** — uses the public XBRL company facts API, no key needed
- **Financial metrics extracted from 10-K filings:**
  - Revenue (with 5 XBRL concept fallbacks per company)
  - Net Income
  - Earnings Per Share (EPS)
  - Revenue Growth % (year-over-year mean)
  - P/E Ratio (via live market cap from yfinance)
  - Predicted EPS (linear regression on historical trend)
- **Streamlit UI** — interactive charts, sector breakdowns, rankings table, CSV export
- **Checkpointing** — saves progress every 25 companies so interrupted runs resume automatically
- **Rate limiting & retry** — 0.15s delay between SEC requests, exponential backoff on errors

---

## Screenshots

### Rankings — Top Companies by Predicted EPS
Bar chart coloured by sector, with hover tooltips showing revenue, net income and P/E ratio.

### Sector View
Box plot showing the distribution of predicted EPS per sector, plus a sector summary table.

### Raw Data
Full results table with all metrics, sortable and downloadable as CSV.

---

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/isamkhan1809/AlphaLedger.git
cd AlphaLedger
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. (Optional) Set your SEC user-agent

The SEC asks that you identify your app in requests. Copy `.env.example` to `.env` and fill in your details:

```bash
cp .env.example .env
```

```
SEC_USER_AGENT=AlphaLedger YourName your@email.com
```

### 4. Run the web UI

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

### 5. Or run from the CLI

```bash
# Analyse top 100 Russell 3000 companies (2020-2023)
python agent.py --source russell3000 --max-companies 100 --output results.csv

# Analyse S&P 500
python agent.py --source sp500 --max-companies 50

# Analyse Russell 2000
python agent.py --source russell2000 --max-companies 50

# Analyse a custom list
python agent.py --source custom --custom-path my_tickers.csv
```

---

## Custom CSV Format

To analyse your own list of companies, provide a CSV with these columns:

| Column | Required | Description |
|---|---|---|
| `Ticker` | ✅ | Stock ticker symbol (e.g. AAPL) |
| `Name` | ✅ | Company name |
| `Sector` | ✅ | Sector (e.g. Information Technology) |
| `Market Value` | Optional | Used as P/E fallback if yfinance lookup fails |

Example:

```csv
Ticker,Name,Sector,Market Value
AAPL,Apple Inc,Technology,2800000000000
TSLA,Tesla Inc,Consumer Discretionary,600000000000
NVDA,Nvidia Corp,Technology,1100000000000
KO,Coca-Cola Co,Consumer Staples,260000000000
```

---

## How It Works

```
1. Load constituents
   └── Russell 3000 / S&P 500 / Russell 2000 / Custom CSV

2. Fetch ticker → CIK map
   └── https://www.sec.gov/files/company_tickers.json

3. For each company, fetch XBRL company facts
   └── https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json

4. Extract annual (10-K, FY) data points
   └── Revenue, Net Income, EPS
   └── Deduplicated by fiscal year (most recent filing wins)

5. Calculate metrics
   └── Avg Revenue, Avg Net Income
   └── Revenue Growth % (mean YoY)
   └── Predicted EPS (linear regression)
   └── P/E Ratio (yfinance market cap ÷ latest net income)

6. Save results + checkpoint every 25 companies

7. Display in Streamlit (Rankings, Sector View, Raw Data tabs)
```

---

## Project Structure

```
AlphaLedger/
├── agent.py            # Core analysis engine (SEC EDGAR + yfinance)
├── app.py              # Streamlit web UI
├── requirements.txt    # Python dependencies
├── .env.example        # SEC user-agent configuration template
├── russell-3000.csv    # Bundled Russell 3000 holdings (iShares, Dec 2022)
└── README.md
```

---

## Output Columns

| Column | Description |
|---|---|
| `ticker` | Stock ticker |
| `name` | Company name |
| `sector` | GICS sector |
| `predicted_eps` | Projected next-period EPS (linear regression) |
| `avg_revenue` | Mean annual revenue over the analysis period |
| `avg_net_income` | Mean annual net income over the analysis period |
| `revenue_growth_pct` | Mean year-over-year revenue growth % |
| `pe_ratio` | Current market cap ÷ latest annual net income |
| `filings_found` | Number of annual data points retrieved |
| `run_timestamp` | When this row was analysed |

---

## Data Sources

| Source | Provider | Cost |
|---|---|---|
| 10-K filing data | [SEC EDGAR XBRL API](https://data.sec.gov) | Free |
| Ticker → CIK map | [SEC EDGAR](https://www.sec.gov/files/company_tickers.json) | Free |
| Live market cap (P/E) | [yfinance](https://github.com/ranaroussi/yfinance) | Free |
| Russell 3000 / 2000 | [iShares ETF holdings](https://www.ishares.com) | Free (bundled CSV included) |
| S&P 500 | [Wikipedia](https://en.wikipedia.org/wiki/List_of_S%26P_500_companies) | Free |

---

## Requirements

- Python 3.9+
- See `requirements.txt` for all dependencies

```
pandas>=2.0
numpy>=1.24
requests>=2.31
scikit-learn>=1.3
streamlit>=1.35
plotly>=5.18
python-dotenv>=1.0
lxml>=4.9
yfinance>=0.2
```

---

## Limitations

- **Russell 3000 / 2000** — iShares blocks live CSV downloads, so the bundled `russell-3000.csv` (Dec 2022) is used as a fallback. The constituent list is static but all financial data is fetched live from SEC EDGAR.
- **P/E ratio** — uses current market cap from yfinance, not the historical market cap matching the filing period.
- **Predicted EPS** — based on simple linear regression over 1–4 annual data points. Treat as a trend indicator, not a forecast.
- **SEC rate limits** — the agent enforces 0.15s between requests. Analysing the full Russell 3000 (~3,000 companies) takes approximately 15–20 minutes.

---

## License

MIT
