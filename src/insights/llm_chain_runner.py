import pandas as pd
from src.insights.llm_interpreter import construct_prompt, ask_openai
from typing import List

def start_llm_chain(
    ticker: str,
    expiration: str,
    calls_df: pd.DataFrame,
    puts_df: pd.DataFrame,
    stock_info: dict,
    user_question: str
) -> List[dict]:
    """Begins a multi-step LLM conversation."""
    return construct_prompt(ticker, expiration, calls_df, puts_df, stock_info, user_question)

def continue_llm_chain(messages: list, user_followup: str, model="gpt-4o", temperature=0.5):
    """Appends a new user prompt and gets next LLM response."""
    messages.append({"role": "user", "content": user_followup})
    reply = ask_openai(messages, model=model, temperature=temperature)
    messages.append({"role": "assistant", "content": reply})
    return messages
