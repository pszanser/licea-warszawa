import json
import shutil
from pathlib import Path

import pytest

from scripts.data_processing.get_data_pzo_omikron import (
    LABEL_CLASS_COUNT,
    LABEL_CLASS_DESCRIPTION,
    LABEL_CLASS_IDENTIFIER,
    LABEL_EXTENDED_SUBJECTS,
    LABEL_FILES,
    LABEL_FIRST_LANGUAGE,
    LABEL_SECOND_LANGUAGE,
    PzoOmikronClient,
    build_tables,
    fetch_offer_snapshot,
    load_snapshot_files,
    write_snapshot_files,
)


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload, ensure_ascii=False)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, fail_details=False):
        self.fail_details = fail_details
        self.calls = []

    def request(self, method, url, headers=None, json=None, timeout=None):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": headers or {},
                "json": json,
                "timeout": timeout,
            }
        )
        if url.endswith("/api/offer/search"):
            return FakeResponse(sample_metadata())
        if url.endswith("/api/offer/searchSubmit"):
            return FakeResponse(sample_search_result())
        if url.endswith("/api/offer/schoolDetails"):
            if self.fail_details:
                return FakeResponse({"error": "boom"}, status_code=500)
            return FakeResponse(sample_school_detail())
        raise AssertionError(f"Nieoczekiwany URL: {url}")


def sample_metadata():
    return {
        "schoolTypeList": [
            {
                "id": 4,
                "name": "Licea Ogólnokształcące",
            }
        ],
        "unknownMetadata": {"kept": True},
    }


def sample_search_result():
    return {
        "schoolList": [
            {
                "address": sample_address(),
                "schoolShort": {
                    "id": 123,
                    "latitude": 52.208,
                    "longitude": 21.012,
                    "logo": "LOGO_HASH",
                    "name": "VI LO im. Tadeusza Reytana",
                },
            }
        ],
        "unknownSearchField": {"kept": True},
    }


def sample_address():
    return {
        "street": "ul. Wiktorska",
        "house": "30/32",
        "flat": "",
        "zipcode": "02-587",
        "city": "Warszawa",
        "post": "Warszawa",
        "phone": "22 000 00 00",
    }


def sample_offer_item(label, value, extra=None):
    item = {
        "id": f"id-{label}",
        "label": label,
        "offerValue": value,
        "type": "TEXT",
    }
    if extra:
        item.update(extra)
    return item


def sample_school_detail():
    return {
        "schoolOffer": {
            "address": sample_address(),
            "email": "sekretariat@example.edu.pl",
            "fullName": "VI Liceum Ogólnokształcące im. Tadeusza Reytana",
            "headMaster": "Jan Kowalski",
            "homeSite": "https://example.edu.pl",
            "locationDisplay": "Mokotów",
            "logo": "LOGO_HASH",
            "schoolLong": {
                "id": 123,
                "description": '<p>Opis szkoły <img src="https://example.edu.pl/school.jpg"></p>',
                "sioPublicity": "publiczna",
            },
        },
        "schoolImageHashList": ["PHOTO_HASH"],
        "admissionPointCounts": {
            "456": {
                "limit": 30,
            }
        },
        "admissionPointList": [
            {
                "id": 456,
                "name": "1A [O] mat-fiz-ang (ang-niem)",
                "admissionPointType": {"name": "ogólnodostępny"},
                "blockApply": False,
                "hasCriteria": True,
                "iconList": [
                    {"iconClass": "flag-gb", "description": "język angielski"},
                    {"iconClass": "flag-de", "description": "język niemiecki"},
                ],
                "moduleId": 77,
                "qualificationGroup": "",
                "qualificationGroupId": "",
                "showCriteria": True,
                "admissionPointOffersForPublic": [
                    sample_offer_item(LABEL_CLASS_IDENTIFIER, "1A"),
                    sample_offer_item(LABEL_CLASS_COUNT, "1"),
                    sample_offer_item(LABEL_FIRST_LANGUAGE, "język angielski"),
                    sample_offer_item(LABEL_SECOND_LANGUAGE, "język niemiecki"),
                    sample_offer_item(LABEL_EXTENDED_SUBJECTS, "matematyka, fizyka"),
                    sample_offer_item(
                        LABEL_CLASS_DESCRIPTION,
                        '<p>Opis oddziału <img src="https://example.edu.pl/class.jpg"></p>',
                    ),
                    sample_offer_item(
                        "Pole jeszcze niewykorzystywane", "wartość źródłowa"
                    ),
                    sample_offer_item(
                        LABEL_FILES,
                        "",
                        {
                            "attachmentDataList": [
                                {
                                    "fileName": "zasady.pdf",
                                    "hash": "PDF_HASH",
                                    "contentType": "application/pdf",
                                }
                            ]
                        },
                    ),
                ],
                "slotedForOfferBeans": {
                    "200170": {
                        "key": "subjects",
                        "header": "<b>Przedmioty punktowane</b>",
                        "elements": {
                            "0": {
                                "key": "math",
                                "displayValue": "<span>matematyka</span>",
                            }
                        },
                    }
                },
            }
        ],
        "unexpectedDetailField": {
            "mustStayInRaw": True,
        },
    }


def client_with_fake_session(fail_details=False):
    session = FakeSession(fail_details=fail_details)
    client = PzoOmikronClient(session=session)
    return client, session


def test_client_sends_csrf_header_for_all_endpoints():
    client, session = client_with_fake_session()

    client.get_search_metadata()
    client.search_submit({"schoolTypeId": 4})
    client.school_details(123)

    assert len(session.calls) == 3
    for call in session.calls:
        assert call["headers"]["x-csrf-protection"] == "1"


