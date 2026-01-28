import pandas as pd

def test_tickers_file_not_empty():
    df = pd.read_csv("data/tickers.csv")
    assert not df.empty

