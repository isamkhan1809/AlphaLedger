<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=0,2,4&height=200&section=header&text=AlphaLedger&fontSize=80&fontColor=fff&animation=twinkling&fontAlignY=35&desc=Autonomous%20SEC%20Intelligence%20%E2%80%94%20Zero%20Cost%2C%20Full%20Power&descAlignY=60&descSize=20" width="100%"/>

<br/>

[![Python](https://img.shields.io/badge/Python-3.9%2B-00C851?style=for-the-badge&logo=python&logoColor=white&labelColor=0D0D0D)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-Live-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white&labelColor=0D0D0D)](https://streamlit.io)
[![SEC EDGAR](https://img.shields.io/badge/SEC-EDGAR%20API-00C851?style=for-the-badge&logoColor=white&labelColor=0D0D0D)](https://www.sec.gov/developer)
[![License](https://img.shields.io/badge/License-MIT-FFD700?style=for-the-badge&labelColor=0D0D0D)](LICENSE)

<br/>

<a href="https://github.com/isamkhan1809/AlphaLedger">
  <img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=700&size=22&pause=1000&color=00C851&center=true&vCenter=true&width=700&lines=Mine+10-K+Filings+Across+Thousands+of+Companies;Predict+Future+Earnings+%E2%80%94+Zero+Cost;Russell+3000+%7C+S%26P+500+%7C+Custom+Index;No+Bloomberg.+No+API+Keys.+Just+SEC+Data." alt="Typing SVG" />
</a>

</div>

---

<br/>

<div align="center">

```
  ╔══════════════════════════════════════════════════════════════╗
  ║                                                              ║
  ║   Every year, thousands of companies file their secrets      ║
  ║   with the SEC — revenue, earnings, growth, trajectory.      ║
  ║                                                              ║
  ║       AlphaLedger reads them all. For free.                  ║
  ║                                                              ║
  ╚══════════════════════════════════════════════════════════════╝
```

</div>

<br/>

## `>_ The Story`

> *Hidden inside every 10-K filing is the financial DNA of a company — revenue trends, earnings trajectories, the quiet signals that precede big moves.*
>
> *AlphaLedger is an autonomous agent that reads thousands of them, extracts the metrics that matter, and surfaces what's coming next.*
>
> *No terminal fees. No data subscriptions. Just Python, SEC EDGAR, and machine learning.*

<br/>

## `>_ What It Does`

<table>
<tr>
<td width="50%">

**Point it at an index:**
```
russell3000
sp500
russell2000
custom CSV
```

</td>
<td width="50%">

**Get back intelligence:**
```
AAPL  predicted_eps: 6.84   pe: 28.4
NVDA  predicted_eps: 22.1   pe: 61.2
MSFT  predicted_eps: 11.3   pe: 33.1
TSLA  predicted_eps: 3.92   pe: 72.8
```

</td>
</tr>
</table>

<br/>

## `>_ The Pipeline`

```
┌─────────────────────────────────────────────────────────────┐
│                      ALPHALEDGER ENGINE                     │
│                                                             │
│  ┌─────────────┐     ┌──────────────┐     ┌─────────────┐  │
│  │  Index CSV  │────▶│ CIK Resolver │────▶│  SEC EDGAR  │  │
│  │  Russell /  │     │              │     │  XBRL API   │  │
│  │  S&P / Any  │     │  ticker→CIK  │     │             │  │
│  └─────────────┘     └──────────────┘     └──────┬──────┘  │
│                                                  │         │
│                                    ┌─────────────▼──────┐  │
│                                    │   Metric Extractor  │  │
│                                    │   Revenue · EPS     │  │
│                                    │   Net Income · P/E  │  │
│                                    └─────────────┬──────┘  │
│                                                  │         │
│                                    ┌─────────────▼──────┐  │
│                                    │  Linear Regression  │  │
│                                    │  Predicted EPS      │  │
│                                    │  Checkpoint: /25    │  │
│                                    └─────────────┬──────┘  │
│                                                  │         │
│                                    ┌─────────────▼──────┐  │
│                                    │  Streamlit Dashboard│  │
│                                    │  Rankings · Sectors │  │
│                                    │  CSV Export         │  │
│                                    └────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

<br/>

## `>_ Get Running`

```bash
# Clone
git clone https://github.com/isamkhan1809/AlphaLedger.git
cd AlphaLedger

# Install
pip install -r requirements.txt

# Optional — identify yourself to the SEC
cp .env.example .env
# SEC_USER_AGENT=AlphaLedger YourName your@email.com

# Launch dashboard
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) — no API keys, no subscriptions, no friction.

<br/>

## `>_ CLI Mode`

```bash
# Russell 3000 — top 100
python agent.py --source russell3000 --max-companies 100 --output results.csv

# S&P 500
python agent.py --source sp500 --max-companies 50

# Your own list
python agent.py --source custom --custom-path my_tickers.csv
```

<br/>

## `>_ Output`

| Column | Description |
|---|---|
| `ticker` | Stock symbol |
| `predicted_eps` | Projected next-period EPS (linear regression) |
| `avg_revenue` | Mean annual revenue |
| `avg_net_income` | Mean annual net income |
| `revenue_growth_pct` | Mean YoY growth % |
| `pe_ratio` | Market cap ÷ net income |
| `filings_found` | Annual data points retrieved |

<br/>

## `>_ Tech Stack`

<div align="center">

| Layer | Technology |
|---|---|
| **Agent** | Python 3.9+ |
| **Data** | SEC EDGAR XBRL API (free) |
| **Market Data** | yfinance |
| **ML** | scikit-learn (Linear Regression) |
| **Dashboard** | Streamlit + Plotly |
| **Resumability** | CSV checkpointing every 25 companies |

</div>

<br/>

## `>_ Project Structure`

```
AlphaLedger/
├── agent.py            # Autonomous analysis engine
├── app.py              # Streamlit dashboard
├── requirements.txt
├── .env.example
└── russell-3000.csv    # Bundled Dec 2022 holdings
```

<br/>

---

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=0,2,4&height=120&section=footer&animation=twinkling" width="100%"/>

<br/>

*The SEC publishes everything. AlphaLedger reads it.*
*Free data. Real intelligence. No paywalls.*

<br/>

[![GitHub](https://img.shields.io/badge/github-isamkhan1809-00C851?style=for-the-badge&logo=github&logoColor=white&labelColor=0D0D0D)](https://github.com/isamkhan1809)

</div>
