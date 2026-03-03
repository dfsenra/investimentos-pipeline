import os

def test_indices_file_exists():
    assert os.path.exists("data/indices.csv")
