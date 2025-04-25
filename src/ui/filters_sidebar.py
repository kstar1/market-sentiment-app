# src/ui/filters_sidebar.py

import streamlit as st

def render_sidebar_filters(option_type: str, df):
    """
    Renders grouped sidebar filters for a given options type (PUT or CALL).

    Args:
        option_type (str): Either 'PUT' or 'CALL' to differentiate keys and labels.
        df (pd.DataFrame): The option chain DataFrame to base filter ranges on.

    Returns:
        dict: Dictionary with selected filter values for strike range, volume,
              implied volatility, and open interest.
    """
    with st.sidebar.expander(f"{option_type} Filters", expanded=False):

        st.markdown("#### Price Filters")
        strike_min = float(df["strike"].min())
        strike_max = float(df["strike"].max())
        selected_strike = st.slider(
            "Strike Price Range",
            min_value=strike_min,
            max_value=strike_max,
            value=(strike_min, strike_max),
            step=1.0,
            key=f"strike_slider_{option_type}"
        )

        volume_max = int(df["volume"].max())
        if volume_max == 0:
            st.info("All options have zero volume.")
            volume_threshold = 0
        else:
            volume_threshold = st.slider(
                "Minimum Volume",
                min_value=0,
                max_value=volume_max,
                value=0,
                step=10,
                key=f"vol_slider_{option_type}"
            )

        st.markdown("#### Sentiment Filters")
        iv_min = float(df["impliedVolatility"].min())
        iv_max = float(df["impliedVolatility"].max())
        selected_iv = st.slider(
            "Implied Volatility Range",
            min_value=iv_min,
            max_value=iv_max,
            value=(iv_min, iv_max),
            step=0.01,
            key=f"iv_slider_{option_type}"
        )

        oi_max = int(df["openInterest"].max())
        if oi_max == 0:
            st.info("All options have zero open interest.")
            oi_threshold = 0
        else:
            oi_threshold = st.slider(
                "Minimum Open Interest",
                min_value=0,
                max_value=oi_max,
                value=0,
                step=10,
                key=f"oi_slider_{option_type}"
            )

        return {
            "strike_range": selected_strike,
            "volume_min": volume_threshold,
            "iv_range": selected_iv,
            "open_interest_min": oi_threshold
        }
