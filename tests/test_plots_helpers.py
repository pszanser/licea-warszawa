import pytest
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scripts.visualization.plots import (
    get_top_n,
    get_top_subjects,
    merge_with_district,
    plot_heatmap_with_annotations,
    heat_pairs,
    lollipop_diff_top30,
    heatmap_profiles_by_district,
    heatmap_subjects_by_district,
    bubble_prog_vs_dojazd,
    heatmap_rank_commute,
)

def test_get_top_n():
    # series with values a:3, b:2, c:1
    s = pd.Series(['a', 'b', 'a', 'c', 'b', 'a'])
    top2 = get_top_n(s, 2)
    assert top2 == ['a', 'b']

def test_get_top_subjects():
    # only matematyka and fizyka in columns
    """
    Testuje funkcję get_top_subjects, sprawdzając czy zwraca poprawnie dwa najczęściej występujące przedmioty na podstawie sum kolumn w DataFrame.
    """
    df = pd.DataFrame({
        'matematyka': [1, 0, 1],
        'fizyka': [0, 1, 1],
        'inne': [1, 1, 1]
    })
    top2 = get_top_subjects(df, 2)
    # sums: matematyka=2, fizyka=2, order follows SUBJECTS
    assert top2 == ['matematyka', 'fizyka']

def test_merge_with_district():
    df_kl = pd.DataFrame({
        'SzkolaIdentyfikator': [1, 2],
        'Val': [10, 20]
    })
    df_szkoly = pd.DataFrame({
        'SzkolaIdentyfikator': [1],
        'Dzielnica': ['A']
    })
    # merge adds Dzielnica, missing maps to NaN
    res = merge_with_district(df_kl, df_szkoly)
    assert 'Dzielnica' in res.columns
    assert res.loc[res['SzkolaIdentyfikator'] == 1, 'Dzielnica'].iloc[0] == 'A'
    assert pd.isna(res.loc[res['SzkolaIdentyfikator'] == 2, 'Dzielnica'].iloc[0])
    # if Dzielnica already present, copy unchanged
    df_kl2 = df_kl.copy()
    df_kl2['Dzielnica'] = ['X', 'Y']
    res2 = merge_with_district(df_kl2, df_szkoly)
    pd.testing.assert_frame_equal(res2, df_kl2)

def test_plot_heatmap_with_annotations():
    # simple 2x2 matrix
    mat = np.array([[1, 2], [3, 4]])
    x = ['x1', 'x2']
    y = ['y1', 'y2']
    fig = plot_heatmap_with_annotations(mat, x, y, 'T', 'X', 'Y')
    assert isinstance(fig, plt.Figure)
    ax = fig.axes[0]
    assert ax.get_title() == 'T'
    # check that tick labels match input
    assert [t.get_text() for t in ax.get_xticklabels()] == x
    assert [t.get_text() for t in ax.get_yticklabels()] == y

def test_heat_pairs():
    # create binary subject DataFrame
    """
    Testuje funkcję heat_pairs, sprawdzając czy zwraca wykres par rozszerzonych przedmiotów.
    
    Tworzy binarną ramkę danych z przedmiotami, wywołuje funkcję heat_pairs i weryfikuje, że zwrócony obiekt to Figure z odpowiednim tytułem wykresu.
    """
    df = pd.DataFrame({
        'matematyka': [1, 1, 0],
        'fizyka': [1, 0, 1]
    })
    fig = heat_pairs(df, 'TAG', top_n_subj=2)
    assert isinstance(fig, plt.Figure)
    ax = fig.axes[0]
    assert 'TAG: duety rozszerzeń' in ax.get_title()

def test_lollipop_diff_top30():
    # create Profil and RankingPoz
    """
    Testuje funkcję lollipop_diff_top30, sprawdzając czy zwraca obiekt Figure z odpowiednim tytułem wykresu dla danych o profilach i pozycjach rankingowych.
    """
    df = pd.DataFrame({
        'Profil': ['A', 'B', 'A', 'C'],
        'RankingPoz': [1, 40, 10, 20]
    })
    fig = lollipop_diff_top30(df)
    assert isinstance(fig, plt.Figure)
    ax = fig.axes[0]
    assert 'Które profile' in ax.get_title()

def test_heatmap_profiles_by_district():
    # no data returns None
    assert heatmap_profiles_by_district(None, None) is None

def test_heatmap_subjects_by_district():
    # no data returns None
    """
    Testuje, czy funkcja heatmap_subjects_by_district zwraca None przy braku danych wejściowych.
    """
    assert heatmap_subjects_by_district(None, None) is None

def test_bubble_prog_vs_dojazd():
    # minimal DataFrame with required cols
    """
    Testuje funkcję bubble_prog_vs_dojazd, sprawdzając czy zwraca obiekt Figure z odpowiednią etykietą osi X dla czasu dojazdu.
    """
    df = pd.DataFrame({
        'CzasDojazdu': [10, 20, 30],
        'Prog_min_szkola': [100, 200, 150],
        'RankingPoz': [1, 2, 3],
        'Dzielnica': ['X', 'Y', 'Z']
    })
    fig = bubble_prog_vs_dojazd(df)
    assert isinstance(fig, plt.Figure)
    ax = fig.axes[0]
    assert ax.get_xlabel() == 'Czas dojazdu [min]'

def test_heatmap_rank_commute():
    # minimal DataFrame with required cols
    """
    Testuje funkcję heatmap_rank_commute, sprawdzając poprawność generowanego wykresu.
    
    Tworzy minimalny DataFrame z kolumnami 'CzasDojazdu' i 'RankingPoz', wywołuje funkcję heatmap_rank_commute i weryfikuje, czy zwracany obiekt to instancja matplotlib Figure oraz czy etykieta osi X jest ustawiona prawidłowo.
    """
    df = pd.DataFrame({
        'CzasDojazdu': [5, 25, 45],
        'RankingPoz': [5, 15, 35]
    })
    fig = heatmap_rank_commute(df)
    assert isinstance(fig, plt.Figure)
    ax = fig.axes[0]
    # check labels
    assert ax.get_xlabel() == 'Czas dojazdu [min]'