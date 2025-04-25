import json
import hashlib
import streamlit as st
from src.insights.llm_interpreter import ask_openai, construct_prompt
from typing import List, Dict
from src.utils.helpers import sanitize_insights
import pandas as pd
import time
from streamlit import progress

@st.cache_data(show_spinner="🔍 Generating multi-insight summary...")
def run_insight_tasks(
    ticker: str,
    expiration: str,
    calls_df: pd.DataFrame,
    puts_df: pd.DataFrame,
    stock_info: dict
) -> List[Dict]:

    task_prompts = {
        "Sentiment Pulse": (
            "Please respond with only valid JSON in this format:\n"
            "{ 'sentiment': '...', 'rationale': '...', 'key_levels': [...], 'takeaway': '...' }\n"
            "Using the volume, open interest, and implied volatility of this options chain, assess overall trader sentiment. "
            "Is it bullish, bearish, or neutral? Provide reasoning based on where traders are placing bets (e.g., OTM calls vs puts, ATM volumes). "
            "Mention any deviations from analyst consensus."
        ),

        "Support/Resistance": (
            "Please respond with only valid JSON in this format:\n"
            "{ 'support_levels': [...], 'resistance_levels': [...], 'rationale': '...', 'takeaway': '...' }\n"
            "Based on open interest patterns, identify likely support and resistance levels. "
            "Focus on strikes with significantly elevated OI relative to surrounding levels."
        ),

        "IV Skew Analysis": (
            "Please respond with only valid JSON in this format:\n"
            "{ 'skew_type': '...', 'key_observations': '...', 'iv_range': '...', 'takeaway': '...' }\n"
            "Analyze the implied volatility skew across strikes. "
            "Comment on whether skew favors downside or upside protection, and what this suggests about market expectations."
        ),

        "Unusual Flow": (
            "Please respond with only valid JSON in this format:\n"
            "{ 'flagged_strikes': [...], 'observation': '...', 'takeaway': '...' }\n"
            "Highlight any unusual volume or open interest patterns that suggest large trades or directional bets. "
            "Look for volume spikes at unexpected strikes or new OI builds."
        ),

        "Risk Factors": (
            "Please respond with only valid JSON in this format:\n"
            "{ 'risks': [...], 'implications': '...', 'takeaway': '...' }\n"
            "What are the key risks implied by this options chain (e.g., time decay, volatility compression, earnings exposure)? "
            "Mention where positions are most vulnerable."
        ),

        "Strategist Summary": (
            "Please respond with only valid JSON in this format:\n"
            "{ 'summary': '...', 'confidence_level': '...', 'recommended_read': '...' }\n"
            "Summarize this options chain as if writing a strategist report. "
            "Integrate positioning, skew, and key strike zones. "
            "Conclude with a confident takeaway a client could act on."
        )
    }

    results = []
    progress_bar = st.progress(0)
    step = 1 / len(task_prompts)

    for i, (task_name, prompt) in enumerate(task_prompts.items()):
        messages = construct_prompt(
            ticker=ticker,
            expiration=expiration,
            calls_df=calls_df,
            puts_df=puts_df,
            stock_info=stock_info,
            user_question=prompt
        )

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
        results.append(parsed)
        progress_bar.progress(min((i + 1) * step, 1.0))

    progress_bar.empty()
    return results

