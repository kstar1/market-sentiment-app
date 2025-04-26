# src/insights/preprocessors.py

import pandas as pd
import numpy as np

from scipy.stats import linregress
from datetime import datetime

# ========================
# HELPER FUNCTIONS
# ========================

def calculate_realized_vol(prices_df, window):
    returns = prices_df['Close'].pct_change().dropna()
    if len(returns) < window:
        return None  # not enough data
    realized_vol = returns.rolling(window=window).std() * np.sqrt(252)
    vol = realized_vol.iloc[-1]
    return float(vol * 100) if pd.notnull(vol) else None


def calculate_emas(prices_df):
    ema_20 = prices_df['Close'].ewm(span=20).mean().iloc[-1]
    ema_50 = prices_df['Close'].ewm(span=50).mean().iloc[-1]
    ema_200 = prices_df['Close'].ewm(span=200).mean().iloc[-1]
    return ema_20, ema_50, ema_200

def calculate_iv_rank_by_strike(df, all_ivs):
    """
    Calculates IV rank of a given option (df row) compared to the full chain.
    IV rank = percentage of other options with lower IV.
    """
    ranks = {}
    for idx, row in df.iterrows():
        current_iv = row["impliedVolatility"]
        if pd.isna(current_iv):
            ranks[idx] = None
        else:
            rank = 100 * (all_ivs < current_iv).sum() / len(all_ivs)
            ranks[idx] = round(rank, 2)
    return ranks

def find_atm_implied_vol(calls_df):
    if calls_df.empty:
        return None
    atm_row = calls_df.iloc[(calls_df['strike'] - calls_df['strike'].mean()).abs().argsort()[:1]]
    return atm_row['impliedVolatility'].values[0] * 100

def assess_divergence(vol_premium):
    if vol_premium > 15:
        return "overpriced"
    elif vol_premium < -15:
        return "underpriced"
    else:
        return "neutral"

def calculate_beta_and_correlation(stock_prices, spx_prices):
    merged = pd.merge(stock_prices[['Date', 'Close']], spx_prices[['Date', 'Close']], on='Date', suffixes=('_stock', '_spx'))
    merged['stock_return'] = merged['Close_stock'].pct_change()
    merged['spx_return'] = merged['Close_spx'].pct_change()
    merged = merged.dropna()
    beta, intercept, r_value, _, _ = linregress(merged['spx_return'], merged['stock_return'])
    return beta, r_value ** 2

# ========================
# MAIN PREPROCESSOR FUNCTIONS
# ========================

def prepare_volatility_risk_premium(calls_df, stock_history_df, expiration_date):
    realized_vol = calculate_realized_vol(stock_history_df, 90)
    atm_iv = find_atm_implied_vol(calls_df)
    
    if realized_vol is None:
        print("⚠️ Realized volatility (90D) could not be computed — not enough price history.")
    if atm_iv is None:
        print("⚠️ ATM implied volatility could not be found — maybe no CALLs?")

    vol_premium = atm_iv - realized_vol if realized_vol is not None and atm_iv is not None else None
    return {
        "realized_vol_90d": realized_vol,
        "atm_implied_vol": atm_iv,
        "volatility_premium": vol_premium,
        "divergence_flag": assess_divergence(vol_premium) if vol_premium is not None else "neutral",
        "expiration_date": expiration_date
    }

def prepare_unusual_options_flow(calls_df, puts_df, expiration_date):
    combined = pd.concat([calls_df, puts_df])
    unusual = combined[
        (combined['volume'] > combined['volume'].quantile(0.9)) &
        (combined['openInterest'].pct_change().fillna(0) > 2)
    ]

    all_ivs = combined["impliedVolatility"].dropna()
    iv_ranks = calculate_iv_rank_by_strike(unusual, all_ivs)

    flows = []
    for idx, row in unusual.iterrows():
        flows.append({
            "strike": row['strike'],
            "type": row['optionType'].lower(),
            "expiration": expiration_date,
            "volume": int(row['volume']),
            "open_interest_change": float(row['openInterest']),
            "iv_rank": iv_ranks.get(idx),
            "sentiment": "bullish" if row['optionType'] == "CALL" else "bearish"
        })

    return {"unusual_flow": flows}

def prepare_trend_confirmation(stock_history_df, puts_df, calls_df):
    ema_20, ema_50, ema_200 = calculate_emas(stock_history_df)
    last_close = stock_history_df['Close'].iloc[-1]
    trend_strength = 0
    if ema_20 > ema_50 > ema_200:
        trend_strength = 80
    elif ema_20 < ema_50 < ema_200:
        trend_strength = 20
    else:
        trend_strength = 50

    put_oi = puts_df['openInterest'].sum()
    call_oi = calls_df['openInterest'].sum()
    put_call_oi_ratio = put_oi / call_oi if call_oi > 0 else None
    divergence_warning = put_call_oi_ratio > 1.2 or put_call_oi_ratio < 0.8

    return {
        "ema_20": ema_20,
        "ema_50": ema_50,
        "ema_200": ema_200,
        "trend_strength": trend_strength,
        "put_call_oi_ratio": put_call_oi_ratio,
        "divergence_warning": divergence_warning
    }

