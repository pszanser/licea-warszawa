import pandas as pd

def load_min_points(excel_path):
    df_punkty = pd.read_excel(excel_path, header=2)
    df_punkty = df_punkty.rename(columns={
        "Minimalna": "MinPunkty",
        "Nazwa szkoły": "NazwaSzkoly",
        "Nazwa krótka oddziału": "OddzialNazwa"
    })
    return df_punkty


def main():
    df = load_min_points("data/Minimalna liczba punktów 2024.xlsx")
    print(df.head())

if __name__ == "__main__":
    main()