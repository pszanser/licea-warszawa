from __future__ import annotations

from html import escape

import streamlit as st

NEW_URL = "https://licea-warszawa.streamlit.app/"
OLD_URL_LABEL = "licea-warszawa-2025.streamlit.app"
NEW_URL_LABEL = "licea-warszawa.streamlit.app"


def build_page_styles() -> str:
    """Zwraca statyczne style strony informacyjnej."""
    return """
    <style>
    .block-container {
        max-width: 860px;
        padding-top: 3.25rem;
    }

    .redirect-kicker {
        color: #1f7a5f;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0;
        margin-bottom: 0.45rem;
        text-transform: uppercase;
    }

    .redirect-title {
        color: #172026;
        font-size: 2.35rem;
        font-weight: 750;
        letter-spacing: 0;
        line-height: 1.12;
        margin: 0 0 0.8rem;
    }

    .redirect-lead {
        color: #46545f;
        font-size: 1.05rem;
        line-height: 1.6;
        margin: 0 0 1.6rem;
    }

    .route-map {
        background-color: #f7faf8;
        background-image:
            linear-gradient(#dfeae4 1px, transparent 1px),
            linear-gradient(90deg, #dfeae4 1px, transparent 1px);
        background-size: 34px 34px;
        border: 1px solid #d6e3dc;
        border-radius: 8px;
        margin: 1.5rem 0 1.35rem;
        padding: 1rem;
    }

    .route-row {
        align-items: center;
        display: flex;
        gap: 0.75rem;
    }

    .route-node {
        background: #ffffff;
        border: 1px solid #cbd8d2;
        border-radius: 8px;
        flex: 1;
        min-width: 0;
        padding: 0.9rem 1rem;
    }

    .route-node-active {
        border-color: #1f7a5f;
        box-shadow: inset 0 0 0 2px rgba(31, 122, 95, 0.14);
    }

    .route-label {
        color: #64727c;
        font-size: 0.78rem;
        font-weight: 650;
        letter-spacing: 0;
        margin-bottom: 0.2rem;
        text-transform: uppercase;
    }

    .route-url {
        color: #172026;
        font-family: "Source Code Pro", monospace;
        font-size: 0.92rem;
        overflow-wrap: anywhere;
    }

    .route-arrow {
        color: #1f7a5f;
        flex: 0 0 auto;
        font-size: 1.55rem;
        font-weight: 700;
        line-height: 1;
    }

    .redirect-note {
        color: #5d6b75;
        font-size: 0.92rem;
        margin: 0.5rem 0 1rem;
    }

    @media (max-width: 640px) {
        .block-container {
            padding-top: 2rem;
        }

        .redirect-title {
            font-size: 1.85rem;
        }

        .route-row {
            align-items: stretch;
            flex-direction: column;
        }

        .route-arrow {
            transform: rotate(90deg);
        }
    }
    </style>
    """


def build_notice_markdown(new_url: str = NEW_URL) -> str:
    """Zwraca komunikat z linkiem do aktualnej aplikacji."""
    return (
        "Aktualna wersja aplikacji jest dostępna pod nowym adresem:\n\n"
        f"[{new_url}]({new_url})"
    )


def build_hero_html(new_url: str = NEW_URL) -> str:
    """Zwraca statyczny HTML z graficznym opisem zmiany adresu."""
    safe_new_url = escape(new_url, quote=True)
    safe_old_label = escape(OLD_URL_LABEL)
    safe_new_label = escape(NEW_URL_LABEL)

    return f"""
    <section class="redirect-hero">
        <div class="redirect-kicker">Licea Warszawa</div>
        <h1 class="redirect-title">Mapa szkół ma nowy adres</h1>
        <p class="redirect-lead">
            Aktualna wersja aplikacji działa teraz pod adresem
            <strong>{safe_new_label}</strong>.
        </p>
        <div class="route-map" aria-label="Zmiana adresu aplikacji">
            <div class="route-row">
                <div class="route-node">
                    <div class="route-label">stary adres</div>
                    <div class="route-url">{safe_old_label}</div>
                </div>
                <div class="route-arrow" aria-hidden="true">→</div>
                <div class="route-node route-node-active">
                    <div class="route-label">aktualny adres</div>
                    <div class="route-url">{safe_new_label}</div>
                </div>
            </div>
        </div>
        <p><a href="{safe_new_url}">{safe_new_url}</a></p>
    </section>
    """


def main() -> None:
    st.set_page_config(
        page_title="Licea Warszawa - nowy adres",
        page_icon="🎓",
        layout="centered",
    )

    st.markdown(build_page_styles(), unsafe_allow_html=True)
    st.markdown(build_hero_html(), unsafe_allow_html=True)
    st.link_button(
        "Otwórz aktualną aplikację",
        NEW_URL,
        type="primary",
        icon=":material/open_in_new:",
    )


if __name__ == "__main__":
    main()
