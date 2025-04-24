import streamlit as st
import pandas as pd

def render_ticker_details(info: dict):
    # Define each section
    profile_data = {
        "Long Name": info.get("longName", "N/A"),
        "Sector": info.get("sector", "N/A"),
        "Industry": info.get("industry", "N/A")
    }

    valuation_data = {
        "Market Cap": f"${info.get('marketCap'):,}" if info.get("marketCap") else "N/A",
        "PE (Trailing)": f"{info.get('trailingPE'):.2f}" if info.get("trailingPE") else "N/A",
        "PE (Forward)": f"{info.get('forwardPE'):.2f}" if info.get("forwardPE") else "N/A",
        "Dividend Yield": f"{info.get('dividendYield'):.2%}" if info.get("dividendYield") else "N/A"
    }

    performance_data = {
        "EPS (TTM)": f"${info.get('trailingEps'):.2f}" if info.get("trailingEps") else "N/A",
        "Revenue Growth": f"{info.get('revenueGrowth'):.2%}" if info.get("revenueGrowth") else "N/A",
        "Earnings Date": str(info.get("earningsDate")) if info.get("earningsDate") else "N/A",
        "SEC Filings": info.get("secFilings", "N/A")
    }

    st.markdown("### 🧾 <span style='font-size: 0.9em;'>Company Overview</span>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 🔍 Profile")
        st.dataframe(pd.DataFrame(profile_data.items(), columns=["Metric", "Value"]).set_index("Metric"))

    with col2:
        st.markdown("#### 💰 Valuation")
        st.dataframe(pd.DataFrame(valuation_data.items(), columns=["Metric", "Value"]).set_index("Metric"))

    with col3:
        st.markdown("#### 📈 Performance")
        df_perf = pd.DataFrame(performance_data.items(), columns=["Metric", "Value"])
        df_perf["Value"] = df_perf["Value"].apply(lambda x: f"[Link]({x})" if "http" in str(x) else x)
        st.dataframe(df_perf.set_index("Metric"))
