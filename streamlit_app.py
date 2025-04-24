# streamlit_app.py

import sys
import os
import streamlit as st
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.data.option_loader import get_expirations, get_option_chain, get_stock_info
from src.ui.filters_sidebar import render_sidebar_filters
from src.insights.llm_interpreter import get_llm_insight

st.set_page_config(page_title="Market Sentiment Explorer", layout="wide")
st.title("Market Sentiment Explorer")
st.markdown("Explore PUT/CALL option chains to understand market expectations.")

# --- Ticker Input ---
ticker = st.text_input("Enter Ticker Symbol", value="AAPL").upper()

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

        def display_fields(title, fields):
            st.markdown(f"### {title}")
            for label, value in fields:
                st.markdown(f"- {label}: {value}")
            st.markdown("")

        info = stock_df["full_info"]

        # Profile
        profile = [
            ("**Long Name**", info.get("longName", "N/A")),
            ("**Sector**", info.get("sector", "N/A")),
            ("**Industry**", info.get("industry", "N/A")),
        ]

        # Valuation
        valuation = [
            ("**Market Cap**", f"${info.get('marketCap'):,}" if info.get("marketCap") else "N/A"),
            ("**PE (Trailing)**", f"{info.get('trailingPE'):.2f}" if info.get("trailingPE") else "N/A"),
            ("**PE (Forward)**", f"{info.get('forwardPE'):.2f}" if info.get("forwardPE") else "N/A"),
            ("**Dividend Yield**", f"{info.get('dividendYield'):.2%}" if info.get("dividendYield") else "N/A"),
        ]

        # Performance
        performance = [
            ("**EPS (Trailing 12M)**", f"${info.get('trailingEps'):.2f}" if info.get("trailingEps") else "N/A"),
            ("**Revenue Growth (YoY)**", f"{info.get('revenueGrowth'):.2%}" if info.get("revenueGrowth") else "N/A"),
            ("**Earnings Date**", str(info.get("earningsDate")) if info.get("earningsDate") else "N/A"),
            ("**Filings**", f"[SEC Filings]({info.get('secFilings', '#')})" if info.get("secFilings") else "N/A"),
        ]

        display_fields("🔍 Profile", profile)
        display_fields("💸 Valuation", valuation)
        display_fields("📈 Performance", performance)

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

    # --- AI INSIGHTS BLOCK (requires both filtered sets) ---
    if not filtered_calls.empty and not filtered_puts.empty:
        with st.expander("🤖 AI Insights"):
            if st.button("🧠 Summarize Market Sentiment with AI", key="ai_summary_both"):
                question = "Summarize trader sentiment and IV skew from this option chain."
                summary, loops_used = get_llm_insight(
                    ticker, selected_expiration, filtered_calls, filtered_puts, stock_df, question
                )
                st.markdown(f"✅ Completed in {loops_used} LLM interaction{'s' if loops_used > 1 else ''}")
                st.markdown("#### AI Insight:")
                st.markdown(summary)

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
