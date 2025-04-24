# streamlit_app.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import sys, os

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

    # Fetch option chain
    puts_df, calls_df = get_option_chain(ticker, selected_expiration)
    stock_df = get_stock_info(ticker)

    # --- STOCK SNAPSHOT ---
    st.markdown("#### Stock Snapshot <span style='font-size: 0.8em; font-style: italic;'>(from Yahoo Finance)</span>", unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns([1, 1, 1, 3])

    col1.metric("Current Price", f"${stock_df['current_price']}")
    col2.metric("Beta", stock_df['beta'])
    col3.metric("Analyst Rec.", stock_df['recommendation'])
    col4.markdown(f"[🌐 Visit Website]({stock_df['website']})")

    with st.expander("More Ticker Details"):
        info = stock_df["full_info"]
        st.write({
            "Long Name": info.get("longName"),
            "Sector": info.get("sector"),
            "Industry": info.get("industry"),
            "Market Cap": info.get("marketCap"),
            "PE (Trailing)": info.get("trailingPE"),
            "PE (Forward)": info.get("forwardPE"),
            "Dividend Yield": info.get("dividendYield"),
            "Earnings Date": info.get("earningsDate"),
        })

    # Reset Filters button
    if st.sidebar.button("🔄 Reset Filters"):
        st.experimental_rerun()

    # --- TABS ---
    tab1, tab2 = st.tabs(["▲ CALL Options", "▼ PUT Options"])

    with tab1:
        if not calls_df.empty:
            filters = render_sidebar_filters("CALL", calls_df)
            filtered_calls = calls_df[
                (calls_df["strike"] >= filters["strike_range"][0]) &
                (calls_df["strike"] <= filters["strike_range"][1]) &
                (calls_df["volume"] >= filters["volume_min"]) &
                (calls_df["impliedVolatility"] >= filters["iv_range"][0]) &
                (calls_df["impliedVolatility"] <= filters["iv_range"][1]) &
                (calls_df["openInterest"] >= filters["open_interest_min"])
            ]

            st.markdown("#### Summary Stats")
            col1, col2, col3, col4 = st.columns(4)

            col1.metric("Avg Volume", f"{filtered_calls['volume'].mean():,.0f}")
            col2.metric("Max IV", f"{filtered_calls['impliedVolatility'].max():.2f}")
            col3.metric("Open Interest (Total)", f"{filtered_calls['openInterest'].sum():,}")
            col4.metric("Current Price", f"${stock_df['current_price']:.2f}")

            st.dataframe(filtered_calls, use_container_width=True)
        else:
            st.warning("No CALL options available.")

        # Show AI insights if user clicks a prompt button
        with st.expander("🤖 AI Insights"):
            if st.button("🧠 Analyze CALL Sentiment (AI)", key="ai_summary_CALL"):
                question = "Summarize trader sentiment and IV skew from this option chain."
                summary, loops_used = get_llm_insight(ticker, selected_expiration, filtered_calls, filtered_calls, question)

                st.markdown(f"✅ Completed in {loops_used} LLM interaction{'s' if loops_used > 1 else ''}")
                st.markdown("#### AI Insight:")
                st.markdown(summary)

    with tab2:
        if not puts_df.empty:
            filters = render_sidebar_filters("PUT", puts_df)
            filtered_puts = puts_df[
                (puts_df["strike"] >= filters["strike_range"][0]) &
                (puts_df["strike"] <= filters["strike_range"][1]) &
                (puts_df["volume"] >= filters["volume_min"]) &
                (puts_df["impliedVolatility"] >= filters["iv_range"][0]) &
                (puts_df["impliedVolatility"] <= filters["iv_range"][1]) &
                (puts_df["openInterest"] >= filters["open_interest_min"])
            ]

            st.markdown("#### Summary Stats")
            col1, col2, col3, col4 = st.columns(4)

            col1.metric("Avg Volume", f"{filtered_puts['volume'].mean():,.0f}")
            col2.metric("Max IV", f"{filtered_puts['impliedVolatility'].max():.2f}")
            col3.metric("Open Interest (Total)", f"{filtered_puts['openInterest'].sum():,}")
            col4.metric("Current Price", f"${stock_df['current_price']:.2f}")

            st.dataframe(filtered_puts, use_container_width=True)
        else:
            st.warning("No PUT options available.")

        # Show AI insights if user clicks a prompt button
        with st.expander("🤖 AI Insights"):
            if st.button("🧠 Analyze PUT Sentiment (AI)", key="ai_summary_PUT"):
                question = "Summarize trader sentiment and IV skew from this option chain."
                summary, loops_used = get_llm_insight(ticker, selected_expiration, filtered_calls, filtered_puts, question)

                st.markdown(f"✅ Completed in {loops_used} LLM interaction{'s' if loops_used > 1 else ''}")
                st.markdown("#### AI Insight:")
                st.markdown(summary)