def test_fetch_offer_snapshot_downloads_metadata_search_results_and_details():
    client, session = client_with_fake_session()

    snapshot = fetch_offer_snapshot(client=client)

    assert snapshot["search_metadata"]["unknownMetadata"] == {"kept": True}
    assert snapshot["search_results"]["4"]["unknownSearchField"] == {"kept": True}
    assert snapshot["school_details"]["123"]["unexpectedDetailField"] == {
        "mustStayInRaw": True
    }
    assert snapshot["manifest"]["school_count"] == 1
    assert snapshot["manifest"]["class_count"] == 1
    assert snapshot["manifest"]["total_seats"] == 30
    assert [call["method"] for call in session.calls] == ["GET", "POST", "POST"]


def test_write_snapshot_files_writes_full_raw_json():
    client, _session = client_with_fake_session()
    snapshot = fetch_offer_snapshot(client=client)
    output_dir = Path("tests") / ".tmp_pzo_omikron_raw"
    if output_dir.exists():
        shutil.rmtree(output_dir)

    try:
        write_snapshot_files(snapshot, output_dir)

        detail_path = output_dir / "school_details" / "123.json"
        detail = json.loads(detail_path.read_text(encoding="utf-8"))
        assert detail == sample_school_detail()

        search_path = output_dir / "search_results" / "school_type_4.json"
        assert (
            json.loads(search_path.read_text(encoding="utf-8"))
            == sample_search_result()
        )
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)


def test_load_snapshot_files_rebuilds_snapshot_from_raw_json():
    client, _session = client_with_fake_session()
    snapshot = fetch_offer_snapshot(client=client)
    output_dir = Path("tests") / ".tmp_pzo_omikron_raw"
    if output_dir.exists():
        shutil.rmtree(output_dir)

    try:
        write_snapshot_files(snapshot, output_dir)
        rebuilt = load_snapshot_files(output_dir)

        assert rebuilt["manifest"]["school_count"] == 1
        assert rebuilt["search_metadata"] == snapshot["search_metadata"]
        assert rebuilt["search_results"] == snapshot["search_results"]
        assert rebuilt["school_details"] == snapshot["school_details"]
        assert rebuilt["search_schools"]["123"]["schoolShort"]["logo"] == "LOGO_HASH"
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)


def test_build_tables_maps_addresses_languages_assets_and_unknown_offer_values():
    client, _session = client_with_fake_session()
    snapshot = fetch_offer_snapshot(client=client)

    tables = build_tables(snapshot)
    school = tables["schools"].iloc[0].to_dict()
    klass = tables["classes"].iloc[0].to_dict()

    assert school["source_school_id"] == "pzo:123"
    assert school["AdresSzkoly"] == "ul. Wiktorska 30/32, 02-587 Warszawa"
    assert school["Dzielnica"] == "Mokotów"
    assert school["SzkolaLat"] == 52.208
    assert school["SzkolaLon"] == 21.012
    assert school["LogoHash"] == "LOGO_HASH"

    assert klass["source_class_id"] == "pzo:456"
    assert klass["LiczbaMiejsc"] == 30
    assert klass["LiczbaOddzialow"] == 1
    assert klass["PierwszyJezykObcy"] == "język angielski"
    assert klass["DrugiJezykObcy"] == "język niemiecki"
    assert klass["JezykiObceIkony"] == "flag-gb, flag-de"
    assert klass["PrzedmiotyRozszerzone"] == "matematyka, fizyka"

    offer_labels = set(tables["offer_values_long"]["label"])
    assert "Pole jeszcze niewykorzystywane" in offer_labels

    asset_kinds = set(tables["assets_manifest"]["asset_kind"])
    assert {
        "school_logo",
        "school_image",
        "class_attachment",
        "description_image_url",
    }.issubset(asset_kinds)
    attachment = tables["assets_manifest"][
        tables["assets_manifest"]["asset_kind"] == "class_attachment"
    ].iloc[0]
    assert attachment["hash"] == "PDF_HASH"
    assert attachment["file_name"] == "zasady.pdf"
    assert attachment["content_type"] == "application/pdf"

    criterion = tables["criteria_long"].iloc[0].to_dict()
    assert criterion["group_header_text"] == "Przedmioty punktowane"
    assert criterion["display_value_text"] == "matematyka"


def test_build_tables_reads_nested_pzo_offer_labels_and_trimmed_values():
    client, _session = client_with_fake_session()
    snapshot = fetch_offer_snapshot(client=client)
    offers = snapshot["school_details"]["123"]["admissionPointList"][0][
        "admissionPointOffersForPublic"
    ]
    for item in offers:
        label = item.pop("label")
        offer_type = item.pop("type")
        item["offer"] = {
            "publicDisplayLabel": label,
            "offerType": offer_type,
        }
        item["trimmedOfferValue"] = item["offerValue"]
    offers[4]["offerValue"] = "ta wartość nie powinna wygrać"
    offers[4]["trimmedOfferValue"] = "matematyka, fizyka"

    tables = build_tables(snapshot)
    klass = tables["classes"].iloc[0].to_dict()

    assert klass["PrzedmiotyRozszerzone"] == "matematyka, fizyka"
    assert klass["PierwszyJezykObcy"] == "język angielski"
    assert klass["OpisOddzialuText"] == "Opis oddziału"
    assert "Pole jeszcze niewykorzystywane" in set(tables["offer_values_long"]["label"])


def test_fetch_offer_snapshot_fails_when_school_details_fails():
    client, _session = client_with_fake_session(fail_details=True)

    with pytest.raises(RuntimeError, match="schoolDetails"):
        fetch_offer_snapshot(client=client)
