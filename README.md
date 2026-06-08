<div align="center">

```
 █████╗ ██╗     ██████╗ ██╗  ██╗ █████╗ ██╗     ███████╗██████╗  ██████╗ ███████╗██████╗
██╔══██╗██║     ██╔══██╗██║  ██║██╔══██╗██║     ██╔════╝██╔══██╗██╔════╝ ██╔════╝██╔══██╗
███████║██║     ██████╔╝███████║███████║██║     █████╗  ██║  ██║██║  ███╗█████╗  ██████╔╝
██╔══██║██║     ██╔═══╝ ██╔══██║██╔══██║██║     ██╔══╝  ██║  ██║██║   ██║██╔══╝  ██╔══██╗
██║  ██║███████╗██║     ██║  ██║██║  ██║███████╗███████╗██████╔╝╚██████╔╝███████╗██║  ██║
╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝
```

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=20&pause=1000&color=00D9FF&center=true&vCenter=true&width=700&lines=Autonomous+SEC+EDGAR+Intelligence+%F0%9F%93%88;Mine+10-K+Filings+Across+Thousands+of+Companies;Predict+Future+Earnings+%E2%80%94+Zero+Cost%2C+Full+Power;Russell+3000+%7C+S%26P+500+%7C+Custom+Index+Support" alt="Typing SVG" />

<img src="https://media.giphy.com/media/bvPScI7z27Fap4uHiA/giphy.gif" width="360" />

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![SEC EDGAR](https://img.shields.io/badge/Data-SEC%20EDGAR-003087?style=for-the-badge)](https://www.sec.gov/developer)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

> **An autonomous Python agent that mines SEC EDGAR 10-K filings, extracts financial DNA from thousands of companies, and predicts future earnings — all for free.**

</div>

---

## ◈ What Is AlphaLedger?

AlphaLedger is a fully autonomous financial intelligence agent. Point it at the **Russell 3000**, **S&P 500**, **Russell 2000**, or your own custom ticker list — and it does the rest. No Bloomberg terminal. No paid API keys. Just raw SEC data, machine learning, and a Streamlit dashboard.

```
┌─────────────────────────────────────────────────────────────┐
│  LOAD INDEX  →  FETCH 10-K DATA  →  EXTRACT METRICS         │
│      ↓                ↓                    ↓                 │
│  Russell 3000    SEC EDGAR API        Revenue / EPS          │
│  S&P 500         XBRL company         Net Income             │
│  Russell 2000    facts endpoint       Growth Rate            │
│  Custom CSV                           P/E Ratio              │
│                           ↓                                  │
│               LINEAR REGRESSION  →  PREDICTED EPS           │
│                           ↓                                  │
│                STREAMLIT DASHBOARD  →  EXPORT CSV            │
└─────────────────────────────────────────────────────────────┘
```

---

## ◈ Feature Arsenal

| Feature | Description |
|---|---|
| **Multi-Index Support** | Russell 3000, S&P 500, Russell 2000, or any custom CSV |
| **Free SEC Data** | XBRL company facts API — no key, no cost |
| **Revenue Extraction** | 5 XBRL concept fallbacks per company |
| **EPS Prediction** | Linear regression on historical trend |
| **P/E Ratio** | Live market cap via yfinance |
| **Checkpointing** | Auto-saves every 25 companies — resume interrupted runs |
| **Rate Limiting** | 0.15s delays + exponential backoff on errors |
| **Streamlit UI** | Interactive charts, sector views, downloadable CSV |

---

## ◈ Quick Start

```bash
# 1. Clone
git clone https://github.com/isamkhan1809/AlphaLedger.git
cd AlphaLedger

# 2. Install
pip install -r requirements.txt

# 3. (Optional) Set your SEC user-agent
cp .env.example .env
# Edit .env: SEC_USER_AGENT=AlphaLedger YourName your@email.com

# 4. Launch the dashboard
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) — the dashboard appears.

---

## ◈ CLI Mode

```bash
# Analyse top 100 Russell 3000 companies
python agent.py --source russell3000 --max-companies 100 --output results.csv

# S&P 500
python agent.py --source sp500 --max-companies 50

# Your own list
python agent.py --source custom --custom-path my_tickers.csv
```

---

## ◈ How It Works — The Pipeline

```
① Load index constituents
   └── Russell / S&P / Custom CSV

② Resolve ticker → CIK
   └── https://www.sec.gov/files/company_tickers.json

③ Fetch XBRL company facts per CIK
   └── https://data.sec.gov/api/xbrl/companyfacts/CIK{n}.json

④ Extract annual 10-K data points
   └── Revenue · Net Income · EPS
   └── Deduplicated by fiscal year

⑤ Compute metrics
   └── Avg Revenue, Avg Net Income
   └── Revenue Growth % (mean YoY)
   └── Predicted EPS (linear regression)
   └── P/E (yfinance market cap ÷ net income)

⑥ Checkpoint every 25 companies

⑦ Render Streamlit dashboard
   └── Rankings · Sector View · Raw Data · CSV Export
```

---

## ◈ Output Columns

| Column | Description |
|---|---|
| `ticker` | Stock ticker symbol |
| `predicted_eps` | Projected next-period EPS |
| `avg_revenue` | Mean annual revenue |
| `avg_net_income` | Mean annual net income |
| `revenue_growth_pct` | Mean YoY revenue growth % |
| `pe_ratio` | Market cap ÷ net income |
| `filings_found` | Annual data points retrieved |

---

## ◈ Data Sources — All Free

| Source | Provider |
|---|---|
| 10-K filings | SEC EDGAR XBRL API |
| Ticker → CIK map | SEC EDGAR |
| Live market cap | yfinance |
| Russell 3000/2000 | iShares ETF holdings (bundled) |
| S&P 500 | Wikipedia |

---

## ◈ Project Structure

```
AlphaLedger/
├── agent.py            ← Core analysis engine
├── app.py              ← Streamlit web UI
├── requirements.txt
├── .env.example
├── russell-3000.csv    ← Bundled Dec 2022 holdings
└── README.md
```

---

## ◈ Limitations

- **Russell 3000/2000** — iShares blocks live CSV downloads; bundled Dec 2022 holdings used as fallback
- **P/E ratio** — uses current market cap, not historical
- **Predicted EPS** — linear regression on 1–4 data points; treat as trend, not forecast
- **Full Russell 3000** — ~15–20 minutes due to SEC rate limits

---

<div align="center">

**Built with Python · Powered by SEC EDGAR · Zero Paywalls**

*MIT License*

<br/>

Interested in financial intelligence, SEC data pipelines, or AI-driven investing tools?<br/>
Let's connect — built by <a href="https://github.com/isamkhan1809">Isam Khan</a> &nbsp;|&nbsp;
<a href="https://linkedin.com/in/isam-khan-3a1260292"><img src="https://img.shields.io/badge/-LinkedIn-0A66C2?style=flat-square&logo=linkedin&logoColor=white&labelColor=000000"/></a>
<a href="https://isamkhan.com"><img src="https://img.shields.io/badge/-isamkhan.com-00D9FF?style=flat-square&logo=googlechrome&logoColor=white&labelColor=000000"/></a>

</div>
