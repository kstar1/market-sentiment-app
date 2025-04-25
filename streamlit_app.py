# streamlit_app.py

import sys
import os
import streamlit as st
import pandas as pd
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.data.option_loader import get_expirations, get_option_chain, get_stock_info
from src.ui.filters_sidebar import render_sidebar_filters
from src.insights.llm_interpreter import get_llm_insight
from src.ui.summary_card import render_llm_summary_card
from src.ui.ticker_details import render_ticker_details
from src.insights.llm_task_engine import run_insight_tasks
from src.utils.helpers import render_task_output

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
    st.markdown("## 📊 Strategic GPT Insights")
    if st.button("🔍 Generate Multi-Insight Summary"):
        multi_insights = run_insight_tasks(
            ticker=ticker,
            expiration=selected_expiration,
            calls_df=filtered_calls,
            puts_df=filtered_puts,
            stock_info=stock_df
        )
        st.session_state.multi_insights = multi_insights
        st.success("✅ Insights generated successfully!")

    if "multi_insights" in st.session_state:
        INTRO_COPY = {
            "Sentiment Pulse": "Trader sentiment reveals whether the market is leaning bullish, bearish, or uncertain based on volume, OI, and volatility activity.",
            "Support/Resistance": "These are levels where large option positions exist, often acting as technical barriers to price movement.",
            "IV Skew Analysis": "Implied volatility skew shows how traders price in risk for upside vs downside. It gives clues about market expectations.",
            "Unusual Flow": "Detects abnormal spikes in volume or OI, potentially showing large trades, hedging, or directional bets.",
            "Risk Factors": "Highlights structural risks like time decay, volatility crashes, and exposure concentration within the option chain.",
            "Strategist Summary": "This is a high-level narrative summarizing what a professional strategist might infer from this options data."
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
