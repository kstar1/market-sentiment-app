import json
import hashlib
import streamlit as st
import pandas as pd
import time
import os

from src.insights.llm_interpreter import ask_openai, construct_prompt
from typing import List, Dict
from src.utils.helpers import sanitize_insights
from streamlit import progress
from src.data.option_loader import get_stock_history
from src.insights.preprocessors import (
    prepare_volatility_risk_premium,
    prepare_unusual_options_flow,
    prepare_trend_confirmation,
    prepare_gamma_strike_clustering,
    prepare_beta_adjusted_risk_profile,
    prepare_synthetic_sentiment_index
)
from src.insights.preprocessors import (
    prepare_volatility_risk_premium_v2,
    prepare_unusual_flow_v2,
    prepare_trend_confirmation_v2,
    prepare_gamma_clustering_v2,
    prepare_beta_risk_profile_v2,
    prepare_sentiment_index_v2
)
from src.utils.helpers import safe_json_dumps

def load_task_prompts():
    file_path = os.path.join(os.path.dirname(__file__), "..", "config", "task_prompts.json")
    with open(file_path, "r") as f:
        task_prompts = json.load(f)
    return task_prompts

@st.cache_data(show_spinner="🔍 Generating multi-insight summary...")
def run_insight_tasks(
    ticker: str,
    expiration: str,
    calls_df: pd.DataFrame,
    puts_df: pd.DataFrame,
    stock_info: dict,
    stock_history: pd.DataFrame = None   # <-- add this new param
) -> List[Dict]:

    task_prompts = load_task_prompts()

    results = []
    progress_bar = st.progress(0)
    step = 1 / len(task_prompts)

    for i, (task_name, prompt) in enumerate(task_prompts.items()):
        task_preprocessors = {
            "Volatility Risk Premium Assessment": lambda: prepare_volatility_risk_premium_v2(calls_df, stock_history, expiration),
            "Unusual Options Flow Detection": lambda: prepare_unusual_flow_v2(calls_df, puts_df, expiration),
            "Price-Volume Trend Confirmation": lambda: prepare_trend_confirmation_v2(stock_history, puts_df, calls_df),
            "Gamma Strike Clustering": lambda: prepare_gamma_clustering_v2(calls_df, puts_df, stock_info["current_price"]),
            "Beta-Adjusted Risk Profile": lambda: prepare_beta_risk_profile_v2(stock_history, get_stock_history("^GSPC"), calls_df),
            "Synthetic Sentiment Index": lambda: prepare_sentiment_index_v2(stock_history, calls_df, puts_df, get_stock_history("^GSPC"))
        }

        prepared_data = task_preprocessors[task_name]()

        messages = [
            {"role": "system", "content": "You are a senior financial strategist tasked with analyzing market structure, options flow, and stock price action."},
            {"role": "user", "content": f"Here is the pre-calculated data you must use for your analysis:\n\n{json.dumps(prepared_data, indent=2, default=lambda o: o.item() if hasattr(o, 'item') else str(o))}"},
            {"role": "user", "content": f"Task Instructions:\n\n{prompt}\n\nRespond only with valid JSON as requested."}
        ]
        response = ask_openai(messages)

        try:
            raw_response = response.strip().strip("```json").strip("```").strip()
            parsed = json.loads(raw_response)
            parsed["raw_response"] = raw_response

            if "insights" in parsed:
                parsed["insights"] = sanitize_insights(parsed["insights"])

        except Exception as e:
            parsed = {
                "error": f"Failed to parse response for task: {task_name}",
                "raw_response": response
            }

        parsed["task"] = task_name
        parsed["prepared_data"] = prepared_data  # 👈 Save the numerics separately
        results.append(parsed)
        progress_bar.progress(min((i + 1) * step, 1.0))

    progress_bar.empty()
    print(f"[{task_name}] Input sent to GPT:\n{safe_json_dumps(prepared_data, indent=2)}")
    return results

