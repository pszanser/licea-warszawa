"""Testy nowych helperów do geokodowania pojedynczego adresu (Streamlit Fit tab)."""

from unittest.mock import patch

from scripts.api_clients.googlemaps_api import (
    build_gmaps_client,
    geocode_address,
)


def test_geocode_address_returns_lat_lon(mock_gmaps_geocode):
    mock_gmaps_geocode.geocode.return_value = [
        {"geometry": {"location": {"lat": 52.23, "lng": 21.01}}}
    ]
    result = geocode_address(mock_gmaps_geocode, "ul. Marszałkowska 1, Warszawa")
    assert result == (52.23, 21.01)
    call_kwargs = mock_gmaps_geocode.geocode.call_args.kwargs
    assert call_kwargs["address"] == "ul. Marszałkowska 1, Warszawa"
    assert call_kwargs["region"] == "pl"
    assert "components" not in call_kwargs


def test_geocode_address_passes_custom_components(mock_gmaps_geocode):
    mock_gmaps_geocode.geocode.return_value = [
        {"geometry": {"location": {"lat": 50.0, "lng": 19.9}}}
    ]
    geocode_address(
        mock_gmaps_geocode,
        "Rynek Główny 1",
        components={"country": "PL"},
    )
    assert mock_gmaps_geocode.geocode.call_args.kwargs["components"] == {
        "country": "PL"
    }


def test_geocode_address_handles_empty_input(mock_gmaps_geocode):
    assert geocode_address(mock_gmaps_geocode, "") is None
    assert geocode_address(mock_gmaps_geocode, "   ") is None
    mock_gmaps_geocode.geocode.assert_not_called()


def test_geocode_address_handles_no_results(mock_gmaps_geocode):
    mock_gmaps_geocode.geocode.return_value = []
    assert geocode_address(mock_gmaps_geocode, "nieistniejący adres xyz") is None


def test_geocode_address_handles_api_exception(mock_gmaps_geocode):
    mock_gmaps_geocode.geocode.side_effect = RuntimeError("API down")
    assert geocode_address(mock_gmaps_geocode, "ul. Testowa 1") is None


def test_geocode_address_handles_malformed_response(mock_gmaps_geocode):
    mock_gmaps_geocode.geocode.return_value = [{"unexpected": "structure"}]
    assert geocode_address(mock_gmaps_geocode, "ul. Testowa 1") is None


def test_geocode_address_with_none_client_returns_none():
    assert geocode_address(None, "Marszałkowska 1") is None


def test_build_gmaps_client_without_api_key_returns_none(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    assert build_gmaps_client() is None


def test_build_gmaps_client_with_explicit_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    fake_client = object()
    with patch("googlemaps.Client", return_value=fake_client):
        result = build_gmaps_client(api_key="fake-key")
    assert result is fake_client


def test_build_gmaps_client_handles_client_exception(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "broken-key")
    with patch("googlemaps.Client", side_effect=ValueError("invalid key")):
        assert build_gmaps_client() is None
