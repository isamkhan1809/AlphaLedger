# app.py — Streamlit UI for SEC Filing Analyzer
# Run with: streamlit run app.py

import io
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from agent import load_constituents, run_analysis, RESULT_COLUMNS

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="SEC Filing Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
if "results_df" not in st.session_state:
    st.session_state.results_df = None
if "run_meta" not in st.session_state:
    st.session_state.run_meta = {}

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("SEC Filing Analyzer")
    st.markdown("---")

    source_label = st.selectbox(
        "Data Source",
        options=["Russell 3000", "S&P 500", "Russell 2000", "Custom CSV"],
    )
    source_map = {
        "Russell 3000": "russell3000",
        "S&P 500": "sp500",
        "Russell 2000": "russell2000",
        "Custom CSV": "custom",
    }
    source_key = source_map[source_label]

    custom_file = None
    custom_tmp_path = None
    if source_key == "custom":
        st.markdown("**Upload your CSV**")
        st.caption("CSV must have columns: Ticker, Name, Sector, Market Value")
        custom_file = st.file_uploader("Choose CSV file", type=["csv"])

    st.markdown("---")
    st.subheader("Analysis Period")
    from datetime import datetime
    current_year = datetime.now().year

    col_y1, col_y2 = st.columns(2)
    with col_y1:
        start_year = st.number_input("Start Year", min_value=2000, max_value=current_year, value=2020, step=1)
    with col_y2:
        end_year = st.number_input("End Year", min_value=2000, max_value=current_year, value=2023, step=1)

    if end_year < start_year:
        st.error("End Year must be >= Start Year")

    st.markdown("---")
    st.subheader("Companies to Analyze")
    max_companies = st.slider(
        "Max companies",
        min_value=5,
        max_value=500,
        value=25,
        step=5,
    )
    st.warning("Full index = slower + more SEC requests")

    st.markdown("---")
    run_button = st.button("Run Analysis", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Main area header
# ---------------------------------------------------------------------------
st.title("SEC Filing Analyzer")
st.markdown(
    "Analyze financial metrics (EPS, revenue, net income) from SEC EDGAR 10-K filings "
    "for major equity indices. Data sourced directly from the SEC — no API key required."
)

# ---------------------------------------------------------------------------
# Run analysis
# ---------------------------------------------------------------------------
if run_button:
    # Validate inputs
    if source_key == "custom" and custom_file is None:
        st.error("Please upload a CSV file before running the analysis.")
        st.stop()

    if end_year < start_year:
        st.error("Please fix the year range before running.")
        st.stop()

    # Save uploaded file to a temp location if custom
    if source_key == "custom" and custom_file is not None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        tmp.write(custom_file.read())
        tmp.flush()
        custom_tmp_path = tmp.name

    # Clear previous results
    st.session_state.results_df = None

    # Progress UI
    progress_bar = st.progress(0.0, text="Starting analysis ...")
    status_text = st.empty()

    def progress_callback(current, total, ticker):
        pct = current / total if total > 0 else 0
        progress_bar.progress(pct, text=f"Analyzing {ticker} ({current}/{total}) ...")
        status_text.info(f"Current ticker: **{ticker}**  ({current} of {total})")

    # Load constituents
    try:
        with st.spinner(f"Downloading {source_label} constituents ..."):
            constituents_df = load_constituents(
                source=source_key,
                custom_path=custom_tmp_path,
                start_year=int(start_year),
                end_year=int(end_year),
            )
    except Exception as exc:
        st.error(f"Failed to load constituents: {exc}")
        st.stop()

    st.success(f"Loaded {len(constituents_df)} companies from {source_label}.")

    # Run analysis
    try:
        results_df = run_analysis(
            constituents_df=constituents_df,
            start_year=int(start_year),
            end_year=int(end_year),
            max_companies=max_companies,
            progress_callback=progress_callback,
        )
    except Exception as exc:
        st.error(f"Analysis failed: {exc}")
        st.stop()

    progress_bar.progress(1.0, text="Done!")
    status_text.empty()

    if results_df.empty:
        st.warning(
            "No financial data found for any company in the selected range. "
            "Try expanding the analysis period or choosing a different index."
        )
        st.stop()

    st.session_state.results_df = results_df
    st.session_state.run_meta = {
        "source": source_label,
        "start_year": start_year,
        "end_year": end_year,
        "max_companies": max_companies,
        "total_companies": len(results_df),
    }

# ---------------------------------------------------------------------------
# Display results
# ---------------------------------------------------------------------------
if st.session_state.results_df is not None:
    df = st.session_state.results_df.copy()
    meta = st.session_state.run_meta

    # ---------- Metric cards ----------
    companies_with_data = int(df["predicted_eps"].notna().sum())
    avg_predicted_eps = df["predicted_eps"].mean()

    sector_eps = (
        df.groupby("sector")["predicted_eps"]
        .mean()
        .sort_values(ascending=False)
    )
    top_sector = sector_eps.index[0] if not sector_eps.empty else "N/A"

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Companies", meta.get("total_companies", len(df)))
    col2.metric(
        "Avg Predicted EPS",
        f"${avg_predicted_eps:.2f}" if pd.notna(avg_predicted_eps) else "N/A",
    )
    col3.metric("Top Sector (EPS)", top_sector)
    col4.metric("Companies with Data", companies_with_data)

    st.markdown("---")

    # ---------- Tabs ----------
    tab_rankings, tab_sector, tab_raw = st.tabs(["Rankings", "Sector View", "Raw Data"])

    # --- Rankings tab ---
    with tab_rankings:
        st.subheader("Top Companies by Predicted EPS")
        top_n = st.slider("Show top N companies", min_value=5, max_value=50, value=20, step=5)

        df_sorted = df.dropna(subset=["predicted_eps"]).sort_values(
            "predicted_eps", ascending=False
        )
        top_df = df_sorted.head(top_n).copy()

        if top_df.empty:
            st.info("No companies with predicted EPS data available.")
        else:
            fig = px.bar(
                top_df,
                x="ticker",
                y="predicted_eps",
                color="sector",
                hover_data=["name", "avg_revenue", "avg_net_income", "pe_ratio"],
                title=f"Top {top_n} Companies — Predicted EPS",
                labels={"predicted_eps": "Predicted EPS ($)", "ticker": "Ticker"},
                template="plotly_white",
            )
            fig.update_layout(xaxis_tickangle=-45, height=500)
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Rankings Table")
            display_cols = [
                "ticker", "name", "sector", "predicted_eps",
                "avg_revenue", "avg_net_income", "revenue_growth_pct", "pe_ratio",
            ]
            st.dataframe(
                top_df[display_cols].reset_index(drop=True),
                use_container_width=True,
                column_config={
                    "ticker": st.column_config.TextColumn("Ticker"),
                    "name": st.column_config.TextColumn("Company"),
                    "sector": st.column_config.TextColumn("Sector"),
                    "predicted_eps": st.column_config.NumberColumn("Predicted EPS", format="$%.2f"),
                    "avg_revenue": st.column_config.NumberColumn("Avg Revenue", format="$%.0f"),
                    "avg_net_income": st.column_config.NumberColumn("Avg Net Income", format="$%.0f"),
                    "revenue_growth_pct": st.column_config.NumberColumn("Rev Growth %", format="%.1f%%"),
                    "pe_ratio": st.column_config.NumberColumn("P/E Ratio", format="%.1f"),
                },
            )

    # --- Sector View tab ---
    with tab_sector:
        st.subheader("Predicted EPS Distribution by Sector")

        df_sector = df.dropna(subset=["predicted_eps", "sector"])
        if df_sector.empty:
            st.info("No sector data available.")
        else:
            fig_box = px.box(
                df_sector,
                x="sector",
                y="predicted_eps",
                color="sector",
                title="Predicted EPS by Sector",
                labels={"predicted_eps": "Predicted EPS ($)", "sector": "Sector"},
                template="plotly_white",
            )
            fig_box.update_layout(
                xaxis_tickangle=-30,
                height=500,
                showlegend=False,
            )
            st.plotly_chart(fig_box, use_container_width=True)

            st.subheader("Sector Summary")
            sector_summary = (
                df_sector.groupby("sector")
                .agg(
                    avg_predicted_eps=("predicted_eps", "mean"),
                    avg_revenue=("avg_revenue", "mean"),
                    company_count=("ticker", "count"),
                )
                .sort_values("avg_predicted_eps", ascending=False)
                .reset_index()
            )
            st.dataframe(
                sector_summary,
                use_container_width=True,
                column_config={
                    "sector": st.column_config.TextColumn("Sector"),
                    "avg_predicted_eps": st.column_config.NumberColumn(
                        "Avg Predicted EPS", format="$%.2f"
                    ),
                    "avg_revenue": st.column_config.NumberColumn(
                        "Avg Revenue", format="$%.0f"
                    ),
                    "company_count": st.column_config.NumberColumn("# Companies"),
                },
            )

    # --- Raw Data tab ---
    with tab_raw:
        st.subheader("Full Results")
        st.dataframe(df, use_container_width=True)

        # Download button
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="Download CSV",
            data=csv_buffer.getvalue(),
            file_name=f"sec_analysis_{meta.get('source','results').replace(' ','_').lower()}.csv",
            mime="text/csv",
        )

else:
    # Placeholder before any run
    st.info(
        "Configure your analysis in the sidebar and click **Run Analysis** to get started. "
        "Data is fetched live from SEC EDGAR — the first run may take a few minutes."
    )
    with st.expander("How it works"):
        st.markdown(
            """
            1. **Constituents** are downloaded from iShares (Russell 3000 / 2000) or Wikipedia (S&P 500).
            2. Each company's CIK is looked up via the [SEC EDGAR ticker map](https://www.sec.gov/files/company_tickers.json).
            3. Annual 10-K filings are retrieved from the [XBRL company facts API](https://data.sec.gov/api/xbrl/companyfacts/).
            4. Financial metrics are extracted, deduplicated by fiscal year, and aggregated.
            5. A linear regression on historical EPS produces the **Predicted EPS** ranking.

            **Rate limiting:** 0.15s delay between SEC requests to comply with fair-use policy.
            Progress is checkpointed every 25 companies so interrupted runs can resume.
            """
        )
