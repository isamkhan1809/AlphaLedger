# agent.py
# Requirements: pandas, numpy, requests, scikit-learn, python-dotenv
# Install: pip install pandas numpy requests scikit-learn python-dotenv lxml
#
# Uses free SEC EDGAR APIs — no API key required.
# Set SEC_USER_AGENT env var (see .env.example) to identify your app to SEC.

import os
import time
import logging
import csv
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import yfinance as yf
from dotenv import load_dotenv
from sklearn.linear_model import LinearRegression

load_dotenv()

# Suppress SSL warnings from requests on macOS (missing CA certs for external sites)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "EquityLens contact@example.com")
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
CHECKPOINT_FILE = "checkpoint.csv"
CHECKPOINT_INTERVAL = 25
REQUEST_DELAY = 0.15  # seconds between SEC requests
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # seconds

REVENUE_CONCEPTS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",
    "SalesRevenueGoodsNet",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
]

HEADERS = {"User-Agent": SEC_USER_AGENT, "Accept": "application/json"}


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _get_with_retry(url: str, headers: dict, retries: int = MAX_RETRIES) -> requests.Response:
    """GET request with exponential backoff on HTTP errors."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200:
                return resp
            if resp.status_code == 404:
                return resp  # not retryable
            if resp.status_code == 429 or resp.status_code >= 500:
                wait = RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning("HTTP %d for %s — retrying in %ds", resp.status_code, url, wait)
                time.sleep(wait)
                continue
            return resp
        except requests.RequestException as exc:
            wait = RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning("Request error (%s) for %s — retrying in %ds", exc, url, wait)
            time.sleep(wait)
    logger.error("Giving up on %s after %d retries", url, retries)
    return requests.Response()  # empty response


# ---------------------------------------------------------------------------
# Ticker -> CIK map
# ---------------------------------------------------------------------------

_TICKER_CIK_MAP: dict = {}


def _load_ticker_cik_map() -> dict:
    global _TICKER_CIK_MAP
    if _TICKER_CIK_MAP:
        return _TICKER_CIK_MAP
    logger.info("Fetching ticker->CIK map from SEC EDGAR ...")
    resp = _get_with_retry(TICKERS_URL, HEADERS)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to fetch ticker map: HTTP {resp.status_code}")
    data = resp.json()
    mapping = {}
    for entry in data.values():
        ticker = str(entry.get("ticker", "")).upper()
        cik = str(entry.get("cik_str", "")).zfill(10)
        if ticker:
            mapping[ticker] = cik
    _TICKER_CIK_MAP = mapping
    logger.info("Loaded %d tickers from SEC EDGAR", len(mapping))
    return mapping


def get_cik(ticker: str):
    mapping = _load_ticker_cik_map()
    return mapping.get(ticker.upper())


# ---------------------------------------------------------------------------
# iShares URL builder
# ---------------------------------------------------------------------------

def _get_ishares_url(fund_ticker: str = "IWV") -> list:
    """
    Return a list of candidate iShares CSV URLs to try (newest date first).
    fund_ticker: IWV = Russell 3000, IWM = Russell 2000
    """
    product_ids = {
        "IWV": "239714/ishares-russell-3000-etf",
        "IWM": "239696/ishares-russell-2000-etf",
    }
    product_path = product_ids.get(fund_ticker, product_ids["IWV"])
    urls = []
    for days_back in range(1, 11):
        date = datetime.now() - timedelta(days=days_back)
        date_str = date.strftime("%Y%m%d")
        url = (
            f"https://www.ishares.com/us/products/{product_path}"
            f"/1467271812596.ajax?fileType=csv&fileName={fund_ticker}_holdings"
            f"&dataType=fund&asOfDate={date_str}"
        )
        urls.append(url)
    return urls


LOCAL_FALLBACK = {
    "IWV": Path(__file__).parent / "russell-3000.csv",
    "IWM": Path(__file__).parent / "russell-2000.csv",
}


def _parse_ishares_text(text: str, fund_ticker: str) -> pd.DataFrame:
    """Parse iShares CSV text (with metadata header rows) into a clean DataFrame."""
    from io import StringIO
    lines = text.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if "Ticker" in line and "Name" in line:
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("Could not find header row in iShares CSV")
    df = pd.read_csv(StringIO("\n".join(lines[header_idx:])))
    df = df.rename(columns=lambda c: c.strip())
    if "Ticker" not in df.columns:
        raise ValueError("No Ticker column found")
    df = df[df["Ticker"].notna() & (df["Ticker"] != "-") & (df["Ticker"] != "")]
    col_map = {}
    for col in df.columns:
        cl = col.lower()
        if "sector" in cl:
            col_map[col] = "Sector"
        elif "market value" in cl:
            col_map[col] = "Market Value"
        elif "name" in cl and col != "Ticker":
            col_map[col] = "Name"
    df = df.rename(columns=col_map)
    for c in ["Name", "Sector", "Market Value"]:
        if c not in df.columns:
            df[c] = np.nan
    df["Ticker"] = df["Ticker"].str.upper().str.strip()
    # Filter equity rows only (exclude cash, bond lines)
    if "Asset Class" in df.columns:
        df = df[df["Asset Class"].str.strip().str.lower() == "equity"]
    return df[["Ticker", "Name", "Sector", "Market Value"]].reset_index(drop=True)


def _load_local_ishares(fund_ticker: str) -> pd.DataFrame:
    """Load the bundled local iShares CSV as a fallback."""
    local_path = LOCAL_FALLBACK.get(fund_ticker)
    if local_path and local_path.exists():
        logger.info("Using local fallback CSV: %s", local_path)
        text = local_path.read_text(encoding="utf-8", errors="replace")
        df = _parse_ishares_text(text, fund_ticker)
        logger.info("Loaded %d holdings from local file (%s)", len(df), fund_ticker)
        return df
    raise FileNotFoundError(f"No local fallback CSV found for {fund_ticker} at {local_path}")


def _download_ishares_csv(fund_ticker: str = "IWV") -> pd.DataFrame:
    """
    Download iShares ETF holdings CSV.
    Falls back to the bundled local CSV if iShares blocks the request.
    """
    urls = _get_ishares_url(fund_ticker)
    ishares_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/csv,text/plain,*/*",
        "Referer": "https://www.ishares.com/",
    }
    for url in urls:
        logger.debug("Trying iShares URL: %s", url)
        try:
            resp = requests.get(url, headers=ishares_headers, timeout=30, verify=False)
            if resp.status_code != 200:
                continue
            text = resp.text.strip()
            # iShares returns HTML when blocking — detect and skip
            if text.startswith("<!") or "<html" in text[:200].lower():
                logger.warning("iShares returned HTML (blocked) — will use local fallback")
                break
            if not text.startswith("iShares"):
                continue
            df = _parse_ishares_text(text, fund_ticker)
            logger.info("Downloaded %d holdings from iShares (%s)", len(df), fund_ticker)
            return df
        except Exception as exc:
            logger.debug("iShares URL failed: %s", exc)
            continue

    # All URLs failed or returned HTML — use local file
    logger.warning("Live iShares download unavailable — loading bundled local CSV")
    return _load_local_ishares(fund_ticker)


# ---------------------------------------------------------------------------
# S&P 500 from Wikipedia
# ---------------------------------------------------------------------------

def _download_sp500() -> pd.DataFrame:
    import ssl
    from io import StringIO
    import urllib.request

    logger.info("Fetching S&P 500 constituents from Wikipedia ...")
    # macOS often lacks updated CA certs; fetch via requests (which uses its own bundle)
    resp = requests.get(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        headers={"User-Agent": "Mozilla/5.0"},
        verify=False,
        timeout=30,
    )
    resp.raise_for_status()
    tables = pd.read_html(StringIO(resp.text))
    sp500 = tables[0][["Symbol", "Security", "GICS Sector"]].copy()
    sp500.columns = ["Ticker", "Name", "Sector"]
    sp500["Market Value"] = np.nan
    sp500["Ticker"] = sp500["Ticker"].str.upper().str.strip()
    logger.info("Loaded %d S&P 500 companies", len(sp500))
    return sp500.reset_index(drop=True)


# ---------------------------------------------------------------------------
# load_constituents
# ---------------------------------------------------------------------------

def load_constituents(
    source: str,
    custom_path=None,
    start_year: int = 2020,
    end_year: int = 2023,
) -> pd.DataFrame:
    """
    Load index constituents as a DataFrame with columns:
    Ticker, Name, Sector, Market Value

    source options:
        "russell3000"  - iShares IWV ETF holdings CSV
        "russell2000"  - iShares IWM ETF holdings CSV
        "sp500"        - Wikipedia S&P 500 table
        "custom"       - CSV at custom_path (must have Ticker, Name, Sector, Market Value)
    """
    source = source.lower().strip()

    if source == "russell3000":
        return _download_ishares_csv("IWV")

    elif source == "russell2000":
        return _download_ishares_csv("IWM")

    elif source == "sp500":
        return _download_sp500()

    elif source == "custom":
        if not custom_path:
            raise ValueError("custom_path must be provided when source='custom'")
        path = Path(custom_path)
        if not path.exists():
            raise FileNotFoundError(f"Custom CSV not found: {custom_path}")
        df = pd.read_csv(path)
        required = {"Ticker", "Name", "Sector", "Market Value"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Custom CSV missing columns: {missing}")
        df["Ticker"] = df["Ticker"].str.upper().str.strip()
        return df[["Ticker", "Name", "Sector", "Market Value"]].reset_index(drop=True)

    else:
        raise ValueError(
            f"Unknown source: {source!r}. Use 'russell3000', 'sp500', 'russell2000', or 'custom'"
        )


# ---------------------------------------------------------------------------
# Market cap via yfinance (real-time, used for P/E ratio)
# ---------------------------------------------------------------------------

_MARKET_CAP_CACHE: dict = {}


def fetch_market_caps(tickers: list) -> dict:
    """
    Fetch real market caps for a list of tickers via yfinance.
    Returns dict of {ticker: market_cap_float}.
    Results are cached so each ticker is only fetched once per session.
    """
    to_fetch = [t for t in tickers if t not in _MARKET_CAP_CACHE]
    if to_fetch:
        logger.info("Fetching market caps for %d tickers via yfinance ...", len(to_fetch))
        # yfinance batch download is fastest via download() but fast_info is more reliable
        for ticker in to_fetch:
            try:
                info = yf.Ticker(ticker).fast_info
                cap = info.get("market_cap") or info.get("marketCap")
                _MARKET_CAP_CACHE[ticker] = float(cap) if cap else None
            except Exception as exc:
                logger.debug("yfinance market cap failed for %s: %s", ticker, exc)
                _MARKET_CAP_CACHE[ticker] = None
    return {t: _MARKET_CAP_CACHE.get(t) for t in tickers}


# ---------------------------------------------------------------------------
# SEC financial data extraction
# ---------------------------------------------------------------------------

def _clean_market_value(v):
    """Parse market value string like '$1,234,567.89' -> float."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    try:
        return float(str(v).replace(",", "").replace("$", "").strip())
    except (ValueError, TypeError):
        return None


