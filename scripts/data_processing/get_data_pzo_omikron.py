"""Downloader i parser publicznej oferty PZO/Omikron.

Skrypt zapisuje pełne odpowiedzi JSON jako źródło prawdy, buduje z nich roboczy
skoroszyt analityczny i udostępnia tabele wykorzystywane przez pipeline 2026.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_BASE_URL = "https://rekrutacje-warszawa.pzo.edu.pl"
DEFAULT_PUBLIC_CONTEXT = "/omikron-public"
DEFAULT_SCHOOL_YEAR = "2026/2027"
SCHEMA_VERSION = "1.0"
EXCEL_CELL_LIMIT = 32767
EXCEL_TRUNCATION_SUFFIX = " [ucieto w Excelu; pelna wartosc jest w raw JSON]"

SEARCH_METADATA_PATH = "/api/offer/search"
SEARCH_SUBMIT_PATH = "/api/offer/searchSubmit"
SCHOOL_DETAILS_PATH = "/api/offer/schoolDetails"

LABEL_CLASS_IDENTIFIER = "Identyfikator oddziału/grupy rekrutacyjnej"
LABEL_CLASS_COUNT = "Liczba oddziałów"
LABEL_FIRST_LANGUAGE = "Pierwszy język obcy"
LABEL_SECOND_LANGUAGE = "Drugi język obcy"
LABEL_EXTENDED_SUBJECTS = "Przedmioty rozszerzone"
LABEL_CLASS_DESCRIPTION = "Dodatkowe informacje o grupie rekrutacyjnej"
LABEL_PROFESSION = "Zawód"
LABEL_SPORT_DISCIPLINE = "Dyscyplina sportowa"
LABEL_FILES = "Pliki do pobrania"


JsonDict = dict[str, Any]


@dataclass(frozen=True)
class EndpointConfig:
    """Konfiguracja adresów publicznego API PZO."""

    base_url: str = DEFAULT_BASE_URL
    public_context: str = DEFAULT_PUBLIC_CONTEXT

    def url(self, path: str) -> str:
        context = self.public_context.strip("/")
        api_path = path.lstrip("/")
        return urljoin(self.base_url.rstrip("/") + "/", f"{context}/{api_path}")


class PzoOmikronClient:
    """Minimalny klient publicznych endpointów oferty PZO/Omikron."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        public_context: str = DEFAULT_PUBLIC_CONTEXT,
        session: requests.Session | None = None,
        timeout: int = 60,
    ) -> None:
        self.endpoints = EndpointConfig(
            base_url=base_url, public_context=public_context
        )
        self.session = session or requests.Session()
        self.timeout = timeout

    def _headers(self, method: str) -> dict[str, str]:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "x-csrf-protection": "1",
        }
        if method.upper() == "POST":
            headers["Content-Type"] = "application/json"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        payload: JsonDict | None = None,
    ) -> Any:
        url = self.endpoints.url(path)
        response = self.session.request(
            method,
            url,
            headers=self._headers(method),
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_search_metadata(self) -> JsonDict:
        return self._request("GET", SEARCH_METADATA_PATH)

    def search_submit(self, payload: JsonDict) -> Any:
        return self._request("POST", SEARCH_SUBMIT_PATH, payload)

    def school_details(
        self,
        school_id: int | str,
        no_recrutation: bool = False,
        other_recrutation: bool = False,
    ) -> JsonDict:
        payload = {
            "schoolId": int(school_id),
            "noRecrutation": no_recrutation,
            "otherRecrutation": other_recrutation,
        }
        return self._request("POST", SCHOOL_DETAILS_PATH, payload)


def school_year_slug(school_year: str) -> str:
    return re.sub(r"[^0-9]+", "_", school_year).strip("_")


def default_raw_dir(year: int, school_year: str = DEFAULT_SCHOOL_YEAR) -> Path:
    return (
        BASE_DIR
        / "data"
        / "raw"
        / str(year)
        / f"pzo_omikron_{school_year_slug(school_year)}"
    )


def default_output_xlsx(school_year: str = DEFAULT_SCHOOL_YEAR) -> Path:
    return (
        BASE_DIR
        / "results"
        / "processed"
        / f"pzo_omikron_{school_year_slug(school_year)}.xlsx"
    )


def default_search_payload(school_type_id: int | None = None) -> JsonDict:
    payload: JsonDict = {
        "noRecrutation": False,
        "otherRecrutation": False,
        "freePlaces": False,
        "recrutationModule": True,
        "offerMap": {},
        "connective": {},
        "chosenOperatorMap": {},
    }
    if school_type_id is not None:
        payload["schoolTypeId"] = int(school_type_id)
    return payload


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def html_to_text(value: Any) -> str:
    if value is None:
        return ""
    soup = BeautifulSoup(str(value), "html.parser")
    text = soup.get_text(" ", strip=True)
    text = text.replace("Text-editor", " ")
    return clean_text(text)


def extract_image_sources(value: Any) -> list[str]:
    if not value:
        return []
    soup = BeautifulSoup(str(value), "html.parser")
    sources: list[str] = []
    for tag in soup.find_all("img"):
        src = tag.get("src")
        if src:
            sources.append(str(src))
    return sources


def first_present(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def get_nested(data: JsonDict | None, *path: str, default: Any = None) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def extract_school_type_id(type_item: JsonDict) -> int | None:
    for key in ("id", "schoolTypeId", "key", "value"):
        value = type_item.get(key)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    return None


def extract_school_type_name(type_item: JsonDict) -> str:
    return clean_text(
        first_present(
            type_item.get("name"),
            type_item.get("description"),
            type_item.get("label"),
            type_item.get("text"),
            type_item.get("value"),
        )
    )


def school_kind_from_name(value: Any) -> str:
    name = clean_text(value).lower()
    if "technik" in name:
        return "technikum"
    if "branż" in name or "branz" in name:
        return "branżowa"
    if "lice" in name:
        return "liceum"
    return clean_text(value)


def parse_int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def extract_search_school_items(search_result: Any) -> list[JsonDict]:
    """Wyciąga listę szkół z odpowiedzi searchSubmit niezależnie od opakowania."""
    if isinstance(search_result, list):
        return [item for item in search_result if isinstance(item, dict)]
    if not isinstance(search_result, dict):
        return []

    direct_keys = (
        "schoolList",
        "schoolOfferList",
        "schoolOfferListForPublic",
        "offerList",
        "results",
        "result",
        "data",
    )
    for key in direct_keys:
        value = search_result.get(key)
        if isinstance(value, list) and any(isinstance(item, dict) for item in value):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = extract_search_school_items(value)
            if nested:
                return nested

    for value in search_result.values():
        if isinstance(value, list) and any(
            isinstance(item, dict) and "schoolShort" in item for item in value
        ):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = extract_search_school_items(value)
            if nested:
                return nested
    return []


def search_school_id(item: JsonDict) -> int | None:
    value = get_nested(item, "schoolShort", "id")
    if value is None:
        value = first_present(item.get("schoolId"), item.get("id"))
    return parse_int_or_none(value)


def detail_school_id(detail: JsonDict) -> int | None:
    value = get_nested(detail, "schoolOffer", "schoolLong", "id")
    if value is None:
        value = get_nested(detail, "schoolOffer", "schoolShort", "id")
    if value is None:
        value = get_nested(detail, "schoolOffer", "id")
    return parse_int_or_none(value)


def admission_points(detail: JsonDict) -> list[JsonDict]:
    value = detail.get("admissionPointList")
    return value if isinstance(value, list) else []


def count_classes(details: dict[str, JsonDict]) -> int:
    return sum(len(admission_points(detail)) for detail in details.values())


def count_seats(details: dict[str, JsonDict]) -> int:
    total = 0
    for detail in details.values():
        counts = detail.get("admissionPointCounts") or {}
        if not isinstance(counts, dict):
            continue
        for count_data in counts.values():
            if isinstance(count_data, dict):
                limit = count_data.get("limit")
                if isinstance(limit, (int, float)):
                    total += int(limit)
    return total


def fetch_offer_snapshot(
    client: PzoOmikronClient,
    year: int = 2026,
    school_year: str = DEFAULT_SCHOOL_YEAR,
    school_type_ids: list[int] | None = None,
    limit_schools: int | None = None,
    delay: float = 0.0,
) -> JsonDict:
    """Pobiera metadane, wyniki wyszukiwania typów szkół i szczegóły szkół."""
    metadata = client.get_search_metadata()
    school_type_list = metadata.get("schoolTypeList") or []
    type_map: dict[int, str] = {}
    for item in school_type_list:
        if not isinstance(item, dict):
            continue
        type_id = extract_school_type_id(item)
        if type_id is not None:
            type_map[type_id] = extract_school_type_name(item)

    selected_type_ids = school_type_ids or list(type_map)
    if not selected_type_ids:
        raise ValueError("Brak typów szkół w schoolTypeList i brak --school-type-id.")

    search_results: dict[str, Any] = {}
    search_payloads: dict[str, JsonDict] = {}
    schools_by_id: dict[str, JsonDict] = {}
    type_ids_by_school: dict[str, list[int]] = {}

    for school_type_id in selected_type_ids:
        payload = default_search_payload(school_type_id)
        search_payloads[str(school_type_id)] = payload
        logger.info("Pobieranie listy szkół dla typu %s", school_type_id)
        result = client.search_submit(payload)
        search_results[str(school_type_id)] = result
        for item in extract_search_school_items(result):
            school_id = search_school_id(item)
            if school_id is None:
                continue
            school_key = str(school_id)
            schools_by_id.setdefault(school_key, item)
            type_ids_by_school.setdefault(school_key, [])
            if school_type_id not in type_ids_by_school[school_key]:
                type_ids_by_school[school_key].append(int(school_type_id))

    school_ids = [int(key) for key in schools_by_id]
    school_ids.sort()
    if limit_schools is not None:
        school_ids = school_ids[:limit_schools]

    details: dict[str, JsonDict] = {}
    failed_details: list[dict[str, str]] = []
    for index, school_id in enumerate(school_ids, start=1):
        logger.info(
            "Pobieranie szczegółów szkoły %s (%s/%s)", school_id, index, len(school_ids)
        )
        try:
            details[str(school_id)] = client.school_details(school_id)
        except (
            ValueError,
            requests.RequestException,
            json.JSONDecodeError,
        ) as exc:
            failed_details.append({"school_id": str(school_id), "error": str(exc)})
        if delay > 0:
            time.sleep(delay)

    if failed_details:
        raise RuntimeError(
            "Nie pobrano pełnego snapshotu schoolDetails: "
            + json.dumps(failed_details, ensure_ascii=False)
        )

    selected_type_names = {
        str(type_id): type_map.get(type_id, str(type_id))
        for type_id in selected_type_ids
    }
    manifest: JsonDict = {
        "schema_version": SCHEMA_VERSION,
        "source": "pzo_omikron_public",
        "base_url": client.endpoints.base_url,
        "public_context": client.endpoints.public_context,
        "endpoints": {
            "search": client.endpoints.url(SEARCH_METADATA_PATH),
            "searchSubmit": client.endpoints.url(SEARCH_SUBMIT_PATH),
            "schoolDetails": client.endpoints.url(SCHOOL_DETAILS_PATH),
        },
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "year": year,
        "school_year": school_year,
        "school_type_ids": selected_type_ids,
        "school_type_names": selected_type_names,
        "school_type_count": len(selected_type_ids),
        "school_count": len(school_ids),
        "school_detail_count": len(details),
        "class_count": count_classes(details),
        "total_seats": count_seats(details),
        "limit_schools": limit_schools,
        "search_payloads": search_payloads,
        "type_ids_by_school": type_ids_by_school,
    }

    return {
        "manifest": manifest,
        "search_metadata": metadata,
        "search_results": search_results,
        "school_details": details,
        "search_schools": {key: schools_by_id[key] for key in map(str, school_ids)},
        "type_ids_by_school": type_ids_by_school,
    }


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_snapshot_files(snapshot: JsonDict, raw_dir: Path) -> None:
    """Zapisuje pełny snapshot w kontrakcie katalogów raw."""
    write_json(raw_dir / "search_metadata.json", snapshot["search_metadata"])
    for school_type_id, result in snapshot["search_results"].items():
        write_json(
            raw_dir / "search_results" / f"school_type_{school_type_id}.json", result
        )
    for school_id, detail in snapshot["school_details"].items():
        write_json(raw_dir / "school_details" / f"{school_id}.json", detail)
    write_json(raw_dir / "manifest.json", snapshot["manifest"])


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_snapshot_files(raw_dir: Path) -> JsonDict:
    """Odtwarza snapshot z katalogu raw, żeby regenerować tabele bez sieci."""
    manifest = read_json(raw_dir / "manifest.json")
    search_metadata = read_json(raw_dir / "search_metadata.json")

    search_results: dict[str, Any] = {}
    for path in sorted((raw_dir / "search_results").glob("school_type_*.json")):
        school_type_id = path.stem.replace("school_type_", "")
        search_results[school_type_id] = read_json(path)

    school_details: dict[str, JsonDict] = {}
    for path in sorted((raw_dir / "school_details").glob("*.json")):
        school_details[path.stem] = read_json(path)

    search_schools: dict[str, JsonDict] = {}
    rebuilt_type_ids_by_school: dict[str, list[int]] = {}
    for school_type_id, result in search_results.items():
        for item in extract_search_school_items(result):
            school_id = search_school_id(item)
            if school_id is None:
                continue
            school_key = str(school_id)
            if school_key not in school_details:
                continue
            search_schools.setdefault(school_key, item)
            rebuilt_type_ids_by_school.setdefault(school_key, [])
            numeric_type_id = parse_int_or_none(school_type_id)
            if numeric_type_id is None:
                continue
            if numeric_type_id not in rebuilt_type_ids_by_school[school_key]:
                rebuilt_type_ids_by_school[school_key].append(numeric_type_id)

    return {
        "manifest": manifest,
        "search_metadata": search_metadata,
        "search_results": search_results,
        "school_details": school_details,
        "search_schools": search_schools,
        "type_ids_by_school": manifest.get("type_ids_by_school")
        or rebuilt_type_ids_by_school,
    }


def compact_json_cell(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if value is None:
        return ""
    return str(value)


def address_to_text(address: JsonDict | None) -> str:
    if not isinstance(address, dict):
        return ""
    street = clean_text(address.get("street"))
    house = clean_text(address.get("house"))
    flat = clean_text(address.get("flat"))
    number = house
    if flat:
        number = f"{house}/{flat}" if house else flat
    zipcode = clean_text(address.get("zipcode"))
    city = clean_text(address.get("city"))
    street_part = " ".join(part for part in (street, number) if part)
    city_part = " ".join(part for part in (zipcode, city) if part)
    return ", ".join(part for part in (street_part, city_part) if part)


def get_school_offer(detail: JsonDict) -> JsonDict:
    offer = detail.get("schoolOffer")
    return offer if isinstance(offer, dict) else {}


def get_school_address(search_item: JsonDict | None, detail: JsonDict) -> JsonDict:
    address = get_school_offer(detail).get("address")
    if isinstance(address, dict):
        return address
    if isinstance(search_item, dict) and isinstance(search_item.get("address"), dict):
        return search_item["address"]
    return {}


def get_school_name(search_item: JsonDict | None, detail: JsonDict) -> str:
    offer = get_school_offer(detail)
    return clean_text(
        first_present(
            offer.get("fullName"),
            get_nested(search_item, "schoolShort", "name") if search_item else None,
            offer.get("name"),
        )
    )


def get_short_school_name(search_item: JsonDict | None, detail: JsonDict) -> str:
    return clean_text(
        first_present(
            get_nested(search_item, "schoolShort", "name") if search_item else None,
            get_school_offer(detail).get("name"),
            get_school_name(search_item, detail),
        )
    )


def get_school_coords(
    search_item: JsonDict | None, detail: JsonDict
) -> tuple[Any, Any]:
    latitude = first_present(
        get_nested(search_item, "schoolShort", "latitude") if search_item else None,
        get_nested(detail, "schoolOffer", "schoolShort", "latitude"),
        get_nested(detail, "schoolOffer", "latitude"),
    )
    longitude = first_present(
        get_nested(search_item, "schoolShort", "longitude") if search_item else None,
        get_nested(detail, "schoolOffer", "schoolShort", "longitude"),
        get_nested(detail, "schoolOffer", "longitude"),
    )
    return latitude, longitude


def get_school_logo(search_item: JsonDict | None, detail: JsonDict) -> str:
    return clean_text(
        first_present(
            get_nested(search_item, "schoolShort", "logo") if search_item else None,
            get_school_offer(detail).get("logo"),
        )
    )


def school_type_info(snapshot: JsonDict, school_id: str) -> tuple[str, str, str]:
    type_ids = snapshot.get("type_ids_by_school", {}).get(school_id, [])
    manifest_names = snapshot.get("manifest", {}).get("school_type_names", {})
    type_names = [
        manifest_names.get(str(type_id), str(type_id)) for type_id in type_ids
    ]
    return (
        ",".join(str(type_id) for type_id in type_ids),
        " | ".join(type_names),
        school_kind_from_name(type_names[0]) if type_names else "",
    )


def offer_items_by_label(admission_point: JsonDict) -> dict[str, list[JsonDict]]:
    result: dict[str, list[JsonDict]] = {}
    for item in admission_point.get("admissionPointOffersForPublic") or []:
        if not isinstance(item, dict):
            continue
        label = offer_item_label(item)
        if label:
            result.setdefault(label, []).append(item)
    return result


def offer_item_metadata(item: JsonDict | None) -> JsonDict:
    if not isinstance(item, dict):
        return {}
    offer = item.get("offer")
    return offer if isinstance(offer, dict) else {}


def offer_item_label(item: JsonDict | None) -> str:
    offer = offer_item_metadata(item)
    return clean_text(
        first_present(
            item.get("label") if isinstance(item, dict) else None,
            item.get("name") if isinstance(item, dict) else None,
            item.get("key") if isinstance(item, dict) else None,
            offer.get("publicDisplayLabel"),
            offer.get("displayLabel"),
            offer.get("label"),
            offer.get("name"),
        )
    )


def offer_item_type(item: JsonDict | None) -> str:
    offer = offer_item_metadata(item)
    return clean_text(
        first_present(
            item.get("type") if isinstance(item, dict) else None,
            item.get("offerType") if isinstance(item, dict) else None,
            offer.get("offerType"),
            offer.get("type"),
        )
    )


def offer_item_value(item: JsonDict | None) -> Any:
    if not isinstance(item, dict):
        return ""
    return first_present(
        item.get("trimmedOfferValue"),
        item.get("offerValue"),
        item.get("value"),
        item.get("displayValue"),
        item.get("text"),
        item.get("description"),
    )


def first_offer_value(items_by_label: dict[str, list[JsonDict]], label: str) -> str:
    items = items_by_label.get(label) or []
    if not items:
        return ""
    value = offer_item_value(items[0])
    return html_to_text(value) if looks_like_html(value) else clean_text(value)


def first_offer_html(items_by_label: dict[str, list[JsonDict]], label: str) -> str:
    items = items_by_label.get(label) or []
    if not items:
        return ""
    return clean_text(offer_item_value(items[0]))


def looks_like_html(value: Any) -> bool:
    text = str(value or "")
    return "<" in text and ">" in text


def parse_number(value: Any) -> Any:
    text = clean_text(value)
    if not text:
        return ""
    text = text.replace(",", ".")
    try:
        number = float(text)
    except ValueError:
        return value
    return int(number) if number.is_integer() else number


def admission_point_count(detail: JsonDict, admission_point_id: Any) -> JsonDict:
    counts = detail.get("admissionPointCounts") or {}
    if not isinstance(counts, dict):
        return {}
    value = counts.get(str(admission_point_id))
    if value is None:
        value = counts.get(admission_point_id)
    return value if isinstance(value, dict) else {}


def icon_summary(icon_list: Any) -> tuple[str, str]:
    if not isinstance(icon_list, list):
        return "", ""
    classes = []
    descriptions = []
    for icon in icon_list:
        if not isinstance(icon, dict):
            continue
        icon_class = clean_text(icon.get("iconClass"))
        description = clean_text(icon.get("description"))
        if icon_class:
            classes.append(icon_class)
        if description:
            descriptions.append(description)
    return ", ".join(classes), ", ".join(descriptions)


def joined_languages(first_language: str, second_language: str) -> str:
    return ", ".join(
        language
        for language in (clean_text(first_language), clean_text(second_language))
        if language
    )


def class_type_name(admission_point: JsonDict) -> str:
    admission_type = admission_point.get("admissionPointType")
    if isinstance(admission_type, dict):
        return clean_text(
            first_present(
                admission_type.get("name"),
                admission_type.get("description"),
                admission_type.get("label"),
            )
        )
    return clean_text(admission_type)


def raw_offer_value_for_long(item: JsonDict) -> Any:
    return first_present(
        item.get("trimmedOfferValue"),
        item.get("offerValue"),
        item.get("displayValue"),
        item.get("value"),
        item.get("text"),
        item.get("description"),
    )


def offer_value_text(value: Any) -> str:
    return html_to_text(value) if looks_like_html(value) else clean_text(value)


def parse_json_if_possible(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text or text[0] not in "[{":
        return value
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def iter_attachment_metadata(item: JsonDict) -> list[JsonDict]:
    attachments = item.get("attachmentDataList")
    if not isinstance(attachments, list):
        parsed = parse_json_if_possible(item.get("offerValue"))
        if isinstance(parsed, dict):
            attachments = parsed.get("attachmentDataList") or parsed.get("attachments")
        elif isinstance(parsed, list):
            attachments = parsed
    if not isinstance(attachments, list):
        return []
    return [attachment for attachment in attachments if isinstance(attachment, dict)]


def attachment_name(attachment: JsonDict) -> str:
    return clean_text(
        first_present(
            attachment.get("fileName"),
            attachment.get("filename"),
            attachment.get("name"),
            attachment.get("originalFileName"),
        )
    )


def attachment_hash(attachment: JsonDict) -> str:
    return clean_text(
        first_present(
            attachment.get("hash"),
            attachment.get("fileHash"),
            attachment.get("contentHash"),
            attachment.get("uuid"),
            attachment.get("id"),
        )
    )


def attachment_content_type(attachment: JsonDict) -> str:
    return clean_text(
        first_present(
            attachment.get("contentType"),
            attachment.get("mimeType"),
            attachment.get("type"),
        )
    )


def iter_criteria_rows(
    school_id: str, class_id: str, admission_point: JsonDict
) -> list[JsonDict]:
    rows: list[JsonDict] = []
    beans = admission_point.get("slotedForOfferBeans") or []
    if isinstance(beans, dict):
        group_items = list(beans.items())
    elif isinstance(beans, list):
        group_items = [(str(index), group) for index, group in enumerate(beans)]
    else:
        return rows

    for group_index, (source_group_key, group) in enumerate(group_items):
        if not isinstance(group, dict):
            continue
        header_value = first_present(
            group.get("header"), group.get("label"), group.get("name")
        )
        candidates = first_present(
            group.get("beans"),
            group.get("elements"),
            group.get("items"),
            group.get("values"),
            group.get("children"),
        )
        if isinstance(candidates, dict):
            candidate_items = list(candidates.items())
        elif isinstance(candidates, list):
            candidate_items = [
                (str(index), element) for index, element in enumerate(candidates)
            ]
        else:
            candidate_items = []
        if not candidate_items:
            candidate_items = [(str(source_group_key), group)]
        for element_index, (source_element_key, element) in enumerate(candidate_items):
            if not isinstance(element, dict):
                continue
            display_value = first_present(
                element.get("displayValue"),
                element.get("value"),
                element.get("label"),
                element.get("name"),
                element.get("text"),
            )
            rows.append(
                {
                    "source_school_id": f"pzo:{school_id}",
                    "source_class_id": f"pzo:{class_id}" if class_id else "",
                    "pzo_school_id": school_id,
                    "pzo_admission_point_id": class_id,
                    "group_index": group_index,
                    "group_key": clean_text(
                        first_present(
                            source_group_key,
                            group.get("key"),
                            group.get("id"),
                            group.get("name"),
                        )
                    ),
                    "group_header_html": clean_text(header_value),
                    "group_header_text": html_to_text(header_value),
                    "element_index": element_index,
                    "element_key": clean_text(
                        first_present(
                            source_element_key,
                            element.get("key"),
                            element.get("id"),
                            element.get("name"),
                        )
                    ),
                    "display_value_html": clean_text(display_value),
                    "display_value_text": offer_value_text(display_value),
                    "raw_json": element,
                }
            )
    return rows


def build_tables(snapshot: JsonDict) -> dict[str, pd.DataFrame]:
    """Buduje robocze tabele z raw JSON bez ponownego pobierania danych."""
    schools_rows: list[JsonDict] = []
    classes_rows: list[JsonDict] = []
    offer_rows: list[JsonDict] = []
    criteria_rows: list[JsonDict] = []
    assets_rows: list[JsonDict] = []

    for school_id, detail in sorted(
        snapshot["school_details"].items(), key=lambda item: int(item[0])
    ):
        search_item = snapshot.get("search_schools", {}).get(school_id)
        school_offer = get_school_offer(detail)
        school_long = (
            school_offer.get("schoolLong") if isinstance(school_offer, dict) else {}
        )
        school_long = school_long if isinstance(school_long, dict) else {}
        address = get_school_address(search_item, detail)
        latitude, longitude = get_school_coords(search_item, detail)
        type_ids, type_names, school_kind = school_type_info(snapshot, school_id)
        school_name = get_school_name(search_item, detail)
        short_name = get_short_school_name(search_item, detail)
        logo_hash = get_school_logo(search_item, detail)
        description_html = clean_text(school_long.get("description"))

        schools_rows.append(
            {
                "source_school_id": f"pzo:{school_id}",
                "pzo_school_id": school_id,
                "pzo_school_type_ids": type_ids,
                "pzo_school_type_names": type_names,
                "TypSzkoly": school_kind,
                "NazwaSzkoly": school_name,
                "NazwaJednostki": short_name,
                "AdresSzkoly": address_to_text(address),
                "Ulica": clean_text(address.get("street")),
                "NumerBudynku": clean_text(address.get("house")),
                "NumerLokalu": clean_text(address.get("flat")),
                "Kod": clean_text(address.get("zipcode")),
                "Miasto": clean_text(address.get("city")),
                "Poczta": clean_text(address.get("post")),
                "Dzielnica": clean_text(school_offer.get("locationDisplay")),
                "Telefon": clean_text(address.get("phone")),
                "Email": clean_text(school_offer.get("email")),
                "WWW": clean_text(school_offer.get("homeSite")),
                "SzkolaLat": latitude,
                "SzkolaLon": longitude,
                "latitude": latitude,
                "longitude": longitude,
                "LogoHash": logo_hash,
                "Dyrektor": clean_text(school_offer.get("headMaster")),
                "OpisSzkolyHtml": description_html,
                "OpisSzkolyText": html_to_text(description_html),
                "SioPublicity": clean_text(school_long.get("sioPublicity")),
            }
        )

        if logo_hash:
            assets_rows.append(
                {
                    "source_school_id": f"pzo:{school_id}",
                    "source_class_id": "",
                    "pzo_school_id": school_id,
                    "pzo_admission_point_id": "",
                    "asset_kind": "school_logo",
                    "hash": logo_hash,
                    "file_name": "",
                    "content_type": "",
                    "url": "",
                    "label": "logo",
                    "raw_json": {"logo": logo_hash},
                }
            )
        for image_hash in detail.get("schoolImageHashList") or []:
            assets_rows.append(
                {
                    "source_school_id": f"pzo:{school_id}",
                    "source_class_id": "",
                    "pzo_school_id": school_id,
                    "pzo_admission_point_id": "",
                    "asset_kind": "school_image",
                    "hash": clean_text(image_hash),
                    "file_name": "",
                    "content_type": "",
                    "url": "",
                    "label": "schoolImageHashList",
                    "raw_json": {"hash": image_hash},
                }
            )
        for image_src in extract_image_sources(description_html):
            assets_rows.append(
                {
                    "source_school_id": f"pzo:{school_id}",
                    "source_class_id": "",
                    "pzo_school_id": school_id,
                    "pzo_admission_point_id": "",
                    "asset_kind": "description_image_url",
                    "hash": "",
                    "file_name": "",
                    "content_type": "",
                    "url": image_src,
                    "label": "OpisSzkolyHtml",
                    "raw_json": {"src": image_src},
                }
            )

        for admission_point in admission_points(detail):
            class_id = clean_text(admission_point.get("id"))
            offers = offer_items_by_label(admission_point)
            count_data = admission_point_count(detail, admission_point.get("id"))
            first_language = first_offer_value(offers, LABEL_FIRST_LANGUAGE)
            second_language = first_offer_value(offers, LABEL_SECOND_LANGUAGE)
            icon_classes, icon_descriptions = icon_summary(
                admission_point.get("iconList")
            )
            class_description_html = first_offer_html(offers, LABEL_CLASS_DESCRIPTION)

            classes_rows.append(
                {
                    "source_school_id": f"pzo:{school_id}",
                    "source_class_id": f"pzo:{class_id}" if class_id else "",
                    "pzo_school_id": school_id,
                    "pzo_admission_point_id": class_id,
                    "IdSzkoly": school_id,
                    "IdOddzialu": class_id,
                    "NazwaSzkoly": school_name,
                    "TypSzkoly": school_kind,
                    "AdresSzkoly": address_to_text(address),
                    "Dzielnica": clean_text(school_offer.get("locationDisplay")),
                    "OddzialNazwa": clean_text(admission_point.get("name")),
                    "OddzialNazwaPzo": clean_text(admission_point.get("name")),
                    "OddzialKod": first_offer_value(offers, LABEL_CLASS_IDENTIFIER),
                    "TypOddzialu": class_type_name(admission_point),
                    "TypOddzialuPzo": class_type_name(admission_point),
                    "LiczbaOddzialow": parse_number(
                        first_offer_value(offers, LABEL_CLASS_COUNT)
                    ),
                    "LiczbaMiejsc": count_data.get("limit", ""),
                    "PrzedmiotyRozszerzone": first_offer_value(
                        offers, LABEL_EXTENDED_SUBJECTS
                    ),
                    "PierwszyJezykObcy": first_language,
                    "DrugiJezykObcy": second_language,
                    "JezykiObce": joined_languages(first_language, second_language),
                    "JezykiObceIkony": icon_classes,
                    "JezykiObceIkonyOpis": icon_descriptions,
                    "Zawod": first_offer_value(offers, LABEL_PROFESSION),
                    "DyscyplinaSportowa": first_offer_value(
                        offers, LABEL_SPORT_DISCIPLINE
                    ),
                    "OpisOddzialuHtml": class_description_html,
                    "OpisOddzialuText": html_to_text(class_description_html),
                    "QualificationGroup": clean_text(
                        admission_point.get("qualificationGroup")
                    ),
                    "QualificationGroupId": clean_text(
                        admission_point.get("qualificationGroupId")
                    ),
                    "ModuleId": clean_text(admission_point.get("moduleId")),
                    "BlockApply": admission_point.get("blockApply"),
                    "HasCriteria": admission_point.get("hasCriteria"),
                    "ShowCriteria": admission_point.get("showCriteria"),
                    "UrlGrupy": "",
                    "SzkolaLat": latitude,
                    "SzkolaLon": longitude,
                    "latitude": latitude,
                    "longitude": longitude,
                }
            )

            for order, item in enumerate(
                admission_point.get("admissionPointOffersForPublic") or []
            ):
                if not isinstance(item, dict):
                    continue
                raw_value = raw_offer_value_for_long(item)
                label = offer_item_label(item)
                attachments = iter_attachment_metadata(item)
                offer_rows.append(
                    {
                        "source_school_id": f"pzo:{school_id}",
                        "source_class_id": f"pzo:{class_id}" if class_id else "",
                        "pzo_school_id": school_id,
                        "pzo_admission_point_id": class_id,
                        "offer_order": order,
                        "offer_id": clean_text(item.get("id")),
                        "label": label,
                        "type": offer_item_type(item),
                        "value_text": offer_value_text(raw_value),
                        "value_raw": raw_value,
                        "attachment_count": len(attachments),
                        "raw_json": item,
                    }
                )
                for attachment in attachments:
                    assets_rows.append(
                        {
                            "source_school_id": f"pzo:{school_id}",
                            "source_class_id": f"pzo:{class_id}" if class_id else "",
                            "pzo_school_id": school_id,
                            "pzo_admission_point_id": class_id,
                            "asset_kind": "class_attachment",
                            "hash": attachment_hash(attachment),
                            "file_name": attachment_name(attachment),
                            "content_type": attachment_content_type(attachment),
                            "url": clean_text(attachment.get("url")),
                            "label": label or LABEL_FILES,
                            "raw_json": attachment,
                        }
                    )
                for image_src in extract_image_sources(raw_value):
                    assets_rows.append(
                        {
                            "source_school_id": f"pzo:{school_id}",
                            "source_class_id": f"pzo:{class_id}" if class_id else "",
                            "pzo_school_id": school_id,
                            "pzo_admission_point_id": class_id,
                            "asset_kind": "description_image_url",
                            "hash": "",
                            "file_name": "",
                            "content_type": "",
                            "url": image_src,
                            "label": label,
                            "raw_json": {"src": image_src},
                        }
                    )

            criteria_rows.extend(
                iter_criteria_rows(school_id, class_id, admission_point)
            )

    tables = {
        "schools": pd.DataFrame(schools_rows),
        "classes": pd.DataFrame(classes_rows),
        "offer_values_long": pd.DataFrame(offer_rows),
        "criteria_long": pd.DataFrame(criteria_rows),
        "assets_manifest": pd.DataFrame(assets_rows),
        "download_manifest": manifest_dataframe(snapshot["manifest"]),
    }
    return tables


def manifest_dataframe(manifest: JsonDict) -> pd.DataFrame:
    rows = []
    for key, value in manifest.items():
        rows.append(
            {
                "key": key,
                "value": compact_json_cell(value),
            }
        )
    return pd.DataFrame(rows)


def excel_safe_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    if len(value) <= EXCEL_CELL_LIMIT:
        return value
    max_length = EXCEL_CELL_LIMIT - len(EXCEL_TRUNCATION_SUFFIX)
    return value[:max_length] + EXCEL_TRUNCATION_SUFFIX


def dataframe_for_output(df: pd.DataFrame, excel: bool = False) -> pd.DataFrame:
    output = df.copy()
    for column in output.columns:
        if output[column].map(lambda value: isinstance(value, (dict, list))).any():
            output[column] = output[column].map(compact_json_cell)
        if excel and output[column].dtype == "object":
            output[column] = output[column].map(excel_safe_value)
    return output


def write_tables(
    tables: dict[str, pd.DataFrame],
    output_xlsx: Path,
    csv_dir: Path | None = None,
) -> None:
    output_xlsx.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_xlsx, engine="openpyxl") as writer:
        for sheet_name, df in tables.items():
            dataframe_for_output(df, excel=True).to_excel(
                writer, sheet_name=sheet_name[:31], index=False
            )

    if csv_dir is not None:
        csv_dir.mkdir(parents=True, exist_ok=True)
        for name, df in tables.items():
            dataframe_for_output(df).to_csv(
                csv_dir / f"{name}.csv", index=False, encoding="utf-8-sig"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pobierz publiczny snapshot oferty PZO/Omikron i zapisz JSON + Excel."
    )
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--school-year", default=DEFAULT_SCHOOL_YEAR)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--public-context", default=DEFAULT_PUBLIC_CONTEXT)
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--output-xlsx", type=Path)
    parser.add_argument("--csv-dir", type=Path)
    parser.add_argument(
        "--school-type-id", type=int, action="append", dest="school_type_ids"
    )
    parser.add_argument("--limit-schools", type=int)
    parser.add_argument("--delay", type=float, default=0.0)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument(
        "--from-raw",
        action="store_true",
        help="Nie pobieraj danych z sieci; zbuduj Excel/CSV z istniejącego katalogu raw.",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    args = parse_args()
    raw_dir = args.raw_dir or default_raw_dir(args.year, args.school_year)
    output_xlsx = args.output_xlsx or default_output_xlsx(args.school_year)

    if args.from_raw:
        logger.info("Odtwarzanie snapshotu z raw JSON: %s", raw_dir)
        snapshot = load_snapshot_files(raw_dir)
    else:
        client = PzoOmikronClient(
            base_url=args.base_url,
            public_context=args.public_context,
            timeout=args.timeout,
        )
        snapshot = fetch_offer_snapshot(
            client=client,
            year=args.year,
            school_year=args.school_year,
            school_type_ids=args.school_type_ids,
            limit_schools=args.limit_schools,
            delay=args.delay,
        )
        write_snapshot_files(snapshot, raw_dir)
    tables = build_tables(snapshot)
    write_tables(tables, output_xlsx, args.csv_dir)

    manifest = snapshot["manifest"]
    logger.info(
        "Zapisano snapshot: %s szkół, %s oddziałów, %s miejsc",
        manifest["school_count"],
        manifest["class_count"],
        manifest["total_seats"],
    )
    logger.info("Raw JSON: %s", raw_dir)
    logger.info("Excel: %s", output_xlsx)


if __name__ == "__main__":
    main()
