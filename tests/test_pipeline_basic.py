import pandas as pd

def test_indices_file_not_empty():
    df = pd.read_csv("data/indices.csv")
    assert not df.empty

