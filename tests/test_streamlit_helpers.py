import pandas as pd
from scripts.visualization.streamlit_mapa_licea import get_unique_districts


def test_get_unique_districts():
    df = pd.DataFrame({"Dzielnica": ["B", "A", "B", None]})
    assert get_unique_districts(df) == ["A", "B"]