def prepare_gamma_strike_clustering(calls_df, puts_df, current_price):
    combined = pd.concat([calls_df, puts_df])
    nearby = combined[
        (combined['strike'] >= current_price * 0.95) &
        (combined['strike'] <= current_price * 1.05) &
        (combined['openInterest'] > 10000)
    ]
    clusters = []
    for _, row in nearby.iterrows():
        clusters.append({
            "strike": row['strike'],
            "call_oi": int(row['openInterest']) if row['optionType'] == "CALL" else 0,
            "put_oi": int(row['openInterest']) if row['optionType'] == "PUT" else 0,
            "distance_from_price": abs(row['strike'] - current_price) / current_price * 100,
            "pinning_risk": abs(row['strike'] - current_price) / current_price < 0.01
        })
    return {"gamma_clusters": clusters}

def prepare_beta_adjusted_risk_profile(stock_history_df, spx_history_df, calls_df):
    beta, r_squared = calculate_beta_and_correlation(stock_history_df, spx_history_df)
    realized_vol_20d = calculate_realized_vol(stock_history_df, 20)
    atm_iv = find_atm_implied_vol(calls_df)

    score = int(np.clip((realized_vol_20d + atm_iv) / 10, 1, 10))
    if score <= 3:
        category = "low"
    elif score <= 6:
        category = "medium"
    else:
        category = "high"

    return {
        "beta_90d": beta,
        "realized_vol_20d": realized_vol_20d,
        "implied_vol": atm_iv,
        "composite_risk_score": score,
        "risk_category": category
    }

def prepare_synthetic_sentiment_index(stock_history_df, calls_df, puts_df, spx_history_df):
    last_30_returns = stock_history_df['Close'].pct_change(30).iloc[-1]
    price_momentum_contribution = int(np.clip(last_30_returns * 500, -100, 100))

    put_volume = puts_df['volume'].sum()
    call_volume = calls_df['volume'].sum()
    put_call_vol_ratio = put_volume / call_volume if call_volume > 0 else 1
    options_flow_contribution = int(np.clip((1 - put_call_vol_ratio) * 100, -50, 50))

    iv_skew = (puts_df['impliedVolatility'].mean() - calls_df['impliedVolatility'].mean()) * 100
    vol_skew_contribution = int(np.clip(-iv_skew * 2, -30, 30))

    _, r_squared = calculate_beta_and_correlation(stock_history_df, spx_history_df)
    market_correlation_contribution = int(r_squared * 20)

    total_score = np.clip(
        price_momentum_contribution +
        options_flow_contribution +
        vol_skew_contribution +
        market_correlation_contribution,
        0, 100
    )

    interpretation = "bearish" if total_score <= 30 else "bullish" if total_score >= 70 else "neutral"

    return {
        "score": total_score,
        "price_momentum_contribution": price_momentum_contribution,
        "options_flow_contribution": options_flow_contribution,
        "vol_skew_contribution": vol_skew_contribution,
        "market_correlation_contribution": market_correlation_contribution,
        "interpretation": interpretation
    }

# ======================== V2 functions ========================
def prepare_volatility_risk_premium_v2(calls_df, stock_history_df, expiration_date):
    realized_vol = calculate_realized_vol(stock_history_df, 90)
    atm_iv = find_atm_implied_vol(calls_df)
    
    volatility_analysis_data = {
        "realized_vol_90d": realized_vol,
        "atm_implied_vol": atm_iv,
        "volatility_premium": atm_iv - realized_vol if atm_iv is not None and realized_vol is not None else None,
        "expiration_date": expiration_date
    }
    return volatility_analysis_data

def prepare_unusual_flow_v2(calls_df, puts_df, expiration_date):
    combined = pd.concat([calls_df, puts_df])
    unusual = combined[
        (combined['volume'] > combined['volume'].quantile(0.9)) &
        (combined['openInterest'].pct_change().fillna(0) > 2)
    ]

    all_ivs = combined["impliedVolatility"].dropna()
    iv_ranks = calculate_iv_rank_by_strike(unusual, all_ivs)

    flows = []
    for idx, row in unusual.iterrows():
        flows.append({
            "strike": row['strike'],
            "type": row['optionType'].lower(),
            "expiration": expiration_date,
            "volume": int(row['volume']),
            "open_interest_change": float(row['openInterest']),
            "iv_rank": iv_ranks.get(idx),
            "sentiment": "bullish" if row['optionType'] == "CALL" else "bearish"
        })

    return {"unusual_flow": flows}

