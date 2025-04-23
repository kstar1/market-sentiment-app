# test/test_option_loader.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.data.option_loader import get_expirations, get_option_chain

def test_get_expirations():
    ticker = "AAPL"
    expirations = get_expirations(ticker)
    print(f"Expirations for {ticker}:", expirations)

def test_get_option_chain():
    ticker = "AAPL"
    expirations = get_expirations(ticker)
    if expirations:
        puts_df, calls_df = get_option_chain(ticker, expirations[0])
        print("\nSample PUTs:\n", puts_df.head())
        print("\nSample CALLs:\n", calls_df.head())
    else:
        print("No expirations available for", ticker)

if __name__ == "__main__":
    test_get_expirations()
    test_get_option_chain()