def _extract_annual_series(facts: dict, concept: str, start_year: int = None, end_year: int = None) -> list:
    """
    Extract annual (10-K, FY) data points for a US-GAAP concept.
    Tries USD first, then USD/shares, then any available unit key.
    Returns list of dicts with keys: year, value, filed.
    """
    try:
        units_dict = (
            facts.get("facts", {})
            .get("us-gaap", {})
            .get(concept, {})
            .get("units", {})
        )
    except (AttributeError, KeyError):
        return []

    if not units_dict:
        return []

    # Prefer USD, then USD/shares, then whatever is available
    unit_key = None
    for candidate in ("USD", "USD/shares"):
        if candidate in units_dict:
            unit_key = candidate
            break
    if unit_key is None:
        unit_key = next(iter(units_dict))

    entries = units_dict.get(unit_key, [])

    annual = [
        e for e in entries
        if e.get("form") == "10-K" and e.get("fp") == "FY"
        and e.get("end") and e.get("val") is not None
    ]

    # Deduplicate by fiscal year — keep most recently filed
    by_year = {}
    for e in annual:
        try:
            year = int(e["end"][:4])
            filed = e.get("filed", "0000-00-00")
            if year not in by_year or filed > by_year[year]["filed"]:
                by_year[year] = {"year": year, "value": e["val"], "filed": filed}
        except (ValueError, KeyError):
            continue

    series = sorted(by_year.values(), key=lambda x: x["year"])

    if start_year is not None or end_year is not None:
        lo = start_year or 0
        hi = end_year or 9999
        series = [e for e in series if lo <= e["year"] <= hi]

    return series


