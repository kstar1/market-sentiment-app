# streamlit_app.py

import sys
import os
import streamlit as st
import pandas as pd
import re
import plotly.express as px
import io

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

    with st.expander("🧠 What Does Each GPT Insight Analyze?", expanded=False):
        st.markdown("""
        ### 🧩 GPT-Based Analysis Dimensions

        The AI analyzes **9 distinct dimensions** of market sentiment using options flow, price action, and volatility data:

        ---

        **1. Volatility Risk Premium Assessment**  
        - **What it assesses**: Whether current option prices fairly reflect expected volatility.
        - **Data used**: 90-day realized volatility vs current ATM implied volatility.
        - **Insight**: Identify mispriced volatility opportunities.

        ---

        **2. Variance Risk Premium Analysis**  
        - **What it measures**: The gap between risk-neutral variance and realized variance.
        - **Data used**: 30-day realized variance and ATM implied variance.
        - **Insight**: Detect market overpricing or underpricing of volatility.

        ---

        **3. Unusual Options Flow Detection**  
        - **What it detects**: Spikes in volume, open interest, and IV suggesting large directional bets.
        - **Data used**: Strike-level options chain anomalies.
        - **Insight**: Uncover hidden trader sentiment shifts.

        ---

        **4. Price-Volume Trend Confirmation**  
        - **What it validates**: Whether price trends align with options trader positioning.
        - **Data used**: EMA 20/50/200 crossovers and put-call open interest ratios.
        - **Insight**: Confirm trend strength or detect divergence.

        ---

        **5. Gamma Strike Clustering**  
        - **What it maps**: High open interest strikes causing potential price pinning.
        - **Data used**: OI concentrations near current price.
        - **Insight**: Predict price constriction zones or breakout points.

        ---

        **6. Beta-Adjusted Risk Profile**  
        - **What it profiles**: Systemic risk posture relative to the market.
        - **Data used**: Beta, realized volatility, implied volatility.
        - **Insight**: Classify stocks into low, medium, or high portfolio risk.

        ---

        **7. Synthetic Sentiment Index**  
        - **What it synthesizes**: Momentum, options flow, volatility skew, and market beta correlation.
        - **Data used**: Multiple sentiment drivers combined.
        - **Insight**: Quickly assess overall market tilt (bullish, neutral, bearish).

        ---

        **8. Volatility Term Structure Analysis**  
        - **What it examines**: How implied volatility changes across different expirations.
        - **Data used**: ATM IVs across expiration dates.
        - **Insight**: Detect near-term fear or long-term complacency.

        ---

        **9. Crash Risk Premium Analysis**  
        - **What it measures**: Implied volatility skew between deep OTM PUTs and CALLs.
        - **Data used**: IV difference 20% OTM.
        - **Insight**: Identify demand for crash protection pricing.

        ---
        """)

    st.markdown("## 📊 Strategic GPT Insights")
    if st.button("🔍 Generate Multi-Insight Summary"):
        multi_insights = run_insight_tasks(
            ticker=ticker,
            expiration=selected_expiration,
            expirations=expirations,
            calls_df=filtered_calls,
            puts_df=filtered_puts,
            stock_info=stock_df,
            stock_history=stock_history_df
        )
        st.session_state.multi_insights = multi_insights
        st.success("✅ Insights generated successfully!")

    if "multi_insights" in st.session_state:
        INTRO_COPY = {
            "Volatility Risk Premium Assessment": "Assesses whether current option prices fairly reflect expected volatility, helping identify mispricing opportunities for volatility trading strategies.",
            "Variance Risk Premium Analysis": "Measures the difference between risk-neutral (implied) variance and realized variance to detect whether the market is overpricing or underpricing volatility risk.",
            "Unusual Options Flow Detection": "Identifies concentrated, unusual trading activity in specific strikes, providing early signals of potential directional bets, hedging, or event-driven speculation.",
            "Price-Volume Trend Confirmation": "Evaluates if technical price momentum is reinforced or contradicted by options trader positioning, offering a second layer of trend validation or warning signals.",
            "Gamma Strike Clustering": "Maps key strike price clusters with high open interest that could cause price pinning or sharp breakouts due to dealer hedging dynamics around gamma exposure.",
            "Beta-Adjusted Risk Profile": "Analyzes the stock’s systemic risk posture relative to broader markets using beta, realized volatility, and implied volatility to classify portfolio riskiness.",
            "Synthetic Sentiment Index": "Combines price momentum, options volume, volatility skew, and market beta correlation into a single tactical sentiment score (bullish, bearish, neutral).",
            "Volatility Term Structure Analysis": "Examines how implied volatility varies across expiration dates to detect whether markets anticipate near-term stress or exhibit stable long-term expectations.",
            "Crash Risk Premium Analysis": "Measures crash hedging demand by comparing implied volatility between deep OTM PUTs and CALLs, identifying if traders are paying extra for downside protection."
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

    if "multi_insights" in st.session_state:
        st.markdown("## 📥 Save Your Insights")

        def compile_insights_to_markdown(multi_insights):
            md = "# Market Sentiment Insights\n\n"
            for insight in multi_insights:
                task = insight.get("task", "Insight")
                md += f"## {task}\n\n"
                for key, value in insight.items():
                    if key not in ["task", "prepared_data", "raw_response"]:
                        md += f"**{key.replace('_', ' ').title()}:** {value}\n\n"
            return md

        def compile_insights_to_html(multi_insights):
            html = "<html><body><h1>Market Sentiment Insights</h1>"
            for insight in multi_insights:
                task = insight.get("task", "Insight")
                html += f"<h2>{task}</h2>"
                for key, value in insight.items():
                    if key not in ["task", "prepared_data", "raw_response"]:
                        html += f"<p><strong>{key.replace('_', ' ').title()}:</strong> {value}</p>"
            html += "</body></html>"
            return html

        markdown_content = compile_insights_to_markdown(st.session_state.multi_insights)
        html_content = compile_insights_to_html(st.session_state.multi_insights)

        st.download_button(
            label="📄 Download as Markdown",
            data=markdown_content,
            file_name=f"{ticker}_insights.md",
            mime="text/markdown"
        )

        st.download_button(
            label="🌐 Download as HTML",
            data=html_content,
            file_name=f"{ticker}_insights.html",
            mime="text/html"
        )

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
