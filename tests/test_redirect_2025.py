from scripts.visualization.redirect_2025 import (
    NEW_URL,
    build_hero_html,
    build_notice_markdown,
    build_page_styles,
)


def test_redirect_2025_notice_points_to_new_app_without_auto_redirect():
    notice = build_notice_markdown()
    hero = build_hero_html()
    styles = build_page_styles()

    assert NEW_URL == "https://licea-warszawa.streamlit.app/"
    assert f"[{NEW_URL}]({NEW_URL})" in notice
    assert f'href="{NEW_URL}"' in hero
    assert "licea-warszawa-2025.streamlit.app" in hero
    assert "route-map" in styles
    assert "window.location" not in notice + hero + styles
    assert "<script" not in notice + hero + styles