def _get_revenue_series(facts: dict, start_year: int = None, end_year: int = None) -> list:
    """
    Try multiple revenue XBRL concepts.
    Returns the concept with the most entries in the requested year range.
    """
    best = []
    for concept in REVENUE_CONCEPTS:
        series = _extract_annual_series(facts, concept, start_year, end_year)
        if len(series) > len(best):
            best = series
    return best


def _predict_eps(eps_series: list):
    """Fit a linear regression on EPS values and predict the next year."""
    if len(eps_series) < 2:
        return None
    x = np.arange(len(eps_series)).reshape(-1, 1)
    y = np.array(eps_series, dtype=float)
    model = LinearRegression().fit(x, y)
    return float(model.predict([[len(eps_series)]])[0])


def _revenue_growth_pct(revenue_series: list):
    """Mean year-over-year revenue growth percentage."""
    if len(revenue_series) < 2:
        return None
    yoy = [
        (revenue_series[i] - revenue_series[i - 1]) / abs(revenue_series[i - 1]) * 100
        for i in range(1, len(revenue_series))
        if revenue_series[i - 1] != 0
    ]
    return float(np.mean(yoy)) if yoy else None


def analyze_ticker(
    ticker: str,
    name: str,
    sector: str,
    market_value_raw,
    start_year: int,
    end_year: int,
):
    """
    Fetch SEC EDGAR company facts and compute financial metrics.
    Returns a result dict or None if insufficient data.
    """
    cik = get_cik(ticker)
    if not cik:
        logger.debug("No CIK found for %s — skipping", ticker)
        return None

    url = COMPANY_FACTS_URL.format(cik=cik)
    time.sleep(REQUEST_DELAY)
    resp = _get_with_retry(url, HEADERS)
    if resp.status_code != 200:
        logger.debug("HTTP %d fetching facts for %s (CIK %s)", resp.status_code, ticker, cik)
        return None

    try:
        facts = resp.json()
    except Exception:
        logger.debug("JSON parse error for %s", ticker)
        return None

    # Revenue — picks the concept with the most in-range entries
    rev_filtered = [e["value"] for e in _get_revenue_series(facts, start_year, end_year)]

    # Net income
    ni_filtered = [e["value"] for e in _extract_annual_series(facts, "NetIncomeLoss", start_year, end_year)]

    # EPS — stored as USD/shares, handled automatically by _extract_annual_series
    eps_filtered = [e["value"] for e in _extract_annual_series(facts, "EarningsPerShareBasic", start_year, end_year)]

    filings_found = len(rev_filtered) + len(ni_filtered) + len(eps_filtered)
    if filings_found == 0:
        logger.debug("No financial data in range %d-%d for %s", start_year, end_year, ticker)
        return None

    avg_revenue = float(np.mean(rev_filtered)) if rev_filtered else None
    avg_net_income = float(np.mean(ni_filtered)) if ni_filtered else None
    rev_growth = _revenue_growth_pct(rev_filtered)
    predicted_eps = _predict_eps(eps_filtered)

    # P/E ratio: use real market cap from yfinance (accurate for all sources).
    # Fall back to the index-supplied market value only if yfinance returns nothing.
    real_cap = fetch_market_caps([ticker]).get(ticker)
    if real_cap is None:
        real_cap = _clean_market_value(market_value_raw)
    pe_ratio = None
    if real_cap and ni_filtered and ni_filtered[-1] and ni_filtered[-1] != 0:
        pe_ratio = round(real_cap / ni_filtered[-1], 2)

    return {
        "ticker": ticker,
        "name": name,
        "sector": sector,
        "predicted_eps": predicted_eps,
        "avg_revenue": avg_revenue,
        "avg_net_income": avg_net_income,
        "revenue_growth_pct": rev_growth,
        "pe_ratio": pe_ratio,
        "filings_found": filings_found,
        "run_timestamp": datetime.now().isoformat(timespec="seconds"),
    }


