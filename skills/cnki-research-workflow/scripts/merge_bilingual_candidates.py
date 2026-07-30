#!/usr/bin/env python3
"""Merge CNKI JSON and paper-search-pro JSON into one auditable dataset."""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def clean_doi(value: Any) -> str:
    doi = str(value or "").strip().lower()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
    return doi


def clean_title(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return "".join(ch for ch in text if ch.isalnum())


def author_names(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [part.strip() for part in re.split(r"[;,，；]", value) if part.strip()]
    names: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            names.append(item.strip())
        elif isinstance(item, dict):
            name = item.get("name") or item.get("display_name")
            if not name:
                name = " ".join(filter(None, [item.get("given"), item.get("family")]))
            if name:
                names.append(str(name).strip())
    return names


def cnki_records(payload: Any, origin: str) -> list[dict[str, Any]]:
    rows = payload.get("results", []) if isinstance(payload, dict) else payload
    output = []
    for row in rows or []:
        if not isinstance(row, dict) or not row.get("title"):
            continue
        output.append({
            "language": "中文",
            "title": str(row.get("title", "")).strip(),
            "authors": author_names(row.get("authors")),
            "journal": row.get("source") or row.get("journal") or "",
            "year": row.get("year") or "",
            "volume": row.get("volume") or "",
            "issue": row.get("issue") or "",
            "pages": row.get("pages") or row.get("page") or "",
            "doi": clean_doi(row.get("doi")),
            "url": row.get("url") or "",
            "abstract": row.get("abstract") or "",
            "citation_count": row.get("cited") or row.get("citation_count") or 0,
            "downloads": row.get("downloads") or 0,
            "origins": [origin],
            "metadata_status": "CNKI检索元数据；卷期页码按需复核",
            "fulltext_status": "未核验",
        })
    return output


def english_records(payload: Any, origin: str) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and "ok" in payload:
        if not payload.get("ok"):
            raise ValueError(f"paper-search-pro result is not ok: {origin}")
        rows = payload.get("data", [])
    elif isinstance(payload, dict):
        rows = payload.get("results") or payload.get("data") or []
    else:
        rows = payload
    output = []
    for row in rows or []:
        if not isinstance(row, dict) or not row.get("title"):
            continue
        journal = row.get("journal") or row.get("venue") or row.get("source") or ""
        if isinstance(journal, dict):
            journal = journal.get("display_name") or journal.get("name") or ""
        output.append({
            "language": row.get("language") or "英文",
            "title": str(row.get("title", "")).strip(),
            "authors": author_names(row.get("authors") or row.get("authorships")),
            "journal": journal,
            "year": row.get("year") or row.get("publication_year") or "",
            "volume": row.get("volume") or "",
            "issue": row.get("issue") or "",
            "pages": row.get("pages") or row.get("page") or "",
            "doi": clean_doi(row.get("doi")),
            "url": row.get("url") or row.get("openalex_url") or "",
            "abstract": row.get("abstract") or "",
            "citation_count": row.get("citation_count") or row.get("cited_by_count") or 0,
            "downloads": "",
            "origins": [origin],
            "metadata_status": "英文开放数据库元数据；DOI待引用前复核",
            "fulltext_status": "未核验",
        })
    return output


def merge_record(current: dict[str, Any], incoming: dict[str, Any]) -> None:
    current["origins"] = sorted(set(current.get("origins", []) + incoming.get("origins", [])))
    for field in ("authors", "journal", "year", "volume", "issue", "pages", "doi", "url", "abstract"):
        if not current.get(field) and incoming.get(field):
            current[field] = incoming[field]
    current["citation_count"] = max(int(current.get("citation_count") or 0), int(incoming.get("citation_count") or 0))
    if current.get("downloads", "") != "" or incoming.get("downloads", "") != "":
        current["downloads"] = max(int(current.get("downloads") or 0), int(incoming.get("downloads") or 0))


def deduplicate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for row in records:
        doi = clean_doi(row.get("doi"))
        title_key = clean_title(row.get("title"))
        year = str(row.get("year") or "")
        language_group = "zh" if row.get("language") == "中文" else "non-zh"
        key = f"doi:{doi}" if doi else f"title:{language_group}|{title_key}|year:{year}"
        if key in merged:
            merge_record(merged[key], row)
        else:
            merged[key] = row
    output = list(merged.values())
    output.sort(key=lambda row: (row.get("language", ""), -(int(row.get("year") or 0)), clean_title(row.get("title"))))
    for index, row in enumerate(output, 1):
        row["id"] = f"B{index:04d}"
    return output


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    fields = ["id", "language", "title", "authors", "journal", "year", "volume", "issue", "pages", "doi", "url", "citation_count", "downloads", "origins", "metadata_status", "fulltext_status"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in records:
            item = {field: row.get(field, "") for field in fields}
            item["authors"] = "; ".join(row.get("authors", []))
            item["origins"] = "; ".join(row.get("origins", []))
            writer.writerow(item)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cnki", nargs="*", default=[], type=Path)
    parser.add_argument("--english", nargs="*", default=[], type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--csv", type=Path)
    args = parser.parse_args()
    if not args.cnki and not args.english:
        parser.error("at least one --cnki or --english input is required")

    records: list[dict[str, Any]] = []
    for source in args.cnki:
        records.extend(cnki_records(load_json(source), str(source)))
    for source in args.english:
        records.extend(english_records(load_json(source), str(source)))
    merged = deduplicate(records)
    result = {
        "counts": {
            "input_records": len(records),
            "after_dedup": len(merged),
            "duplicates_removed": len(records) - len(merged),
            "chinese": sum(row["language"] == "中文" for row in merged),
            "english": sum(row["language"] != "中文" for row in merged),
        },
        "records": merged,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        write_csv(args.csv, merged)
    print(json.dumps(result["counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
