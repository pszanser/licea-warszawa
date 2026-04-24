from scripts.visualization.redirect_2025 import NEW_URL, build_redirect_html


def test_redirect_2025_html_points_to_new_app():
    html = build_redirect_html()

    assert NEW_URL == "https://licea-warszawa.streamlit.app/"
    assert f'window.location.replace("{NEW_URL}")' in html
    assert f'href="{NEW_URL}"' in html
    assert "<noscript>" in html
