import os

def test_tickers_file_exists():
    assert os.path.exists("data/tickers.csv")
