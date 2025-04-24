# src/insights/llm_interpreter.py

import openai
import pandas as pd
import textwrap
from dotenv import load_dotenv
from openai import OpenAI
import os
from typing import Tuple
from streamlit.runtime.caching import cache_data
from src.utils.helpers import sanitize_insights

import hashlib
import json
import re

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI()

# === Step 1: Summarize option chain ===
def summarize_option_chain(df: pd.DataFrame, option_type: str) -> str:
    summary = [f"{option_type.upper()} OPTIONS:"]
    if df.empty:
        summary.append("No data available.")
        return "\n".join(summary)

    summary.append(f"Strike range: ${df['strike'].min():.2f} to ${df['strike'].max():.2f}")
    summary.append(
        f"IV: avg {df['impliedVolatility'].mean():.1%}, "
        f"range {df['impliedVolatility'].min():.1%} - {df['impliedVolatility'].max():.1%}"
    )
    summary.append(
        f"Volume: total {df['volume'].sum():,}, "
        f"peak at ${df.loc[df['volume'].idxmax(), 'strike']} with {df['volume'].max():,} contracts"
    )
    summary.append(
        f"OI: total {df['openInterest'].sum():,}, "
        f"hotspot at ${df.loc[df['openInterest'].idxmax(), 'strike']}"
    )
    summary.append("")
    return "\n".join(summary)

# === Step 2: Build prompt context ===
def construct_prompt(
    ticker: str,
    expiration: str,
    calls_df: pd.DataFrame,
    puts_df: pd.DataFrame,
    stock_info: dict,
    user_question: str
) -> list:
    calls_summary = summarize_option_chain(calls_df, "CALL")
    puts_summary = summarize_option_chain(puts_df, "PUT")

    stock_summary = textwrap.dedent(f"""
    Stock Overview:
    - Ticker: {ticker}
    - Current Price: ${stock_info.get('current_price', 'N/A')}
    - Beta: {stock_info.get('beta', 'N/A')}
    - Analyst Recommendation: {stock_info.get('recommendation', 'N/A')}
    """)

    schema_description = textwrap.dedent('''
    You have access to two DataFrames: calls_df and puts_df. Each contains columns:
    - strike (float)
    - lastPrice (float)
    - bid, ask (float)
    - volume (int)
    - openInterest (int)
    - impliedVolatility (float, 0-1)
    - lastTradeDate (datetime)
    - inTheMoney (bool)
    - optionType ("CALL" or "PUT")

    You may ask for:
    - specific strikes (e.g., IV at $250)
    - average or max volume/open interest
    - IV skew between OTM PUTs and CALLs
    - volume anomalies
    - time decay implications if Theta is provided later

    You may ask for 2 - 3 clarifications before your final response.

    Return only the JSON object. Do not include explanations, introductions, or closing remarks. Respond only with valid JSON in the exact format:
    {
    "summary_heading": "string",
    "call_summary": {
        "iv_range": "string",
        "peak_volume_strike": float,
        "peak_volume": int
    },
    "put_summary": {
        "iv_range": "string",
        "peak_oi_strike": float,
        "peak_oi": int
    },
    "insights": [ "string", "string", ... ]
    }
    ''')

    return [
        {"role": "system", "content": "You are a professional options strategist generating daily summaries from live options chain data."},
        {"role": "user", "content": schema_description},
        {"role": "user", "content": stock_summary},
        {"role": "user", "content": f"Option chain for {ticker} expiring {expiration}:\n\n{calls_summary}\n{puts_summary}"},
        {"role": "user", "content": user_question.strip()},
    ]

# === Step 3: Ask OpenAI ===
def ask_openai(messages: list, model="gpt-4o", temperature=0.5, max_tokens=800):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content

# === Step 4: Generate cache key ===
def _make_cache_key(ticker, expiration, calls_df, puts_df, stock_info, user_question):
    key_data = {
        "ticker": ticker,
        "expiration": expiration,
        "user_question": user_question,
        "calls_hash": int(pd.util.hash_pandas_object(calls_df, index=True).sum()),
        "puts_hash": int(pd.util.hash_pandas_object(puts_df, index=True).sum()),
        "price": stock_info.get("current_price", "N/A")
    }
    raw = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()

# === Step 5: Public entry point (with cache) ===
@cache_data(show_spinner="Generating AI insight...", experimental_allow_widgets=True)
def get_llm_insight(
    ticker: str,
    expiration: str,
    calls_df: pd.DataFrame,
    puts_df: pd.DataFrame,
    stock_info: dict,
    user_question: str
) -> Tuple[dict, int]:
    cache_key = _make_cache_key(ticker, expiration, calls_df, puts_df, stock_info, user_question)
    return _cached_llm_insight(ticker, expiration, calls_df, puts_df, stock_info, user_question, cache_key)

# === Step 6: Cached internal logic ===
@cache_data
def _cached_llm_insight(ticker, expiration, calls_df, puts_df, stock_info, user_question, _cache_key) -> Tuple[dict, int]:
    messages = construct_prompt(ticker, expiration, calls_df, puts_df, stock_info, user_question)
    response = ask_openai(messages)

    try:
        json_match = re.search(r'\{[\s\S]+\}', response)
        if not json_match:
            raise ValueError("No JSON found")

        parsed = json.loads(json_match.group(0))
        parsed["insights"] = sanitize_insights(parsed.get("insights", []))
        return parsed, len(messages) - 4
    except Exception as e:
        return {"error": f"Failed to parse JSON from GPT: {str(e)}"}, len(messages) - 4
