#!/usr/bin/env python3
"""Fetch canonical public Bilibili titles for the Pages video catalogue.

The Pages catalogue is allowed to publish only public metadata.  This helper
reads the existing public catalogue, asks Bilibili's public view endpoint for
each BVID, and writes a title registry containing only source id, BVID and the
platform title.  It never downloads video, audio, frames, ASR or private
runtime data.

Run this before rebuilding ``catalog.json`` whenever source titles need a
refresh.  The catalogue builder consumes the registry so Pages never displays
an internal import label in place of a Bilibili title.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_CATALOG = Path("web/public/pages-demo/catalog.json")
DEFAULT_OUTPUT = Path("web/public/pages-demo/bilibili-title-registry.json")
BVID_RE = re.compile(r"\b(BV[0-9A-Za-z]+)\b")
USER_AGENT = "BadmintonCoachSkill-public-metadata/1.0 (+https://github.com/jhxu003/BadmintonCoachSkill)"


def load_catalog(path: Path) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    videos: list[dict[str, str]] = []
    for coach in payload.get("coaches", []):
        for video in coach.get("videos", []):
            source_id = str(video.get("source_id", "")).strip()
            url = str(video.get("url", "")).strip()
            match = BVID_RE.search(url)
            if not source_id or not match:
                raise ValueError(f"catalogue record has no source id or BVID: {video!r}")
            videos.append({"source_id": source_id, "bvid": match.group(1), "url": url})
    if len(videos) != len({video["source_id"] for video in videos}):
        raise ValueError("catalogue contains duplicate source ids")
    return videos


def load_existing(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "public-bilibili-title-registry/v1":
        raise ValueError(f"unexpected title registry schema: {path}")
    result: dict[str, dict[str, str]] = {}
    for row in payload.get("videos", []):
        source_id = str(row.get("source_id", "")).strip()
        bvid = str(row.get("bvid", "")).strip()
        title = str(row.get("title", "")).strip()
        if not source_id or not bvid or not title or source_id in result:
            raise ValueError(f"invalid title registry record: {row!r}")
        result[source_id] = {"source_id": source_id, "bvid": bvid, "title": title}
    return result


def fetch_title(bvid: str, *, retries: int = 3) -> str:
    endpoint = "https://api.bilibili.com/x/web-interface/view?" + urlencode({"bvid": bvid})
    error: Exception | None = None
    for attempt in range(retries):
        try:
            request = Request(endpoint, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urlopen(request, timeout=20) as response:  # nosec B310: fixed public HTTPS endpoint
                payload: dict[str, Any] = json.load(response)
            if payload.get("code") != 0:
                raise RuntimeError(f"Bilibili API {payload.get('code')}: {payload.get('message')}")
            title = str((payload.get("data") or {}).get("title", "")).strip()
            if not title:
                raise RuntimeError("Bilibili API returned an empty title")
            return title
        except Exception as exc:  # network/API errors get a bounded retry
            error = exc
            if attempt + 1 < retries:
                time.sleep(0.7 * (attempt + 1))
    raise RuntimeError(f"{bvid}: {error}")


def refresh(rows: list[dict[str, str]], existing: dict[str, dict[str, str]], *, workers: int, refresh_all: bool) -> list[dict[str, str]]:
    resolved: dict[str, dict[str, str]] = {}
    pending: list[dict[str, str]] = []
    for row in rows:
        cached = existing.get(row["source_id"])
        if cached and cached["bvid"] == row["bvid"] and not refresh_all:
            resolved[row["source_id"]] = cached
        else:
            pending.append(row)

    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch_title, row["bvid"]): row for row in pending}
        for index, future in enumerate(as_completed(futures), start=1):
            row = futures[future]
            try:
                title = future.result()
            except Exception as exc:
                failures.append(f"{row['source_id']} ({row['bvid']}): {exc}")
            else:
                resolved[row["source_id"]] = {"source_id": row["source_id"], "bvid": row["bvid"], "title": title}
            if index % 50 == 0 or index == len(pending):
                print(f"resolved {index}/{len(pending)} titles")
    if failures:
        raise RuntimeError("failed to retrieve canonical titles:\n" + "\n".join(failures))
    return [resolved[row["source_id"]] for row in sorted(rows, key=lambda item: item["source_id"])]


def write_registry(path: Path, videos: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "public-bilibili-title-registry/v1",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "publication_boundary": "public Bilibili source id, BVID and public page title only; no media or private analysis data",
        "video_count": len(videos),
        "videos": videos,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    result.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    result.add_argument("--workers", type=int, default=6)
    result.add_argument("--refresh-all", action="store_true", help="refetch cached BVID titles as well")
    return result


def main() -> None:
    args = parser().parse_args()
    if args.workers < 1 or args.workers > 12:
        raise SystemExit("--workers must be between 1 and 12")
    rows = load_catalog(args.catalog)
    videos = refresh(rows, load_existing(args.output), workers=args.workers, refresh_all=args.refresh_all)
    write_registry(args.output, videos)
    print(f"wrote {len(videos)} canonical Bilibili titles -> {args.output}")


if __name__ == "__main__":
    main()
