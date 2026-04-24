from __future__ import annotations

import streamlit as st

NEW_URL = "https://licea-warszawa.streamlit.app/"


def build_redirect_html(new_url: str = NEW_URL) -> str:
    """Zwraca HTML z przekierowaniem i linkiem awaryjnym."""
    return f"""
    <script>
        window.location.replace("{new_url}");
    </script>
    <noscript>
        JavaScript jest wyłączony. Użyj linku poniżej, aby przejść do aktualnej wersji aplikacji.
    </noscript>
    <p>
        Jeżeli przekierowanie nie zadziała, przejdź tutaj:
        <a href="{new_url}">{new_url}</a>
    </p>
    """


def render_redirect_html(html: str) -> None:
    """Renderuje redirect bez iframe, zgodnie z aktualnym API Streamlit."""
    st.html(html, unsafe_allow_javascript=True)


def main() -> None:
    st.set_page_config(
        page_title="Licea Warszawa - nowy adres",
        page_icon="🎓",
    )

    render_redirect_html(build_redirect_html())

    st.title("Aplikacja ma nowy adres")
    st.write("Aktualna wersja aplikacji jest dostępna tutaj:")
    st.link_button("Przejdź do aktualnej wersji", NEW_URL)


if __name__ == "__main__":
    main()