def prepare_trend_confirmation_v2(stock_history_df, puts_df, calls_df):
    ema_20, ema_50, ema_200 = calculate_emas(stock_history_df)

    put_oi = puts_df['openInterest'].sum()
    call_oi = calls_df['openInterest'].sum()
    put_call_oi_ratio = put_oi / call_oi if call_oi > 0 else None
    divergence_warning = put_call_oi_ratio > 1.2 or put_call_oi_ratio < 0.8

    return {
        "ema_20": ema_20,
        "ema_50": ema_50,
        "ema_200": ema_200,
        "put_call_oi_ratio": put_call_oi_ratio,
        "divergence_warning": divergence_warning
    }

def prepare_gamma_clustering_v2(calls_df, puts_df, current_price):
    combined = pd.concat([calls_df, puts_df])
    nearby = combined[
        (combined['strike'] >= current_price * 0.95) &
        (combined['strike'] <= current_price * 1.05) &
        (combined['openInterest'] > 10000)
    ]

    clusters = []
    for _, row in nearby.iterrows():
        clusters.append({
            "strike": row['strike'],
            "call_oi": int(row['openInterest']) if row['optionType'] == "CALL" else 0,
            "put_oi": int(row['openInterest']) if row['optionType'] == "PUT" else 0,
            "distance_from_price": abs(row['strike'] - current_price) / current_price * 100,
            "pinning_risk": abs(row['strike'] - current_price) / current_price < 0.01
        })
    
    return {"gamma_clusters": clusters}

def prepare_beta_risk_profile_v2(stock_history_df, spx_history_df, calls_df):
    beta, r_squared = calculate_beta_and_correlation(stock_history_df, spx_history_df)
    realized_vol_20d = calculate_realized_vol(stock_history_df, 20)
    atm_iv = find_atm_implied_vol(calls_df)

    score = int(np.clip((realized_vol_20d + atm_iv) / 10, 1, 10))
    if score <= 3:
        category = "low"
    elif score <= 6:
        category = "medium"
    else:
        category = "high"

    return {
        "beta_90d": beta,
        "realized_vol_20d": realized_vol_20d,
        "implied_vol": atm_iv,
        "composite_risk_score": score,
        "risk_category": category
    }

def prepare_sentiment_index_v2(stock_history_df, calls_df, puts_df, spx_history_df):
    last_30_returns = stock_history_df['Close'].pct_change(30).iloc[-1]
    price_momentum_contribution = int(np.clip(last_30_returns * 500, -100, 100))

    put_volume = puts_df['volume'].sum()
    call_volume = calls_df['volume'].sum()
    put_call_vol_ratio = put_volume / call_volume if call_volume > 0 else 1
    options_flow_contribution = int(np.clip((1 - put_call_vol_ratio) * 100, -50, 50))

    iv_skew = (puts_df['impliedVolatility'].mean() - calls_df['impliedVolatility'].mean()) * 100
    vol_skew_contribution = int(np.clip(-iv_skew * 2, -30, 30))

    _, r_squared = calculate_beta_and_correlation(stock_history_df, spx_history_df)
    market_correlation_contribution = int(r_squared * 20)

    total_score = np.clip(
        price_momentum_contribution +
        options_flow_contribution +
        vol_skew_contribution +
        market_correlation_contribution,
        0, 100
    )

    interpretation = "bearish" if total_score <= 30 else "bullish" if total_score >= 70 else "neutral"

    return {
        "score": total_score,
        "price_momentum_contribution": price_momentum_contribution,
        "options_flow_contribution": options_flow_contribution,
        "vol_skew_contribution": vol_skew_contribution,
        "market_correlation_contribution": market_correlation_contribution,
        "interpretation": interpretation
    }

# --- New preprocessor for Deep Research ---

