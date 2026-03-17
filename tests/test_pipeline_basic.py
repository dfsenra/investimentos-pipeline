import pandas as pd

def confere_conteudo_indices():
    df = pd.read_csv("data/indices.csv")
    assert not df.empty

