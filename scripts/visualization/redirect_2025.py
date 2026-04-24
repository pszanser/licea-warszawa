from __future__ import annotations

import streamlit as st

NEW_URL = "https://licea-warszawa.streamlit.app/"


def build_notice_markdown(new_url: str = NEW_URL) -> str:
    """Zwraca komunikat z linkiem do aktualnej aplikacji."""
    return (
        "Aktualna wersja aplikacji jest dostępna pod nowym adresem:\n\n"
        f"[{new_url}]({new_url})"
    )


def main() -> None:
    st.set_page_config(
        page_title="Licea Warszawa - nowy adres",
        page_icon="🎓",
    )

    st.title("Aplikacja ma nowy adres")
    st.markdown(build_notice_markdown())
    st.link_button("Przejdź do aktualnej wersji", NEW_URL)


if __name__ == "__main__":
    main()
