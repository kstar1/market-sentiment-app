# src/data/option_loader.py

import yfinance as yf
import pandas as pd

def get_expirations(ticker: str) -> list[str]:
    """
    Returns a list of expiration dates available for the given ticker.
    """
    try:
        ticker_obj = yf.Ticker(ticker)
        return ticker_obj.options
    except Exception as e:
        print(f"[Error] Unable to fetch expiration dates for {ticker}: {e}")
        return []

def get_option_chain(ticker: str, expiration: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns PUT and CALL DataFrames for the given ticker and expiration date.
    """
    try:
        ticker_obj = yf.Ticker(ticker)
        chain = ticker_obj.option_chain(expiration)
        
        puts_df = clean_option_df(chain.puts, "PUT")
        calls_df = clean_option_df(chain.calls, "CALL")

        return puts_df, calls_df
    except Exception as e:
        print(f"[Error] Unable to fetch option chain for {ticker} @ {expiration}: {e}")
        return pd.DataFrame(), pd.DataFrame()

def clean_option_df(df: pd.DataFrame, option_type: str) -> pd.DataFrame:
    """
    Adds metadata and formats the DataFrame for downstream use.
    """
    df = df.copy()
    df["optionType"] = option_type
    df["lastTradeDate"] = pd.to_datetime(df["lastTradeDate"])
    
    # Reorder columns to prioritize relevant info
    preferred_order = [
        "contractSymbol", "optionType", "strike", "lastPrice",
        "bid", "ask", "volume", "openInterest", "impliedVolatility",
        "lastTradeDate", "inTheMoney"
    ]
    cols = [col for col in preferred_order if col in df.columns]
    df = df[cols]
    
    return df.reset_index(drop=True)

def get_stock_info(ticker_symbol: str) -> dict:
    """
    Fetches summary stock information for the given ticker.

    Args:
        ticker_symbol (str): Ticker symbol like 'AAPL'

    Returns:
        dict: Core metrics and full info for deeper display
    """
    ticker = yf.Ticker(ticker_symbol)
    info = {}

    try:
        info = ticker.info
    except:
        pass  # fallback to empty dict if error

    return {
        "current_price": info.get("regularMarketPrice", "N/A"),
        "beta": info.get("beta", "N/A"),
        "recommendation": info.get("recommendationKey", "N/A"),
        "website": info.get("website", "#"),
        "full_info": info  # pass full dict for optional expansion
    }