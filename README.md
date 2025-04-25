# Market Sentiment App

Analyze PUT/CALL option chains to understand market expectations.
# 📈 Market Sentiment Explorer

This is a Streamlit-based web application that helps users explore market expectations using CALL and PUT options data. The app provides both filtered raw options data and AI-powered strategic insights based on option chain analytics.

---

## 🔧 Features

### 🧰 Core Functionality
- Load options chain for any ticker and expiration using **yfinance**
- View **CALL** and **PUT** data with filters for:
  - Strike range
  - Volume
  - Open Interest (OI)
  - Implied Volatility (IV)

### 🤖 GPT-Powered Insights
- Generate **multi-dimensional option chain summaries** using OpenAI GPT-4
- 6 strategic modules:
  1. **Sentiment Pulse** – Understand overall trader sentiment
  2. **Support/Resistance** – Infer price levels with high OI clustering
  3. **IV Skew Analysis** – Identify upside/downside pricing bias
  4. **Unusual Flow** – Detect anomalies in volume/OI
  5. **Risk Factors** – Spot time decay, volatility risk, etc.
  6. **Strategist Summary** – High-level narrative summary

### 🧼 UI Enhancements
- Tooltip-style explanations for each insight module
- Progress bar when generating multi-insight summaries
- Toggle to show raw GPT response (for developers)
- Auto-escaped dollar signs (`\$`) for clean rendering

---

## 📦 Installation

```bash
git clone https://github.com/kstar1/market-sentiment-app.git
cd market-sentiment-app
pip install -r requirements.txt
```

Create a `.env` file with your OpenAI key:
```env
OPENAI_API_KEY=your-key-here
```

---

## 🚀 Run the App

```bash
streamlit run streamlit_app.py
```

---

## 🧪 Notes

- App uses **yfinance**, which may occasionally return stale or zero values for `openInterest`, `bid`, and `ask`.
- This version disables caching for stability, but caching logic can be reintroduced later using JSON-normalized inputs.

---

## 📋 To Do
- Add markdown export
- Integrate historical IV comparison
- Cross-expiry ladder analysis (coming soon!)
