import pandas as pd

from scripts.data_processing.load_plan_naboru import load_plan_naboru


def test_load_plan_naboru_multilevel_header(monkeypatch):
    columns = pd.MultiIndex.from_tuples(
        [
            ("Dzielnica", "Unnamed: 0_level_1"),
            ("Typ szkoły", "typ"),
            ("Nazwa szkoły", "Unnamed: 2_level_1"),
            ("Ulica", "Unnamed: 3_level_1"),
            ("Typ oddziału", "Unnamed: 4_level_1"),
            (
                "Zawód lub język w oddziałach dwujęzycznych",
                "Unnamed: 5_level_1",
            ),
            ("Plan naboru na rok szkolny 2026/2027", "Liczba oddziałów"),
            ("Plan naboru na rok szkolny 2026/2027", "liczba miejsc"),
        ]
    )
    mock_df = pd.DataFrame(
        [
            ["Bemowo", "LO", "LO nr 1", "Szkolna 1", "O", None, 2, 64],
            ["Wola", "T", "Technikum nr 1", "Zawodowa 1", "O", "technik", 1, 30],
        ],
        columns=columns,
    )

    def mock_read_excel(*args, **kwargs):
        assert args[0] == "plan.xlsx"
        assert kwargs.get("header") == [1, 2]
        return mock_df

    monkeypatch.setattr(pd, "read_excel", mock_read_excel)

    result = load_plan_naboru("plan.xlsx", year=2026, school_year="2026/2027")

    assert result["TypSzkoly"].tolist() == ["liceum", "technikum"]
    assert result["LiczbaOddzialowPlan"].tolist() == [2, 1]
    assert result["LiczbaMiejscPlan"].tolist() == [64, 30]
    assert result["year"].tolist() == [2026, 2026]
    assert result["school_year"].tolist() == ["2026/2027", "2026/2027"]
