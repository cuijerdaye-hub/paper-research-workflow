#!/usr/bin/env python3
"""Merge and deduplicate structured CNKI candidate JSON files locally."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any


ROW_KEYS = ("results", "rows", "candidates", "papers")


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def first(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def authors_list(value: Any) -> list[str]:
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, dict):
                name = clean_text(first(item, "name", "author", "text"))
            else:
                name = clean_text(item)
            if name:
                result.append(name)
        return result
    text = clean_text(value)
    if not text:
        return []
    return [part.strip() for part in re.split(r"[;,；，]", text) if part.strip()]


def number(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = clean_text(value).replace(",", "")
    match = re.search(r"-?\d+", text)
    return int(match.group()) if match else None


def year_value(row: dict[str, Any]) -> int | None:
    value = first(row, "year", "date", "publication_year", "pub_year")
    match = re.search(r"(?:19|20)\d{2}", clean_text(value))
    return int(match.group()) if match else None


def normalized_key(title: str, authors: list[str], year: int | None) -> str:
    base = unicodedata.normalize("NFKC", title).casefold()
    base = re.sub(r"[^\w\u4e00-\u9fff]+", "", base)
    author = ""
    if authors:
        author = unicodedata.normalize("NFKC", authors[0]).casefold()
        author = re.sub(r"[^\w\u4e00-\u9fff]+", "", author)
    return f"{base}|{author or year or ''}"


def extract_rows(document: Any, source: Path) -> list[dict[str, Any]]:
    if isinstance(document, list):
        rows = document
    elif isinstance(document, dict):
        rows = None
        for key in ROW_KEYS:
            if isinstance(document.get(key), list):
                rows = document[key]
                break
        if rows is None:
            raise ValueError(f"{source}: expected one of {ROW_KEYS}")
    else:
        raise ValueError(f"{source}: JSON root must be an object or array")
    return [row for row in rows if isinstance(row, dict)]


def canonical(row: dict[str, Any], provenance: str) -> dict[str, Any] | None:
    title = clean_text(first(row, "title", "name", "paper_title"))
    if not title:
        return None
    authors = authors_list(first(row, "authors", "author", "creators"))
    return {
        "title": title,
        "authors": authors,
        "source": clean_text(first(row, "source", "journal", "venue", "publisher")),
        "year": year_value(row),
        "issue": clean_text(first(row, "issue", "volume_issue", "pub_info")),
        "document_type": clean_text(first(row, "document_type", "doc_type", "database", "type")),
        "cited": number(first(row, "cited", "citations", "citation_count")),
        "downloads": number(first(row, "downloads", "download_count")),
        "doi": clean_text(first(row, "doi", "DOI")),
        "url": clean_text(first(row, "url", "detail_url", "href", "raw_url")),
        "status": clean_text(first(row, "status", "fit", "classification")) or "待核验",
        "provenance": [provenance],
    }


def richness(record: dict[str, Any]) -> int:
    return sum(bool(record.get(key)) for key in record if key != "provenance")


def merge_record(existing: dict[str, Any], incoming: dict[str, Any]) -> None:
    all_provenance = set(existing.get("provenance", [])) | set(
        incoming.get("provenance", [])
    )
    if richness(incoming) > richness(existing):
        preferred, fallback = incoming, existing.copy()
        existing.clear()
        existing.update(preferred)
    else:
        fallback = incoming
    for key, value in fallback.items():
        if key == "provenance":
            continue
        if existing.get(key) in (None, "", [], {}):
            existing[key] = value
    existing["provenance"] = sorted(all_provenance)


def sort_key(record: dict[str, Any], mode: str) -> tuple[Any, ...]:
    cited = record.get("cited")
    downloads = record.get("downloads")
    year = record.get("year")
    if mode == "downloads":
        return (downloads is None, -(downloads or 0), -(cited or 0), -(year or 0))
    if mode == "year":
        return (year is None, -(year or 0), -(cited or 0), -(downloads or 0))
    if mode == "title":
        return (record.get("title", "").casefold(),)
    return (cited is None, -(cited or 0), -(downloads or 0), -(year or 0))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", nargs="+", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--sort", choices=("cited", "downloads", "year", "title"), default="cited"
    )
    args = parser.parse_args()

    merged: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []
    for path in args.input:
        try:
            document = json.loads(path.read_text(encoding="utf-8-sig"))
            rows = extract_rows(document, path)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        for row in rows:
            record = canonical(row, path.stem)
            if record is None:
                warnings.append(f"{path.name}: skipped row without title")
                continue
            key = normalized_key(record["title"], record["authors"], record["year"])
            if key in merged:
                merge_record(merged[key], record)
            else:
                merged[key] = record

    candidates = sorted(merged.values(), key=lambda item: sort_key(item, args.sort))
    for index, record in enumerate(candidates, start=1):
        record["candidate_id"] = f"C{index:04d}"

    payload = {
        "schema_version": "1.0",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "sort": args.sort,
        "count": len(candidates),
        "warnings": warnings,
        "candidates": candidates,
    }
    output = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
