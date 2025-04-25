import streamlit as st
import pandas as pd

def render_llm_summary_card(summary: dict):
    # Stylized Heading
    st.markdown(f"### 🧠 {summary.get('summary_heading', 'GPT Insight')}")

    # Smaller subheader for styling like Stock Snapshot
    st.markdown("#### <span style='font-size: 0.9em; font-weight: bold;'>📊 Key Option Metrics</span>", unsafe_allow_html=True)

    # Safely fetch call and put summaries
    call_summary = summary.get("call_summary", {})
    put_summary = summary.get("put_summary", {})

    # Convert metrics to dataframes for side-by-side table view
    call_df = pd.DataFrame({
        "Metric": ["IV Range", "Peak Volume Strike", "Peak Volume"],
        "CALL": [
            call_summary.get("iv_range", "N/A"),
            f"${call_summary.get('peak_volume_strike', 'N/A')}" if call_summary.get("peak_volume_strike") is not None else "N/A",
            f"{call_summary.get('peak_volume', 'N/A'):,}" if isinstance(call_summary.get("peak_volume"), int) else "N/A"
        ]
    })

    put_df = pd.DataFrame({
        "Metric": ["IV Range", "Peak OI Strike", "Open Interest"],
        "PUT": [
            put_summary.get("iv_range", "N/A"),
            f"${put_summary.get('peak_oi_strike', 'N/A')}" if put_summary.get("peak_oi_strike") is not None else "N/A",
            f"{put_summary.get('peak_oi', 'N/A'):,}" if isinstance(put_summary.get("peak_oi"), int) else "N/A"
        ]
    })

    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(call_df.set_index("Metric"), use_container_width=True)
    with col2:
        st.dataframe(put_df.set_index("Metric"), use_container_width=True)

    # Insights
    st.markdown("#### <span style='font-size: 0.9em;'>💡 Insights from Option Chain</span>", unsafe_allow_html=True)
    insights = summary.get("insights", [])
    if not insights:
        st.info("No insights available from GPT.")
    else:
        for i, insight in enumerate(insights, 1):
            st.markdown(f"{i}. {insight}")