def prepare_variance_risk_premium_v2(calls_df, stock_history_df, expiration_date):
    """
    Prepares inputs for Variance Risk Premium (VRP) analysis.
    """

    # Step 1: Calculate Realized Variance (past 30d)
    returns = stock_history_df['Close'].pct_change().dropna()
    if len(returns) < 30:
        print("⚠️ Not enough data to calculate realized variance (need ~30 days)")
        realized_variance = None
    else:
        realized_variance = returns.rolling(window=30).var().iloc[-1] * 252  # annualized

    # Step 2: Calculate Risk-Neutral Variance (from ATM IV)
    try:
        atm_row = calls_df.iloc[(calls_df['strike'] - stock_history_df['Close'].iloc[-1]).abs().argsort()[:1]]
        atm_iv = atm_row['impliedVolatility'].values[0]  # already in decimal (e.g., 0.30 for 30%)
    except Exception as e:
        print(f"⚠️ ATM IV fetch failed: {e}")
        atm_iv = None

    try:
        expiry_date = pd.to_datetime(expiration_date)
        today = datetime.now()
        days_to_expiry = max((expiry_date - today).days, 1)
    except Exception as e:
        print(f"⚠️ Expiry parse failed: {e}")
        days_to_expiry = 30  # fallback

    if atm_iv is not None:
        risk_neutral_variance = (atm_iv ** 2) * (days_to_expiry / 365)
    else:
        risk_neutral_variance = None

    # Step 3: Variance Risk Premium
    if realized_variance is not None and risk_neutral_variance is not None:
        variance_risk_premium = risk_neutral_variance - realized_variance
    else:
        variance_risk_premium = None

    return {
        "realized_variance_30d": realized_variance,
        "risk_neutral_variance": risk_neutral_variance,
        "variance_risk_premium": variance_risk_premium,
        "days_to_expiry": days_to_expiry,
        "expiration_date": expiration_date
    }

# --- New preprocessor for Term Structure Analysis ---

def prepare_term_structure_slope_v2(ticker: str, expirations: list[str]) -> dict:
    """
    Prepares inputs for Volatility Term Structure Slope analysis.
    """

    import yfinance as yf
    ticker_obj = yf.Ticker(ticker)

    term_structure_data = []

    for expiry in expirations[:5]:  # Only first 5 expirations to avoid overload
        try:
            chain = ticker_obj.option_chain(expiry)
            calls = chain.calls
            if calls.empty:
                continue

            atm_row = calls.iloc[(calls['strike'] - ticker_obj.info['regularMarketPrice']).abs().argsort()[:1]]
            atm_iv = atm_row['impliedVolatility'].values[0]

            term_structure_data.append({
                "expiration": expiry,
                "atm_implied_vol": atm_iv
            })
        except Exception as e:
            print(f"⚠️ Failed to fetch chain for {expiry}: {e}")
            continue

    # Sort by expiration
    term_structure_data = sorted(term_structure_data, key=lambda x: x["expiration"])

    # Calculate slope: (IV at later date - IV at near date) / time difference
    if len(term_structure_data) >= 2:
        first = term_structure_data[0]
        last = term_structure_data[-1]

        expiry_first = pd.to_datetime(first["expiration"])
        expiry_last = pd.to_datetime(last["expiration"])

        days_diff = (expiry_last - expiry_first).days
        iv_diff = last["atm_implied_vol"] - first["atm_implied_vol"]

        slope = iv_diff / days_diff if days_diff != 0 else None
    else:
        slope = None

    return {
        "term_structure_points": term_structure_data,
        "term_structure_slope": slope
    }

# --- New preprocessor for Crash Risk Premium Analysis ---

def prepare_crash_risk_premium_v2(calls_df, puts_df, stock_price: float) -> dict:
    """
    Prepares inputs for Crash Risk Premium (Skew) analysis.
    """

    if calls_df.empty or puts_df.empty:
        print("⚠️ Calls or Puts dataframe is empty. Cannot compute crash risk premium.")
        return {
            "put_skew_percent": None,
            "otm_put_iv": None,
            "otm_call_iv": None,
            "interpretation_flag": "data_missing"
        }

    # Define OTM region (20% OTM roughly)
    otm_puts = puts_df[puts_df['strike'] <= stock_price * 0.8]
    otm_calls = calls_df[calls_df['strike'] >= stock_price * 1.2]

    if otm_puts.empty or otm_calls.empty:
        print("⚠️ No sufficient OTM options to compute skew.")
        return {
            "put_skew_percent": None,
            "otm_put_iv": None,
            "otm_call_iv": None,
            "interpretation_flag": "insufficient_data"
        }

    # Average IV of deep OTM puts and calls
    otm_put_iv = otm_puts['impliedVolatility'].mean()
    otm_call_iv = otm_calls['impliedVolatility'].mean()

    # Compute skew
    put_skew_percent = ((otm_put_iv - otm_call_iv) / otm_call_iv) * 100 if otm_call_iv != 0 else None

    # Interpretation
    if put_skew_percent is None:
        interpretation = "insufficient_data"
    elif put_skew_percent > 20:
        interpretation = "high_crash_risk_priced"
    elif put_skew_percent > 5:
        interpretation = "moderate_crash_risk_priced"
    else:
        interpretation = "low_crash_risk_priced"

    return {
        "put_skew_percent": put_skew_percent,
        "otm_put_iv": otm_put_iv,
        "otm_call_iv": otm_call_iv,
        "interpretation_flag": interpretation
    }
