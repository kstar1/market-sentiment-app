# streamlit_app.py

import sys
import os
import streamlit as st
import pandas as pd
import re
import plotly.express as px

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.data.option_loader import get_expirations, get_option_chain, get_stock_info, get_stock_history
from src.ui.filters_sidebar import render_sidebar_filters
from src.insights.llm_interpreter import get_llm_insight
from src.ui.summary_card import render_llm_summary_card
from src.ui.ticker_details import render_ticker_details
from src.insights.llm_task_engine import run_insight_tasks
from src.utils.helpers import render_task_output
from src.data.option_loader import get_stock_history
from src.ui.charts import (
    render_gamma_clustering_chart,
    render_unusual_flow_chart,
    render_volatility_premium_chart,
    render_trend_confirmation_chart,
    render_beta_risk_profile_chart,
    render_sentiment_index_chart
)


st.set_page_config(page_title="Market Sentiment Explorer", layout="wide")
st.title("Market Sentiment Explorer")
st.markdown("Explore PUT/CALL option chains to understand market expectations.")

# --- Ticker Input ---
ticker = st.text_input("Enter Ticker Symbol", value="TSLA").upper()

if ticker:
    expirations = get_expirations(ticker)
    if not expirations:
        st.error("No options data found for this ticker.")
        st.stop()

    selected_expiration = st.selectbox("Select Expiration Date", expirations)

    # Fetch data
    puts_df, calls_df = get_option_chain(ticker, selected_expiration)
    stock_df = get_stock_info(ticker)
    stock_history_df = get_stock_history(ticker, period="180d")
    if stock_history_df is None or stock_history_df.empty:
        print(f"⚠️ Warning: No stock history loaded for {ticker}")
    else:
        print(f"✅ Stock history loaded for {ticker}: {len(stock_history_df)} days, from {stock_history_df['Date'].min().date()} to {stock_history_df['Date'].max().date()}")

    # --- Check for critical data completeness ---
    critical_data_missing = False

    if stock_history_df is None or stock_history_df.empty:
        critical_data_missing = True
    elif len(stock_history_df) < 100:  # sanity threshold for 90-day realized vol
        critical_data_missing = True

    if critical_data_missing:
        st.warning("⚠️ Stock history data may be insufficient to calculate 90-day realized volatility. Some insights might be incomplete.")

    # --- STOCK SNAPSHOT ---
    st.markdown("#### Stock Snapshot <span style='font-size: 0.8em; font-style: italic;'>(from Yahoo Finance)</span>", unsafe_allow_html=True)

    info = stock_df["full_info"]
    raw_rec = stock_df["recommendation"]
    pretty_rec = raw_rec.replace("_", " ").title() if isinstance(raw_rec, str) else "N/A"

    col1, col2, col3, col4 = st.columns([1, 1, 1, 3])
    with col1:
        st.markdown("**Current Price**")
        st.markdown(f"<span style='font-size: 1.5em;'>${stock_df['current_price']}</span>", unsafe_allow_html=True)

    with col2:
        st.markdown("**Beta**")
        st.markdown(f"<span style='font-size: 1.5em;'>{stock_df['beta']}</span>", unsafe_allow_html=True)

    with col3:
        st.markdown("**Analyst Rec.**")
        st.markdown(f"<span style='font-size: 1.5em;'>{pretty_rec}</span>", unsafe_allow_html=True)

    with col4:
        st.markdown("[🌐 Visit Website](" + stock_df.get("website", "#") + ")")

    # --- EXPANDED DETAILS ---
    with st.expander("📊 More Ticker Details"):
        render_ticker_details(stock_df["full_info"])


    # Reset Filters
    if st.sidebar.button("🔄 Reset Filters"):
        st.experimental_rerun()

    # --- FILTERED OPTIONS (used in both tabs and LLM) ---
    filtered_calls, filtered_puts = pd.DataFrame(), pd.DataFrame()
    if not calls_df.empty:
        filters_call = render_sidebar_filters("CALL", calls_df)
        filtered_calls = calls_df[
            (calls_df["strike"] >= filters_call["strike_range"][0]) &
            (calls_df["strike"] <= filters_call["strike_range"][1]) &
            (calls_df["volume"] >= filters_call["volume_min"]) &
            (calls_df["impliedVolatility"] >= filters_call["iv_range"][0]) &
            (calls_df["impliedVolatility"] <= filters_call["iv_range"][1]) &
            (calls_df["openInterest"] >= filters_call["open_interest_min"])
        ]

    if not puts_df.empty:
        filters_put = render_sidebar_filters("PUT", puts_df)
        filtered_puts = puts_df[
            (puts_df["strike"] >= filters_put["strike_range"][0]) &
            (puts_df["strike"] <= filters_put["strike_range"][1]) &
            (puts_df["volume"] >= filters_put["volume_min"]) &
            (puts_df["impliedVolatility"] >= filters_put["iv_range"][0]) &
            (puts_df["impliedVolatility"] <= filters_put["iv_range"][1]) &
            (puts_df["openInterest"] >= filters_put["open_interest_min"])
        ]

    # --- MULTI-INSIGHT STRATEGIST OUTPUT ---
    with st.expander("🧠 What Does Each GPT Insight Analyze?", expanded=False):
        st.markdown("""
    ### 🧩 GPT-Based Analysis Dimensions

    The AI analyzes 6 distinct dimensions of market sentiment using options flow, price action, and volatility data:

    ---

    **1. Volatility Risk Premium Assessment**  
    - **What it measures**: Whether current option prices overestimate or underestimate future volatility.
    - **Data used**: 90-day historical realized volatility vs current ATM implied volatility.
    - **Actionable insight**: Identify overpriced or cheap options for volatility trading strategies.

    ---

    **2. Unusual Options Flow Detection**  
    - **What it detects**: Spikes in options volume, open interest, and implied volatility at specific strikes.
    - **Data used**: Strike-level options chain analysis.
    - **Actionable insight**: Spot directional bets, hedges, or volatility plays by large market participants.

    ---

    **3. Price-Volume Trend Confirmation**  
    - **What it validates**: Whether technical price trends align with options trader positioning.
    - **Data used**: EMA20/50/200 crossovers and put-call open interest ratios.
    - **Actionable insight**: Confirm the strength of bullish or bearish moves, or detect divergence.

    ---

    **4. Gamma Strike Clustering**  
    - **What it maps**: Strikes with high open interest that could "pin" the stock price due to hedging dynamics.
    - **Data used**: Strikes near current price with >10,000 contracts open interest.
    - **Actionable insight**: Understand price zones where movement could slow down or reverse.

    ---

    **5. Beta-Adjusted Risk Profile**  
    - **What it profiles**: The overall riskiness of the stock relative to market volatility.
    - **Data used**: Beta vs SPX, realized volatility, implied volatility.
    - **Actionable insight**: Categorize stocks into low, medium, or high risk to inform portfolio construction.

    ---

    **6. Synthetic Sentiment Index**  
    - **What it synthesizes**: A 0–100 sentiment score based on price momentum, options flow, volatility skew, and market correlation.
    - **Data used**: Pre-aggregated sentiment drivers.
    - **Actionable insight**: Quickly assess whether trader sentiment is bullish, neutral, or bearish.

    ---
    """)

    st.markdown("## 📊 Strategic GPT Insights")
    if st.button("🔍 Generate Multi-Insight Summary"):
        multi_insights = run_insight_tasks(
            ticker=ticker,
            expiration=selected_expiration,
            calls_df=filtered_calls,
            puts_df=filtered_puts,
            stock_info=stock_df,
            stock_history=stock_history_df
        )
        st.session_state.multi_insights = multi_insights
        st.success("✅ Insights generated successfully!")

    if "multi_insights" in st.session_state:
        INTRO_COPY = {
            "Volatility Risk Premium Assessment": "Analyzes the gap between realized and implied volatility to detect mispriced options.",
            "Unusual Options Flow Detection": "Detects aggressive options trades that suggest directional bets, hedging, or volatility positioning.",
            "Price-Volume Trend Confirmation": "Evaluates whether price trends are supported by options positioning or showing divergence.",
            "Gamma Strike Clustering": "Maps high open interest strikes near the stock price that could constrain or accelerate price movement.",
            "Beta-Adjusted Risk Profile": "Summarizes the stock’s risk behavior versus the market based on beta and volatility metrics.",
            "Synthetic Sentiment Index": "Synthesizes multiple indicators into a single sentiment score (bullish, neutral, bearish) to guide trading tilt."
        }

        for insight in st.session_state.multi_insights:
            task = insight.get("task", "Insight")
            with st.expander(f"📌 {task}"):
                st.markdown(f"_{INTRO_COPY.get(task, '')}_")

                show_raw = st.checkbox("🔍 Show Raw GPT Response", key=f"raw_{task}", help="Toggle to view GPT's original output")

                if "error" in insight:
                    st.error(insight["error"])
                    st.code(insight.get("raw_response", ""))
                else:
                    render_task_output(insight, show_raw=show_raw)

                    if task == "Gamma Strike Clustering":
                        render_gamma_clustering_chart(insight["prepared_data"])

                    if task == "Unusual Options Flow Detection":
                        render_unusual_flow_chart(insight["prepared_data"])

                    if task == "Volatility Risk Premium Assessment":
                        render_volatility_premium_chart(insight["prepared_data"])

                    if task == "Price-Volume Trend Confirmation":
                        render_trend_confirmation_chart(insight["prepared_data"])

                    if task == "Beta-Adjusted Risk Profile":
                        render_beta_risk_profile_chart(insight["prepared_data"])

                    if task == "Synthetic Sentiment Index":
                        render_sentiment_index_chart(insight["prepared_data"])

    # --- TABS FOR DISPLAY ---
    tab1, tab2 = st.tabs(["▲ CALL Options", "▼ PUT Options"])

    with tab1:
        if not filtered_calls.empty:
            st.markdown("#### Summary Stats")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Avg Volume", f"{filtered_calls['volume'].mean():,.0f}")
            col2.metric("Max IV", f"{filtered_calls['impliedVolatility'].max():.2f}")
            col3.metric("Open Interest (Total)", f"{filtered_calls['openInterest'].sum():,}")
            col4.metric("Current Price", f"${stock_df['current_price']:.2f}")
            st.dataframe(filtered_calls, use_container_width=True)
        else:
            st.warning("No CALL options available.")

    with tab2:
        if not filtered_puts.empty:
            st.markdown("#### Summary Stats")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Avg Volume", f"{filtered_puts['volume'].mean():,.0f}")
            col2.metric("Max IV", f"{filtered_puts['impliedVolatility'].max():.2f}")
            col3.metric("Open Interest (Total)", f"{filtered_puts['openInterest'].sum():,}")
            col4.metric("Current Price", f"${stock_df['current_price']:.2f}")
            st.dataframe(filtered_puts, use_container_width=True)
        else:
            st.warning("No PUT options available.")
