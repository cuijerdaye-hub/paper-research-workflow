# 能力路由与来源边界

## 路由表

| 用户目标 | 首选能力 | 升级条件 |
|---|---|---|
| 主题、作者、年份、文献类型检索 | `$cnki-search` / `cnki` CLI | CLI 被拦截，或需要页面限定条件 |
| 英文主题检索、批量候选与饱和度 | `$paper-search-pro` headless `agent_search` | 配置缺失、限流、零命中或需要替代数据库 |
| 英文降级发现与 DOI 核验 | `$paper-lookup` | 拟正式引用时再用 `$citation-management` 交叉核验 |
| GB/T 7714 初稿 | `cnki --format=citation` | 终稿必须进入元数据核验 |
| CSSCI、北大核心、CSCD、EI | `$chrome:control-chrome` | 页面筛选无法稳定完成时停止 |
| 论文摘要、关键词、基金、机构 | CLI 详情；失败后 Chrome | 只处理短名单 |
| 期刊检索、收录、影响因子、刊期目录 | Chrome | 以页面当时显示值为准并记录日期 |
| PDF/CAJ 下载 | Chrome 中的合法下载入口 | 登录、权限或验证码出现时暂停 |
| PDF 全文相关性核验 | `$pdf:pdf` | CAJ 无法可靠读取时明确报告 |
| DOI、BibTeX 校验 | `$citation-management` | 中文无 DOI 文献以知网详情为主 |
| Zotero 导入 | `$cli-anything-zotero` | 需要 Zotero Local API |

## 分层原则

1. CLI 负责广覆盖和结构化元数据，默认 10–30 条。
2. 本地清单负责去重、排序和候选状态，不重复访问知网。
3. Chrome 负责登录态页面、来源筛选、期刊信息和授权下载。
4. PDF 负责方法、场景、变量、结论和局限的全文证据。
5. 引用工具负责格式与 DOI 一致性，不能补造缺失信息。
6. 中英文检索式分开执行；统一清单只在本地合并，不跨语种猜测同一性。

## 英文路径

1. 用英文概念块调用 `$paper-search-pro`；由…838 tokens truncated…import re
import unicodedata
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = raw.decode("utf-16")
    else:
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("utf-16")
    return json.loads(text)


def first_text(value: Any) -> str:
    if isinstance(value, list):
        for item in value:
            text = first_text(item)
            if text:
                return text
        return ""
    if isinstance(value, dict):
        return first_text(value.get("display_name") or value.get("name") or value.get("title"))
    return str(value or "").strip()


def publication_year(row: dict[str, Any]) -> Any:
    direct = row.get("year") or row.get("publication_year")
    if direct:
        return direct
    for key in ("published", "issued", "published-print", "published-online"):
        value = row.get(key)
        if isinstance(value, dict):
            parts = value.get("date-parts")
            if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]:
                return parts[0][0]
    date = row.get("publicationDate") or row.get("publication_date")
    if date:
        match = re.match(r"(\d{4})", str(date))
        if match:
            return int(match.group(1))
    return ""


def inverted_abstract(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    positioned: list[tuple[int, str]] = []
    for word, positions in value.items():
        for position in positions or []:
            if isinstance(position, int):
                positioned.append((position, str(word)))
    return " ".join(word for _, word in sorted(positioned))


def primary_source_name(row: dict[str, Any]) -> str:
    location = row.get("primary_location")
    if isinstance(location, dict):
        source = location.get("source")
        if isinstance(source, dict):
            name = source.get("display_name") or source.get("name")
            if name:
                return str(name)
    return ""


def primary_url(row: dict[str, Any]) -> str:
    location = row.get("primary_location")
    if isinstance(location, dict):
        return str(location.get("landing_page_url") or location.get("pdf_url") or "")
    return ""


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
            nested_author = item.get("author") if isinstance(item.get("author"), dict) else {}
            name = item.get("name") or item.get("display_name") or nested_author.get("display_name") or nested_author.get("name")
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


def english_rows(payload: Any, origin: str) -> tuple[list[Any], str]:
    if isinstance(payload, dict) and "ok" in payload:
        if not payload.get("ok"):
            raise ValueError(f"paper-search-pro result is not ok: {origin}")
        return payload.get("data", []), "paper-search-pro"
    if isinstance(payload, dict):
        message = payload.get("message")
        if isinstance(message, dict) and isinstance(message.get("items"), list):
            return message["items"], "crossref"
        if isinstance(payload.get("results"), list):
            return payload["results"], "openalex"
        if isinstance(payload.get("data"), list):
            return payload["data"], "semantic-scholar"
        raise ValueError(f"unsupported English JSON schema: {origin}")
    if isinstance(payload, list):
        return payload, "generic"
    raise ValueError(f"English JSON must be an object or list: {origin}")


def english_records(payload: Any, origin: str) -> list[dict[str, Any]]:
    rows, source_kind = english_rows(payload, origin)
    output = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        title = first_text(row.get("title"))
        if not title:
            continue
        journal = row.get("journal") or row.get("venue") or row.get("source") or row.get("container-title") or primary_source_name(row)
        if isinstance(journal, dict):
            journal = journal.get("display_name") or journal.get("name") or ""
        journal = first_text(journal)
        external_ids = row.get("externalIds") if isinstance(row.get("externalIds"), dict) else {}
        abstract = row.get("abstract") or inverted_abstract(row.get("abstract_inverted_index"))
        raw_language = str(row.get("language") or "").lower()
        language = "中文" if raw_language.startswith("zh") else "英文"
        output.append({
            "language": language,
            "title": title,
            "authors": author_names(row.get("authors") or row.get("author") or row.get("authorships")),
            "journal": journal,
            "year": publication_year(row),
            "volume": row.get("volume") or "",
            "issue": row.get("issue") or "",
            "pages": row.get("pages") or row.get("page") or "",
            "doi": clean_doi(row.get("doi") or row.get("DOI") or external_ids.get("DOI")),
            "url": row.get("url") or row.get("URL") or row.get("openalex_url") or primary_url(row) or row.get("id") or "",
            "abstract": abstract or "",
            "citation_count": row.get("citation_count") or row.get("citationCount") or row.get("cited_by_count") or row.get("is-referenced-by-count") or 0,
            "downloads": "",
            "origins": [origin],
            "metadata_status": f"{source_kind} 元数据；DOI待引用前复核",
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
