# src/insights/llm_interpreter.py

import openai
import pandas as pd
import textwrap

from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI()

# === Step 1: Summarize option chain ===
def summarize_option_chain(df: pd.DataFrame, option_type: str) -> str:
    summary = []
    summary.append(f"{option_type.upper()} OPTIONS:")

    if df.empty:
        summary.append("No data available.")
        return "\n".join(summary)

    summary.append(f"Strike range: ${df['strike'].min():.2f} to ${df['strike'].max():.2f}")
    summary.append(f"IV: avg {df['impliedVolatility'].mean():.1%}, range {df['impliedVolatility'].min():.1%} - {df['impliedVolatility'].max():.1%}")
    summary.append(f"Volume: total {df['volume'].sum():,}, peak at ${df.loc[df['volume'].idxmax(), 'strike']} with {df['volume'].max():,} contracts")
    summary.append(f"OI: total {df['openInterest'].sum():,}, hotspot at ${df.loc[df['openInterest'].idxmax(), 'strike']}")
    summary.append("")
    return "\n".join(summary)

# === Step 2: Build prompt context ===
def construct_prompt(ticker: str, expiration: str, calls_df: pd.DataFrame, puts_df: pd.DataFrame, user_question: str) -> list:
    calls_summary = summarize_option_chain(calls_df, "CALL")
    puts_summary = summarize_option_chain(puts_df, "PUT")

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

    Return your final response using Markdown format:
    - Use #### for section headers
    - Use numbered lists for insights
    - Use **bold** or _italic_ for emphasis
    - Do not use HTML or raw code blocks
    ''')

    return [
        {"role": "system", "content": "You are a professional options strategist generating daily summaries from live options chain data."},
        {"role": "user", "content": schema_description},
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

# === Step 4: Orchestrator with cache and loop tracker ===
from typing import Tuple
from streamlit.runtime.caching import cache_data

@cache_data(show_spinner="Generating AI insight...")
def get_llm_insight(ticker: str, expiration: str, calls_df: pd.DataFrame, puts_df: pd.DataFrame, user_question: str) -> Tuple[str, int]:
    messages = construct_prompt(ticker, expiration, calls_df, puts_df, user_question)
    summary = ask_openai(messages)
    return summary, len(messages) - 3  # Count assistant interactions only