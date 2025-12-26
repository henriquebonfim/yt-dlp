#!/usr/bin/env python3
"""
Minimal YouTube queue downloader for Replit.
- Reads URLs from queue.md (plain or markdown links)
- Downloads the best available video/audio combination
- Records failures after max retries into failed.md
- Appends run history to log.json
"""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Tuple

try:
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError, ExtractorError
except ImportError:
    print("yt-dlp is not installed. Install with: pip install yt-dlp")
    sys.exit(1)


YOUTUBE_URL_RE = re.compile(
    r"https?://(?:www\.)?(youtube\.com|youtu\.be)/", re.IGNORECASE
)
MARKDOWN_LINK_RE = re.compile(r"\((https?://[^\s)]+)\)")


class StatusCode(str, Enum):
    SUCCESS = "SUCCESS"
    RATE_LIMIT = "RATE_LIMIT"
    AGE_LIMIT = "AGE_LIMIT"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


@dataclass
class LogEntry:
    url: str
    status: str  # downloaded | failed
    status_code: StatusCode
    retries: int
    date_created: str


@dataclass
class Config:
    queue_file: Path = Path("queue.md")
    failed_file: Path = Path("failed.md")
    log_file: Path = Path("log.json")
    downloads_dir: Path = Path("downloads")
    max_retries: int = 3
    retry_delay_seconds: int = 5
    ytdlp_format: str = "bestvideo+bestaudio/best"

    def ensure_dirs(self):
        self.downloads_dir.mkdir(parents=True, exist_ok=True)


def load_queue(cfg: Config) -> List[str]:
    if not cfg.queue_file.exists():
        return []
    lines = cfg.queue_file.read_text(encoding="utf-8").splitlines()
    urls: List[str] = []
    for line in lines:
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        match = MARKDOWN_LINK_RE.search(raw)
        candidate = match.group(1) if match else raw
        if YOUTUBE_URL_RE.search(candidate):
            urls.append(candidate)
    return urls


def load_log(cfg: Config) -> List[dict]:
    if not cfg.log_file.exists():
        return []
    try:
        data = json.loads(cfg.log_file.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def persist_log(cfg: Config, entries: List[dict]):
    cfg.log_file.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def append_failed(cfg: Config, failed_urls: List[str]):
    if not failed_urls:
        return
    existing = []
    if cfg.failed_file.exists():
        existing = cfg.failed_file.read_text(encoding="utf-8").splitlines()
    merged = existing + failed_urls
    cfg.failed_file.write_text("\n".join(merged) + "\n", encoding="utf-8")


def build_ydl_opts(cfg: Config) -> dict:
    return {
        "format": cfg.ytdlp_format,
        "outtmpl": str(cfg.downloads_dir / "%(title)s" / "%(title)s.%(ext)s"),
        "writethumbnail": True,
        "quiet": True,
        "no_warnings": True,
    }


def classify_error(exc: Exception) -> StatusCode:
    msg = str(exc).lower()
    if "429" in msg or "too many requests" in msg or "rate" in msg:
        return StatusCode.RATE_LIMIT
    if "age" in msg and "restrict" in msg:
        return StatusCode.AGE_LIMIT
    return StatusCode.UNKNOWN_ERROR


def download_single(url: str, cfg: Config) -> Tuple[StatusCode, int]:
    opts = build_ydl_opts(cfg)
    attempts = 0
    last_status = StatusCode.UNKNOWN_ERROR
    while attempts < cfg.max_retries:
        attempts += 1
        try:
            # Extract info first to get title and create folder
            with YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get("title", "video")
                # Sanitize title for folder name
                folder_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
                video_dir = cfg.downloads_dir / folder_name
                video_dir.mkdir(parents=True, exist_ok=True)

            # Now download to the created folder
            opts["outtmpl"] = str(video_dir / "%(title)s.%(ext)s")
            with YoutubeDL(opts) as ydl:
                ydl.download([url])
            return StatusCode.SUCCESS, attempts - 1
        except (DownloadError, ExtractorError) as exc:
            last_status = classify_error(exc)
        except KeyboardInterrupt:
            raise
        except Exception as exc:  # pragma: no cover - yt_dlp edge cases
            last_status = classify_error(exc)
        if attempts < cfg.max_retries:
            time.sleep(cfg.retry_delay_seconds)
    return last_status, attempts


def process_queue(cfg: Config):
    cfg.ensure_dirs()
    urls = load_queue(cfg)
    if not urls:
        print("No URLs found in queue.md. Add one per line.")
        return

    log_entries = load_log(cfg)
    failed_urls: List[str] = []
    now = datetime.utcnow().isoformat() + "Z"

    for url in urls:
        status_code, attempts = download_single(url, cfg)
        success = status_code == StatusCode.SUCCESS
        status_text = "downloaded" if success else "failed"
        retries_used = max(0, attempts - 1) if success else attempts

        entry = LogEntry(
            url=url,
            status=status_text,
            status_code=status_code,
            retries=retries_used,
            date_created=now,
        )
        log_entries.append(asdict(entry))

        marker = "✅" if success else "❌"
        print(f"{marker} {url} ({status_code.value})")
        if not success:
            failed_urls.append(url)

    append_failed(cfg, failed_urls)
    persist_log(cfg, log_entries)

    print("\nRun complete.")
    print(f"Downloaded to: {cfg.downloads_dir.resolve()}")
    if failed_urls:
        print(f"Failed URLs stored in {cfg.failed_file} ({len(failed_urls)} items)")
    print(f"Log written to {cfg.log_file}")


def main():
    try:
        process_queue(Config())
    except KeyboardInterrupt:
        print("\nAborted by user.")


if __name__ == "__main__":
    main()