# ---------------------------------------------------------------------------
# Checkpointing
# ---------------------------------------------------------------------------

RESULT_COLUMNS = [
    "ticker", "name", "sector", "predicted_eps",
    "avg_revenue", "avg_net_income", "revenue_growth_pct",
    "pe_ratio", "filings_found", "run_timestamp",
]


def _load_checkpoint():
    """Load existing checkpoint file. Returns (df, set_of_done_tickers)."""
    if Path(CHECKPOINT_FILE).exists():
        try:
            df = pd.read_csv(CHECKPOINT_FILE)
            done = set(df["ticker"].str.upper().tolist())
            logger.info("Resuming from checkpoint: %d tickers already processed", len(done))
            return df, done
        except Exception as exc:
            logger.warning("Could not read checkpoint: %s — starting fresh", exc)
    return pd.DataFrame(columns=RESULT_COLUMNS), set()


def _save_checkpoint(results: list) -> None:
    pd.DataFrame(results, columns=RESULT_COLUMNS).to_csv(CHECKPOINT_FILE, index=False)
    logger.info("Checkpoint saved (%d results)", len(results))


# ---------------------------------------------------------------------------
# run_analysis
# ---------------------------------------------------------------------------

def run_analysis(
    constituents_df: pd.DataFrame,
    start_year: int = 2020,
    end_year: int = 2023,
    max_companies=None,
    progress_callback=None,
) -> pd.DataFrame:
    """
    Run SEC EDGAR analysis on a constituents DataFrame.

    Parameters
    ----------
    constituents_df   : DataFrame with columns Ticker, Name, Sector, Market Value
    start_year        : first fiscal year to include
    end_year          : last fiscal year to include
    max_companies     : cap number of tickers to analyze (None = all)
    progress_callback : optional callable(current: int, total: int, ticker: str)

    Returns
    -------
    DataFrame with RESULT_COLUMNS
    """
    # Ensure ticker map is loaded once upfront
    _load_ticker_cik_map()

    df = constituents_df.copy()
    if max_companies:
        df = df.head(int(max_companies))

    checkpoint_df, done_tickers = _load_checkpoint()
    results: list = checkpoint_df.to_dict("records")

    total = len(df)
    processed = 0

    for _, row in df.iterrows():
        ticker = str(row.get("Ticker", "")).upper().strip()
        if not ticker:
            continue

        processed += 1
        if ticker in done_tickers:
            if progress_callback:
                progress_callback(processed, total, ticker)
            continue

        name = str(row.get("Name", ticker))
        sector = str(row.get("Sector", "Unknown"))
        market_value_raw = row.get("Market Value")

        logger.info("[%d/%d] Analyzing %s ...", processed, total, ticker)
        if progress_callback:
            progress_callback(processed, total, ticker)

        result = analyze_ticker(ticker, name, sector, market_value_raw, start_year, end_year)
        if result:
            results.append(result)
            done_tickers.add(ticker)

        # Checkpoint every N companies
        if processed % CHECKPOINT_INTERVAL == 0 and results:
            _save_checkpoint(results)

    # Final save
    if results:
        _save_checkpoint(results)

    result_df = pd.DataFrame(results, columns=RESULT_COLUMNS)
    logger.info(
        "Analysis complete: %d companies with data out of %d processed",
        len(result_df), processed,
    )
    return result_df


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="SEC EDGAR Equity Analyzer")
    parser.add_argument(
        "--source",
        default="russell3000",
        choices=["russell3000", "sp500", "russell2000", "custom"],
        help="Index to analyze",
    )
    parser.add_argument(
        "--custom-path", default=None,
        help="Path to custom CSV (when source=custom)",
    )
    parser.add_argument("--start-year", type=int, default=2020)
    parser.add_argument("--end-year", type=int, default=2023)
    parser.add_argument("--max-companies", type=int, default=None)
    parser.add_argument("--output", default="results.csv", help="Output CSV path")
    args = parser.parse_args()

    print(f"Loading constituents: {args.source}")
    try:
        constituents = load_constituents(
            source=args.source,
            custom_path=args.custom_path,
            start_year=args.start_year,
            end_year=args.end_year,
        )
    except Exception as exc:
        print(f"ERROR loading constituents: {exc}")
        return

    print(f"Analyzing {len(constituents)} companies ({args.start_year}-{args.end_year}) ...")
    results = run_analysis(
        constituents_df=constituents,
        start_year=args.start_year,
        end_year=args.end_year,
        max_companies=args.max_companies,
    )

    if results.empty:
        print("No results found.")
        return

    results_sorted = results.sort_values("predicted_eps", ascending=False)
    results_sorted.to_csv(args.output, index=False)
    print(f"\nSaved {len(results_sorted)} results to {args.output}")

    print("\nTop 10 Companies by Predicted EPS:")
    print("-" * 60)
    top10 = results_sorted.head(10)[
        ["ticker", "name", "sector", "predicted_eps", "avg_revenue", "pe_ratio"]
    ]
    for _, r in top10.iterrows():
        eps = f"{r['predicted_eps']:.2f}" if pd.notna(r["predicted_eps"]) else "N/A"
        rev = f"${r['avg_revenue']/1e9:.1f}B" if pd.notna(r["avg_revenue"]) else "N/A"
        pe = f"{r['pe_ratio']:.1f}x" if pd.notna(r["pe_ratio"]) else "N/A"
        print(f"  {r['ticker']:<8} {r['name']:<35} EPS={eps:>8}  Rev={rev:>10}  PE={pe}")


if __name__ == "__main__":
    main()
