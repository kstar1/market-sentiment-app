import streamlit as st
import pandas as pd

def render_llm_summary_card(summary: dict):
    # Stylized Heading
    st.markdown(f"### 🧠 {summary['summary_heading']}")

    # Smaller subheader for styling like Stock Snapshot
    st.markdown("#### <span style='font-size: 0.9em; font-weight: bold;'>📊 Key Option Metrics</span>", unsafe_allow_html=True)

    # Convert metrics to dataframes for side-by-side table view
    call_df = pd.DataFrame({
        "Metric": ["IV Range", "Peak Volume Strike", "Peak Volume"],
        "CALL": [
            summary["call_summary"]["iv_range"],
            f"${summary['call_summary']['peak_volume_strike']:.1f}",
            f"{summary['call_summary']['peak_volume']:,}"
        ]
    })

    put_df = pd.DataFrame({
        "Metric": ["IV Range", "Peak OI Strike", "Open Interest"],
        "PUT": [
            summary["put_summary"]["iv_range"],
            f"${summary['put_summary']['peak_oi_strike']:.1f}",
            f"{summary['put_summary']['peak_oi']:,}"
        ]
    })

    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(call_df.set_index("Metric"), use_container_width=True)
    with col2:
        st.dataframe(put_df.set_index("Metric"), use_container_width=True)

    # Insights
    st.markdown("#### <span style='font-size: 0.9em;'>💡 Insights from Option Chain</span>", unsafe_allow_html=True)
    for i, insight in enumerate(summary["insights"], 1):
        st.markdown(f"{i}. {insight}")
