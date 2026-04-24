from scripts.visualization.redirect_2025 import NEW_URL, build_notice_markdown


def test_redirect_2025_notice_points_to_new_app_without_auto_redirect():
    notice = build_notice_markdown()

    assert NEW_URL == "https://licea-warszawa.streamlit.app/"
    assert f"[{NEW_URL}]({NEW_URL})" in notice
    assert "window.location" not in notice
    assert "<script" not in notice
