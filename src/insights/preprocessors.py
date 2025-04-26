# src/insights/preprocessors.py

import pandas as pd
import numpy as np
from scipy.stats import linregress

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
