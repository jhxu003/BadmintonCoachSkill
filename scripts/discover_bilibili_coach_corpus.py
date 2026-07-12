from __future__ import annotations

import argparse
from collections.abc import Iterable
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_ROOT = "https://api.bilibili.com"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0 Safari/537.36"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a resumable public-metadata manifest for a Bilibili coach account."
    )
    parser.add_argument("--mid", required=True, type=int)
    parser.add_argument("--coach-name", required=True)
    parser.add_argument("--flat-jsonl", type=Path, required=True)
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--sleep-seconds", type=float, default=1.5)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--max-attempts", type=int, default=4)
    parser.add_argument("--skip-remote-discovery", action="store_true")
    parser.add_argument("--skip-details", action="store_true")
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _archives(container: dict[str, Any]) -> Iterable[dict[str, Any]]:
    archives = container.get("archives") or []
    if isinstance(archives, list):
        yield from (item for item in archives if isinstance(item, dict))


def merge_discovery(
    flat_items: list[dict[str, Any]],
    collections_payload: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    by_bvid: dict[str, dict[str, Any]] = {}

    def ensure(bvid: str) -> dict[str, Any]:
        return by_bvid.setdefault(
            bvid,
            {
                "bvid": bvid,
                "url": f"https://www.bilibili.com/video/{bvid}",
                "playlist_indices": [],
                "discovery_methods": [],
                "collection_titles": [],
                "collection_ids": [],
                "discovery_metadata": {},
            },
        )

    for item in flat_items:
        bvid = str(item.get("id") or item.get("bvid") or "").strip()
        if not bvid:
            continue
        row = ensure(bvid)
        row["discovery_methods"].append("space_playlist")
        index = item.get("playlist_index")
        if index is not None:
            row["playlist_indices"].append(index)

    lists = (
        ((collections_payload or {}).get("data") or {}).get("items_lists") or {}
    )
    for kind, method, id_key in [
        ("seasons_list", "season", "season_id"),
        ("series_list", "series", "series_id"),
    ]:
        containers = lists.get(kind) or []
        if not isinstance(containers, list):
            continue
        for container in containers:
            if not isinstance(container, dict):
                continue
            meta = container.get("meta") or {}
            title = str(meta.get("title") or meta.get("name") or "").strip()
            collection_id = meta.get(id_key)
            for archive in _archives(container):
                bvid = str(archive.get("bvid") or "").strip()
                if not bvid:
                    continue
                row = ensure(bvid)
                row["discovery_methods"].append(method)
                if title:
                    row["collection_titles"].append(title)
                if collection_id is not None:
                    row["collection_ids"].append(f"{method}:{collection_id}")
                row["discovery_metadata"].update(
                    {
                        key: archive.get(key)
                        for key in ["title", "pubdate", "duration", "aid", "state"]
                        if archive.get(key) is not None
                    }
                )

    def unique(values: list[Any]) -> list[Any]:
        return list(dict.fromkeys(values))

    for row in by_bvid.values():
        for key in [
            "playlist_indices",
            "discovery_methods",
            "collection_titles",
            "collection_ids",
        ]:
            row[key] = unique(row[key])
    return sorted(
        by_bvid.values(),
        key=lambda row: (
            min(row["playlist_indices"]) if row["playlist_indices"] else 10**9,
            row["bvid"],
        ),
    )


def fetch_json(
    path: str,
    params: dict[str, Any],
    *,
    timeout: int,
    max_attempts: int,
    sleep_seconds: float,
) -> dict[str, Any]:
    url = f"{API_ROOT}{path}?{urlencode(params)}"
    last_error = "unknown error"
    for attempt in range(1, max_attempts + 1):
        request = Request(url, headers={"User-Agent": USER_AGENT, "Referer": "https://www.bilibili.com/"})
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("code") == 0:
                return payload
            last_error = f"api code={payload.get('code')} message={payload.get('message')}"
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        if attempt < max_attempts:
            time.sleep(sleep_seconds * attempt)
    raise RuntimeError(f"Bilibili request failed after {max_attempts} attempts: {last_error}")


def fetch_collections(args: argparse.Namespace, cache_path: Path) -> dict[str, Any] | None:
    payload: dict[str, Any] | None = None
    if cache_path.exists():
        cached = read_json(cache_path)
        if cached.get("code") == 0:
            payload = cached
    if payload is None:
        if args.skip_remote_discovery:
            return None
        try:
            payload = fetch_json(
                "/x/polymer/web-space/seasons_series_list",
                {"mid": args.mid, "page_num": 1, "page_size": 20},
                timeout=args.timeout,
                max_attempts=args.max_attempts,
                sleep_seconds=args.sleep_seconds,
            )
        except RuntimeError as exc:
            print(f"collection discovery unavailable: {exc}", flush=True)
            return None
    lists = ((payload.get("data") or {}).get("items_lists") or {})
    for container in lists.get("series_list") or []:
        meta = container.get("meta") or {}
        series_id = meta.get("series_id")
        total = int(meta.get("total") or 0)
        if not series_id or total <= len(container.get("archives") or []):
            continue
        archives: list[dict[str, Any]] = []
        page_number = 1
        while len(archives) < total:
            page = fetch_json(
                "/x/series/archives",
                {
                    "mid": args.mid,
                    "series_id": series_id,
                    "only_normal": "true",
                    "sort": "desc",
                    "pn": page_number,
                    "ps": 100,
                },
                timeout=args.timeout,
                max_attempts=args.max_attempts,
                sleep_seconds=args.sleep_seconds,
            )
            page_archives = (page.get("data") or {}).get("archives") or []
            if not page_archives:
                break
            archives.extend(page_archives)
            page_number += 1
            time.sleep(args.sleep_seconds)
        if archives:
            container["archives"] = archives
    write_json(cache_path, payload)
    return payload


def hydrate_details(rows: list[dict[str, Any]], args: argparse.Namespace) -> None:
    detail_dir = args.private_dir / "video-details"
    for number, row in enumerate(rows, start=1):
        path = detail_dir / f"{row['bvid']}.json"
        if path.exists():
            payload = read_json(path)
        elif args.skip_details:
            continue
        else:
            try:
                payload = fetch_json(
                    "/x/web-interface/view",
                    {"bvid": row["bvid"]},
                    timeout=args.timeout,
                    max_attempts=args.max_attempts,
                    sleep_seconds=args.sleep_seconds,
                )
            except RuntimeError as exc:
                row["detail_error"] = str(exc)
                print(f"detail unavailable {row['bvid']}: {exc}", flush=True)
                continue
            write_json(path, payload)
            time.sleep(args.sleep_seconds)
        detail = payload.get("data") or {}
        owner = detail.get("owner") or {}
        rights = detail.get("rights") or {}
        row["detail"] = {
            "title": detail.get("title"),
            "description": detail.get("desc"),
            "pubdate": detail.get("pubdate"),
            "duration": detail.get("duration"),
            "aid": detail.get("aid"),
            "cid": detail.get("cid"),
            "owner_mid": owner.get("mid"),
            "owner_name": owner.get("name"),
            "state": detail.get("state"),
            "copyright": detail.get("copyright"),
            "is_chargeable_season": detail.get("is_chargeable_season"),
            "is_upower_exclusive": detail.get("is_upower_exclusive"),
            "arc_pay": rights.get("arc_pay"),
            "ugc_pay": rights.get("ugc_pay"),
        }
        if number % 25 == 0:
            print(f"details {number}/{len(rows)}", flush=True)


def main() -> None:
    args = parse_args()
    args.private_dir.mkdir(parents=True, exist_ok=True)
    flat_items = read_jsonl(args.flat_jsonl)
    collections = fetch_collections(
        args,
        args.private_dir / "seasons-series.json",
    )
    rows = merge_discovery(flat_items, collections)
    hydrate_details(rows, args)
    output = {
        "manifest_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "coach": {"mid": args.mid, "name": args.coach_name},
        "scope": "public_free_metadata_only",
        "discovery_counts": {
            "space_playlist_rows": len(flat_items),
            "unique_bvids": len(rows),
            "with_details": sum("detail" in row for row in rows),
        },
        "videos": rows,
    }
    output_path = args.private_dir / "canonical-discovery-manifest.json"
    write_json(output_path, output)
    print(f"wrote {output_path}")
    print(json.dumps(output["discovery_counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
