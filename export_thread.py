#!/usr/bin/env python3
"""Export Discord thread messages plus extracted code, links, and attachments.

Every message in the requested batch is written to JSONL so nothing is lost;
filtering happens later. Media attachments (images, GIFs, video, audio) are
never downloaded. Script-like/text attachments can be downloaded with
--download-attachments; archives are opt-in with --download-archives. Run with
--help for options.
"""

import argparse
import asyncio
import hashlib
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp
import discord
from dotenv import find_dotenv, load_dotenv

DEFAULT_THREAD_ID = 945580784629215253
DEFAULT_LIMIT = 100
DEFAULT_MAX_BATCHES = 10
DEFAULT_MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
DISCORD_EPOCH_MS = 1420070400000

SCRIPT_DIR = Path(__file__).resolve().parent
FENCED_SPAN_RE = re.compile(r"```.*?```", re.DOTALL)
FENCED_BLOCK_RE = re.compile(r"```(.*?)```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
LANGUAGE_RE = re.compile(r"[\w+#.-]*")
URL_RE = re.compile(r"https?://[^\s<>]+")
BARE_KNOWN_HOST_RE = re.compile(
    r"(?<![\w./@-])(?:www\.)?(?:"
    r"github\.com|gist\.github\.com|raw\.githubusercontent\.com|"
    r"gitlab\.com|bitbucket\.org|greasyfork\.org|openuserjs\.org|"
    r"pastebin\.com|sourceb\.in|hastebin\.com|codepen\.io|jsfiddle\.net"
    r")/[^\s<>]+",
    re.IGNORECASE,
)
BARE_WWW_RE = re.compile(
    r"(?<![\w./@-])www\.[a-z0-9-]+(?:\.[a-z0-9-]+)+[^\s<>]*",
    re.IGNORECASE,
)

SCRIPT_EXTENSIONS = {
    ".asm",
    ".bash",
    ".bat",
    ".c",
    ".clj",
    ".cljs",
    ".cmd",
    ".cmake",
    ".cpp",
    ".cs",
    ".css",
    ".dart",
    ".dockerfile",
    ".erl",
    ".ex",
    ".exs",
    ".go",
    ".gradle",
    ".graphql",
    ".gql",
    ".groovy",
    ".h",
    ".hcl",
    ".hs",
    ".html",
    ".ini",
    ".ipynb",
    ".java",
    ".jl",
    ".js",
    ".jsx",
    ".json",
    ".kt",
    ".kts",
    ".lua",
    ".m",
    ".md",
    ".mjs",
    ".mk",
    ".nix",
    ".php",
    ".pl",
    ".proto",
    ".ps1",
    ".psd1",
    ".psm1",
    ".py",
    ".r",
    ".rb",
    ".rs",
    ".scala",
    ".sh",
    ".sql",
    ".svelte",
    ".swift",
    ".tex",
    ".tf",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".vim",
    ".vue",
    ".xml",
    ".yaml",
    ".yml",
}

ARCHIVE_EXTENSIONS = {
    ".7z",
    ".bz2",
    ".gz",
    ".rar",
    ".tar",
    ".tgz",
    ".xz",
    ".zip",
}

MEDIA_EXTENSIONS = {
    ".3gp",
    ".aac",
    ".aiff",
    ".avif",
    ".avi",
    ".bmp",
    ".flac",
    ".flv",
    ".gif",
    ".heic",
    ".ico",
    ".jpeg",
    ".jpg",
    ".m4a",
    ".m4v",
    ".mid",
    ".midi",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".oga",
    ".ogg",
    ".opus",
    ".png",
    ".svg",
    ".tif",
    ".tiff",
    ".wav",
    ".webm",
    ".webp",
    ".wma",
    ".wmv",
}

MEDIA_MIME_PREFIXES = ("image/", "video/", "audio/")
DOWNLOADABLE_MIME_TYPES = {
    "application/gzip",
    "application/javascript",
    "application/json",
    "application/ld+json",
    "application/sql",
    "application/tar",
    "application/typescript",
    "application/x-7z-compressed",
    "application/x-gzip",
    "application/x-javascript",
    "application/x-python",
    "application/x-rar-compressed",
    "application/x-sh",
    "application/x-tar",
    "application/x-typescript",
    "application/x-zip-compressed",
    "application/xml",
    "application/zip",
}

SCRIPT_HOSTS = (
    "gist.github.com",
    "gist.githubusercontent.com",
    "raw.githubusercontent.com",
    "github.com",
    "gitlab.com",
    "bitbucket.org",
    "greasyfork.org",
    "openuserjs.org",
    "pastebin.com",
    "sourceb.in",
    "hastebin.com",
    "codepen.io",
    "jsfiddle.net",
)

URL_CLOSERS = {")": "(", "]": "[", "}": "{"}


def clean_url(url: str) -> str:
    while url:
        last = url[-1]
        if last in ".,;:!?\"'":
            url = url[:-1]
        elif last in URL_CLOSERS and url.count(last) > url.count(URL_CLOSERS[last]):
            url = url[:-1]
        else:
            break
    return url


def normalize_mime_type(content_type: str | None) -> str:
    return (content_type or "").split(";", 1)[0].strip().lower()


def extract_code_blocks(content: str, source: str) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    for match in FENCED_BLOCK_RE.finditer(content):
        inner = match.group(1)
        if "\n" in inner:
            first_line, remainder = inner.split("\n", 1)
            language = first_line.strip()
            if LANGUAGE_RE.fullmatch(language):
                blocks.append({"lang": language, "body": remainder, "source": source})
                continue
        blocks.append({"lang": "", "body": inner, "source": source})
    return blocks


def extract_inline_code(content: str) -> list[str]:
    without_fenced = FENCED_SPAN_RE.sub("", content)
    return INLINE_CODE_RE.findall(without_fenced)


def extract_bare_links(text: str) -> list[str]:
    found = BARE_KNOWN_HOST_RE.findall(text) + BARE_WWW_RE.findall(text)
    return list(dict.fromkeys(f"https://{item}" for item in found))


def extract_link_data(
    message: discord.Message, texts: list[str]
) -> tuple[list[str], list[str], list[str]]:
    candidates: list[str] = []
    for text in texts:
        candidates.extend(URL_RE.findall(text))

    for embed in message.embeds:
        if embed.url:
            candidates.append(embed.url)
        if embed.author and embed.author.url:
            candidates.append(embed.author.url)

    for row in message.components:
        for component in row.children:
            url = getattr(component, "url", None)
            if url:
                candidates.append(url)

    bare_candidates: list[str] = []
    for text in texts:
        bare_candidates.extend(extract_bare_links(text))

    raw_links = list(dict.fromkeys(url for url in candidates if url))
    bare_links = list(
        dict.fromkeys(clean_url(url) for url in bare_candidates if clean_url(url))
    )
    links = list(
        dict.fromkeys(
            [clean_url(url) for url in raw_links if clean_url(url)] + bare_links
        )
    )
    return raw_links, bare_links, links


def is_media_attachment(attachment: dict[str, Any]) -> bool:
    if normalize_mime_type(attachment.get("content_type")).startswith(
        MEDIA_MIME_PREFIXES
    ):
        return True
    return Path(attachment["filename"]).suffix.lower() in MEDIA_EXTENSIONS


def should_download_attachment(
    attachment: dict[str, Any], *, allow_archives: bool = False
) -> bool:
    if attachment["is_media"]:
        return False
    if attachment["script_like"]:
        return True
    if attachment["archive_like"]:
        return allow_archives
    content_type = normalize_mime_type(attachment.get("content_type"))
    return content_type.startswith("text/") or content_type in DOWNLOADABLE_MIME_TYPES


def describe_attachment(
    attachment: discord.Attachment, *, allow_archives: bool = False
) -> dict[str, Any]:
    suffix = Path(attachment.filename).suffix.lower()
    meta: dict[str, Any] = {
        "id": attachment.id,
        "filename": attachment.filename,
        "description": attachment.description,
        "size": attachment.size,
        "content_type": attachment.content_type,
        "url": attachment.url,
        "proxy_url": attachment.proxy_url,
        "script_like": suffix in SCRIPT_EXTENSIONS,
        "archive_like": suffix in ARCHIVE_EXTENSIONS,
    }
    meta["is_media"] = is_media_attachment(meta)
    meta["downloadable"] = should_download_attachment(
        meta, allow_archives=allow_archives
    )
    return meta


async def download_attachment(
    session: aiohttp.ClientSession,
    attachment: discord.Attachment,
    dest_dir: Path,
    max_bytes: int,
    *,
    allow_archives: bool = False,
) -> dict[str, Any]:
    meta = describe_attachment(attachment, allow_archives=allow_archives)

    if not meta["downloadable"]:
        if meta["is_media"]:
            meta["download_skipped"] = "media"
        elif meta["archive_like"] and not allow_archives:
            meta["download_skipped"] = "archive_disabled"
        else:
            meta["download_skipped"] = "not_script_like"
        return meta

    if attachment.size > max_bytes:
        meta["download_skipped"] = "too_large"
        return meta

    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = (
        re.sub(r"[^A-Za-z0-9._-]+", "_", attachment.filename).strip("._")
        or "attachment"
    )
    path = dest_dir / f"{attachment.id}_{safe_name}"
    hasher = hashlib.sha256()
    total = 0

    try:
        async with session.get(attachment.url) as response:
            response.raise_for_status()
            with path.open("wb") as handle:
                async for chunk in response.content.iter_chunked(64 * 1024):
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError(
                            f"attachment exceeded {max_bytes} bytes while downloading"
                        )
                    handle.write(chunk)
                    hasher.update(chunk)
    except (aiohttp.ClientError, asyncio.TimeoutError, OSError, ValueError) as exc:
        path.unlink(missing_ok=True)
        meta["download_error"] = str(exc)
        return meta

    meta["downloaded_path"] = str(path)
    meta["downloaded_bytes"] = total
    meta["sha256"] = hasher.hexdigest()
    return meta


def build_record(
    message: discord.Message,
    include_inline: bool,
    *,
    allow_archives: bool = False,
) -> dict[str, Any]:
    texts: list[tuple[str, str]] = [("message", message.content)]
    for embed in message.embeds:
        if embed.description:
            texts.append(("embed", embed.description))
        if embed.footer and embed.footer.text:
            texts.append(("embed", embed.footer.text))
        for field in embed.fields:
            if field.value:
                texts.append(("embed", field.value))

    code_blocks: list[dict[str, str]] = []
    inline_code: list[str] = []
    for source, text in texts:
        code_blocks.extend(extract_code_blocks(text, source))
        if include_inline:
            inline_code.extend(extract_inline_code(text))

    raw_links, bare_links, links = extract_link_data(
        message, [text for _, text in texts]
    )
    attachments = [
        describe_attachment(item, allow_archives=allow_archives)
        for item in message.attachments
    ]

    kinds: list[str] = []
    if code_blocks or inline_code:
        kinds.append("code")
    if links:
        kinds.append("link")
    if attachments:
        kinds.append("attachment")

    return {
        "message_id": message.id,
        "channel_id": message.channel.id,
        "author": {
            "id": message.author.id,
            "name": str(message.author),
            "bot": message.author.bot,
        },
        "created_at": message.created_at.isoformat(),
        "edited_at": message.edited_at.isoformat() if message.edited_at else None,
        "jump_url": message.jump_url,
        "reply_to_id": (
            message.reference.message_id if message.reference is not None else None
        ),
        "matched": bool(kinds),
        "kinds": kinds,
        "content": message.content,
        "code_blocks": code_blocks,
        "inline_code": list(dict.fromkeys(inline_code)),
        "raw_links": raw_links,
        "bare_links": bare_links,
        "links": links,
        "script_links": [
            url for url in links if any(host in url.lower() for host in SCRIPT_HOSTS)
        ],
        "embeds": [
            {
                "type": str(embed.type),
                "title": embed.title,
                "description": embed.description,
                "url": embed.url,
                "author_url": embed.author.url if embed.author else None,
                "footer_text": embed.footer.text if embed.footer else None,
            }
            for embed in message.embeds
        ],
        "attachments": attachments,
    }


async def fetch_starter_message(
    client: discord.Client, thread: discord.Thread
) -> discord.Message | None:
    try:
        if thread.starter_message is not None:
            return thread.starter_message
        if thread.parent_id is not None:
            parent = await client.fetch_channel(thread.parent_id)
            return await parent.fetch_message(thread.id)
    except discord.HTTPException as exc:
        logging.warning("Could not fetch starter message: %s", exc)
    return None


def default_output_path(thread_id: int, limit: int, oldest_first: bool) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    order = "oldest" if oldest_first else "newest"
    return SCRIPT_DIR / "exports" / f"thread_{thread_id}_{order}_{limit}_{stamp}.jsonl"


def default_state_path(thread_id: int) -> Path:
    return SCRIPT_DIR / "exports" / f"crawl_{thread_id}.state.json"


def default_batch_dir(thread_id: int) -> Path:
    return SCRIPT_DIR / "exports" / f"crawl_{thread_id}"


def write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def snowflake_time(snowflake: int) -> datetime:
    return datetime.fromtimestamp(
        ((int(snowflake) >> 22) + DISCORD_EPOCH_MS) / 1000, tz=timezone.utc
    )


def compute_progress(
    *,
    first_id: int | None,
    last_id: int | None,
    oldest_exported_id: int | None,
    newest_exported_id: int | None,
    direction: str,
    complete: bool,
) -> float:
    if complete:
        return 100.0
    if not first_id or not last_id or last_id <= first_id:
        return 0.0
    if direction == "oldest":
        if newest_exported_id is None:
            return 0.0
        ratio = (newest_exported_id - first_id) / (last_id - first_id)
    else:
        if oldest_exported_id is None:
            return 0.0
        ratio = (last_id - oldest_exported_id) / (last_id - first_id)
    return max(0.0, min(100.0, ratio * 100))


def progress_snapshot(
    channel: Any,
    state: dict[str, Any],
    *,
    complete: bool,
    direction: str,
) -> dict[str, Any]:
    first_id = getattr(channel, "id", None)
    last_id = getattr(channel, "last_message_id", None)
    oldest_exported_id = state.get("oldest_exported_id") or state.get(
        "last_batch_oldest_id"
    )
    newest_exported_id = state.get("newest_exported_id")
    if newest_exported_id is None:
        newest_exported_id = last_id if complete else state.get("last_batch_newest_id")
    if last_id is None:
        last_id = newest_exported_id or first_id
    percent = compute_progress(
        first_id=first_id,
        last_id=last_id,
        oldest_exported_id=oldest_exported_id,
        newest_exported_id=newest_exported_id,
        direction=direction,
        complete=complete,
    )
    oldest_exported_at = state.get("oldest_exported_at")
    if oldest_exported_at is None and oldest_exported_id is not None:
        oldest_exported_at = snowflake_time(oldest_exported_id).isoformat()
    newest_exported_at = state.get("newest_exported_at")
    if newest_exported_at is None and newest_exported_id is not None:
        newest_exported_at = snowflake_time(newest_exported_id).isoformat()
    return {
        "percent": percent,
        "thread_first_id": first_id,
        "thread_last_id": last_id,
        "oldest_exported_id": oldest_exported_id,
        "newest_exported_id": newest_exported_id,
        "oldest_exported_at": oldest_exported_at,
        "newest_exported_at": newest_exported_at,
        "thread_created_at": getattr(channel, "created_at", None),
        "thread_message_count": getattr(channel, "message_count", None),
        "thread_total_message_sent": getattr(channel, "total_message_sent", None),
        "messages": int(state.get("messages", 0)),
        "matched": int(state.get("matched", 0)),
        "batches_completed": int(state.get("batches_completed", 0)),
    }


def log_progress(
    channel: Any,
    state: dict[str, Any],
    *,
    complete: bool,
    direction: str,
) -> dict[str, Any]:
    snapshot = progress_snapshot(channel, state, complete=complete, direction=direction)
    estimate = snapshot["thread_total_message_sent"]
    estimate_text = f"{estimate}" if estimate is not None else "unknown"
    if estimate is not None and snapshot["messages"] > estimate:
        estimate_text += " (API counter undercounts exported messages)"
    logging.info(
        "Progress: %.1f%% by date span; %d messages in %d batches, %d matched; "
        "oldest exported=%s; thread starts=%s; Discord approximate total=%s",
        snapshot["percent"],
        snapshot["messages"],
        snapshot["batches_completed"],
        snapshot["matched"],
        snapshot["oldest_exported_at"] or "unknown",
        (
            snapshot["thread_created_at"].isoformat()
            if isinstance(snapshot["thread_created_at"], datetime)
            else snapshot["thread_created_at"] or "unknown"
        ),
        estimate_text,
    )
    return snapshot


async def export_thread(
    client: discord.Client,
    channel: Any,
    *,
    limit: int,
    oldest_first: bool,
    include_inline: bool,
    include_starter: bool,
    matched_only: bool,
    before: int | None,
    after: int | None,
    output: Path,
    download_attachments: bool,
    download_archives: bool,
    attachment_dir: Path,
    max_attachment_bytes: int,
    http_session: aiohttp.ClientSession,
) -> dict[str, Any]:
    if not hasattr(channel, "history"):
        raise TypeError(
            f"Channel {channel.id} does not support message history "
            f"({type(channel).__name__})"
        )

    history_kwargs: dict[str, Any] = {
        "limit": limit,
        "oldest_first": oldest_first,
    }
    if before is not None:
        history_kwargs["before"] = discord.Object(id=before)
    if after is not None:
        history_kwargs["after"] = discord.Object(id=after)

    records: list[dict[str, Any]] = []
    fetched = 0
    matched = 0
    oldest_id: int | None = None
    newest_id: int | None = None
    oldest_created_at: datetime | None = None
    newest_created_at: datetime | None = None

    async for message in channel.history(**history_kwargs):
        fetched += 1
        record = build_record(message, include_inline, allow_archives=download_archives)

        if download_attachments and record["attachments"]:
            record["attachments"] = [
                await download_attachment(
                    http_session,
                    attachment,
                    attachment_dir,
                    max_attachment_bytes,
                    allow_archives=download_archives,
                )
                for attachment in message.attachments
            ]

        records.append(record)
        if record["matched"]:
            matched += 1
        oldest_id = message.id if oldest_id is None else min(oldest_id, message.id)
        newest_id = message.id if newest_id is None else max(newest_id, message.id)
        if oldest_created_at is None or message.created_at < oldest_created_at:
            oldest_created_at = message.created_at
        if newest_created_at is None or message.created_at > newest_created_at:
            newest_created_at = message.created_at

    if include_starter and isinstance(channel, discord.Thread):
        starter = await fetch_starter_message(client, channel)
        if starter is not None and all(
            record["message_id"] != starter.id for record in records
        ):
            starter_record = build_record(
                starter, include_inline, allow_archives=download_archives
            )
            starter_record["source"] = "starter"
            records.append(starter_record)
            if starter_record["matched"]:
                matched += 1

    written = (
        [record for record in records if record["matched"]] if matched_only else records
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for record in written:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    downloaded = [
        attachment
        for record in records
        for attachment in record["attachments"]
        if attachment.get("downloaded_path")
    ]
    media_skipped = [
        attachment
        for record in records
        for attachment in record["attachments"]
        if attachment.get("download_skipped") == "media"
    ]
    download_errors = [
        attachment
        for record in records
        for attachment in record["attachments"]
        if attachment.get("download_error")
    ]
    archives_skipped = [
        attachment
        for record in records
        for attachment in record["attachments"]
        if attachment.get("download_skipped") == "archive_disabled"
    ]

    logging.info(
        "Scanned %d messages; %d matched (code=%d, link=%d, attachment=%d); "
        "wrote %d records to %s (%.1f KiB)",
        fetched,
        matched,
        sum("code" in record["kinds"] for record in records),
        sum("link" in record["kinds"] for record in records),
        sum("attachment" in record["kinds"] for record in records),
        len(written),
        output,
        output.stat().st_size / 1024,
    )
    if download_attachments:
        logging.info(
            "Attachments: downloaded=%d (%.1f KiB), media_skipped=%d, "
            "archives_skipped=%d, errors=%d",
            len(downloaded),
            sum(item["downloaded_bytes"] for item in downloaded) / 1024,
            len(media_skipped),
            len(archives_skipped),
            len(download_errors),
        )
    logging.info("Batch range: oldest_id=%s newest_id=%s", oldest_id, newest_id)
    if oldest_id is not None and newest_id is not None:
        if oldest_first:
            logging.info("Next forward batch: --after %s", newest_id)
        else:
            logging.info("Next older batch: --before %s", oldest_id)

    return {
        "fetched": fetched,
        "matched": matched,
        "written": len(written),
        "oldest_id": oldest_id,
        "newest_id": newest_id,
        "oldest_created_at": (
            oldest_created_at.isoformat() if oldest_created_at is not None else None
        ),
        "newest_created_at": (
            newest_created_at.isoformat() if newest_created_at is not None else None
        ),
        "downloaded": len(downloaded),
        "downloaded_bytes": sum(item["downloaded_bytes"] for item in downloaded),
        "media_skipped": len(media_skipped),
        "archives_skipped": len(archives_skipped),
        "download_errors": len(download_errors),
        "output": str(output),
    }


async def run(
    *,
    token: str,
    thread_id: int,
    limit: int,
    oldest_first: bool,
    include_inline: bool,
    include_starter: bool,
    matched_only: bool,
    before: int | None,
    after: int | None,
    output: Path,
    download_attachments: bool,
    download_archives: bool,
    max_attachment_bytes: int,
) -> None:
    client = discord.Client(intents=discord.Intents.none())
    timeout = aiohttp.ClientTimeout(total=120)
    try:
        await client.login(token)
        logging.info(
            "Fetching thread %d (limit=%d, oldest_first=%s, before=%s, after=%s)",
            thread_id,
            limit,
            oldest_first,
            before,
            after,
        )
        channel = await client.fetch_channel(thread_id)
        logging.info("Resolved %s (%s)", channel, type(channel).__name__)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            await export_thread(
                client,
                channel,
                limit=limit,
                oldest_first=oldest_first,
                include_inline=include_inline,
                include_starter=include_starter,
                matched_only=matched_only,
                before=before,
                after=after,
                output=output,
                download_attachments=download_attachments,
                download_archives=download_archives,
                attachment_dir=output.parent / "files",
                max_attachment_bytes=max_attachment_bytes,
                http_session=session,
            )
    finally:
        await client.close()


async def run_crawl(
    *,
    token: str,
    thread_id: int,
    limit: int,
    oldest_first: bool,
    include_inline: bool,
    include_starter: bool,
    matched_only: bool,
    before: int | None,
    after: int | None,
    state_file: Path,
    batch_dir: Path,
    max_batches: int,
    reset_state: bool,
    download_attachments: bool,
    download_archives: bool,
    max_attachment_bytes: int,
) -> None:
    direction = "oldest" if oldest_first else "newest"
    state: dict[str, Any] = {}
    if state_file.exists() and not reset_state:
        state = json.loads(state_file.read_text(encoding="utf-8"))
        state_direction = state.get("direction")
        if state_direction and state_direction != direction:
            logging.warning(
                "State direction is %s, not %s; continuing with %s",
                state_direction,
                direction,
                state_direction,
            )
            direction = state_direction
            oldest_first = direction == "oldest"
        if state.get("complete"):
            logging.info(
                "Crawl state already complete. Use --reset-state to start over."
            )
            return
    elif reset_state:
        state_file.unlink(missing_ok=True)
        state = {}

    next_before = state.get("next_before") if state else before
    next_after = state.get("next_after") if state else after
    batch_number = int(state.get("next_batch", 1)) if state else 1
    total_messages = int(state.get("messages", 0)) if state else 0
    total_matched = int(state.get("matched", 0)) if state else 0
    oldest_exported_id = state.get("oldest_exported_id") if state else None
    newest_exported_id = state.get("newest_exported_id") if state else None
    oldest_exported_at = state.get("oldest_exported_at") if state else None
    newest_exported_at = state.get("newest_exported_at") if state else None
    complete = False

    batch_dir.mkdir(parents=True, exist_ok=True)
    client = discord.Client(intents=discord.Intents.none())
    timeout = aiohttp.ClientTimeout(total=120)
    max_loops = max_batches if max_batches > 0 else 10**9

    try:
        await client.login(token)
        channel = await client.fetch_channel(thread_id)
        logging.info(
            "Crawling thread %d direction=%s starting at batch %d "
            "(before=%s, after=%s)",
            thread_id,
            direction,
            batch_number,
            next_before,
            next_after,
        )
        log_progress(channel, state, complete=False, direction=direction)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            for _ in range(max_loops):
                output = batch_dir / f"batch_{batch_number:04d}.jsonl"
                stats = await export_thread(
                    client,
                    channel,
                    limit=limit,
                    oldest_first=oldest_first,
                    include_inline=include_inline,
                    include_starter=include_starter and batch_number == 1,
                    matched_only=matched_only,
                    before=next_before,
                    after=next_after,
                    output=output,
                    download_attachments=download_attachments,
                    download_archives=download_archives,
                    attachment_dir=batch_dir / "files",
                    max_attachment_bytes=max_attachment_bytes,
                    http_session=session,
                )

                if stats["fetched"] == 0:
                    complete = True
                    break

                total_messages += stats["fetched"]
                total_matched += stats["matched"]

                if oldest_first:
                    next_after = stats["newest_id"]
                    next_before = None
                else:
                    next_before = stats["oldest_id"]
                    next_after = None

                if stats["fetched"] < limit:
                    complete = True

                if stats["oldest_id"] is not None:
                    oldest_exported_id = (
                        stats["oldest_id"]
                        if oldest_exported_id is None
                        else min(oldest_exported_id, stats["oldest_id"])
                    )
                if stats["newest_id"] is not None:
                    newest_exported_id = (
                        stats["newest_id"]
                        if newest_exported_id is None
                        else max(newest_exported_id, stats["newest_id"])
                    )
                if stats["oldest_created_at"] is not None:
                    if (
                        oldest_exported_at is None
                        or stats["oldest_created_at"] < oldest_exported_at
                    ):
                        oldest_exported_at = stats["oldest_created_at"]
                if stats["newest_created_at"] is not None:
                    if (
                        newest_exported_at is None
                        or stats["newest_created_at"] > newest_exported_at
                    ):
                        newest_exported_at = stats["newest_created_at"]

                state = {
                    "thread_id": thread_id,
                    "direction": direction,
                    "limit": limit,
                    "next_before": next_before,
                    "next_after": next_after,
                    "next_batch": batch_number + 1,
                    "batches_completed": batch_number,
                    "messages": total_messages,
                    "matched": total_matched,
                    "complete": complete,
                    "last_batch": str(output),
                    "last_batch_oldest_id": stats["oldest_id"],
                    "last_batch_newest_id": stats["newest_id"],
                    "oldest_exported_id": oldest_exported_id,
                    "newest_exported_id": newest_exported_id,
                    "oldest_exported_at": oldest_exported_at,
                    "newest_exported_at": newest_exported_at,
                    "thread_first_id": channel.id,
                    "thread_last_id": getattr(channel, "last_message_id", None),
                    "thread_created_at": (
                        channel.created_at.isoformat()
                        if getattr(channel, "created_at", None) is not None
                        else None
                    ),
                    "thread_message_count": getattr(channel, "message_count", None),
                    "thread_total_message_sent": getattr(
                        channel, "total_message_sent", None
                    ),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                snapshot = log_progress(
                    channel, state, complete=complete, direction=direction
                )
                state["progress_percent"] = round(snapshot["percent"], 2)
                state["progress_method"] = "date_span_estimate"
                write_state(state_file, state)
                batch_number += 1

                if complete:
                    break
    finally:
        await client.close()

    logging.info(
        "Crawl %s: %d messages, %d matched, state=%s",
        "complete" if complete else "paused",
        total_messages,
        total_matched,
        state_file,
    )


async def show_progress(*, token: str, thread_id: int, state_file: Path) -> None:
    state: dict[str, Any] = {}
    if state_file.exists():
        state = json.loads(state_file.read_text(encoding="utf-8"))
    direction = state.get("direction", "newest")
    complete = bool(state.get("complete"))
    client = discord.Client(intents=discord.Intents.none())
    try:
        await client.login(token)
        channel = await client.fetch_channel(thread_id)
        snapshot = log_progress(channel, state, complete=complete, direction=direction)
        if state:
            state.update(
                {
                    "progress_percent": round(snapshot["percent"], 2),
                    "progress_method": "date_span_estimate",
                    "oldest_exported_id": snapshot["oldest_exported_id"],
                    "newest_exported_id": snapshot["newest_exported_id"],
                    "oldest_exported_at": snapshot["oldest_exported_at"],
                    "newest_exported_at": snapshot["newest_exported_at"],
                    "thread_first_id": snapshot["thread_first_id"],
                    "thread_last_id": snapshot["thread_last_id"],
                    "thread_created_at": (
                        snapshot["thread_created_at"].isoformat()
                        if isinstance(snapshot["thread_created_at"], datetime)
                        else snapshot["thread_created_at"]
                    ),
                    "thread_message_count": snapshot["thread_message_count"],
                    "thread_total_message_sent": snapshot["thread_total_message_sent"],
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            write_state(state_file, state)
    finally:
        await client.close()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--thread",
        type=int,
        default=DEFAULT_THREAD_ID,
        help=f"thread ID to scan (default: {DEFAULT_THREAD_ID})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"maximum messages per batch (default: {DEFAULT_LIMIT})",
    )
    parser.add_argument(
        "--newest",
        action="store_true",
        help="scan newest messages first instead of oldest first",
    )
    parser.add_argument(
        "--before",
        type=int,
        help="only messages before this message ID (for paging older batches)",
    )
    parser.add_argument(
        "--after",
        type=int,
        help="only messages after this message ID (for paging newer batches)",
    )
    parser.add_argument(
        "--no-inline",
        action="store_false",
        dest="include_inline",
        default=True,
        help="do not extract inline `code`",
    )
    parser.add_argument(
        "--include-starter",
        action="store_true",
        help="include the thread's starter message when it can be fetched",
    )
    parser.add_argument(
        "--matched-only",
        action="store_true",
        help="write only messages with code, links, or attachments",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="output JSONL path for a single batch",
    )
    parser.add_argument(
        "--download-attachments",
        action="store_true",
        help=(
            "download script-like/text attachments, never media; archives "
            "require --download-archives"
        ),
    )
    parser.add_argument(
        "--download-archives",
        action="store_true",
        help="also download archive attachments (off by default)",
    )
    parser.add_argument(
        "--max-attachment-bytes",
        type=int,
        default=DEFAULT_MAX_ATTACHMENT_BYTES,
        help=(
            "skip downloads larger than this many bytes "
            f"(default: {DEFAULT_MAX_ATTACHMENT_BYTES})"
        ),
    )
    parser.add_argument(
        "--crawl",
        action="store_true",
        help="page continuously, writing one batch file per run and saving state",
    )
    parser.add_argument(
        "--batch-dir",
        type=Path,
        help="directory for crawl batch files (default: exports/crawl_<thread>)",
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        help="crawl state file (default: exports/crawl_<thread>.state.json)",
    )
    parser.add_argument(
        "--progress",
        action="store_true",
        help="print current crawl progress from state and exit",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=DEFAULT_MAX_BATCHES,
        help=(
            "maximum batches to fetch per crawl invocation, 0 = until complete "
            f"(default: {DEFAULT_MAX_BATCHES})"
        ),
    )
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="ignore and replace existing crawl state",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    load_dotenv(find_dotenv(usecwd=True))
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logging.error("DISCORD_TOKEN is not set. Add it to .env or the environment.")
        return 1

    if args.crawl and args.output:
        logging.error("--output cannot be combined with --crawl.")
        return 1

    try:
        if args.progress:
            asyncio.run(
                show_progress(
                    token=token,
                    thread_id=args.thread,
                    state_file=args.state_file or default_state_path(args.thread),
                )
            )
        elif args.crawl:
            asyncio.run(
                run_crawl(
                    token=token,
                    thread_id=args.thread,
                    limit=args.limit,
                    oldest_first=not args.newest,
                    include_inline=args.include_inline,
                    include_starter=args.include_starter,
                    matched_only=args.matched_only,
                    before=args.before,
                    after=args.after,
                    state_file=args.state_file or default_state_path(args.thread),
                    batch_dir=args.batch_dir or default_batch_dir(args.thread),
                    max_batches=args.max_batches,
                    reset_state=args.reset_state,
                    download_attachments=args.download_attachments,
                    download_archives=args.download_archives,
                    max_attachment_bytes=args.max_attachment_bytes,
                )
            )
        else:
            oldest_first = not args.newest
            output = args.output or default_output_path(
                args.thread, args.limit, oldest_first
            )
            asyncio.run(
                run(
                    token=token,
                    thread_id=args.thread,
                    limit=args.limit,
                    oldest_first=oldest_first,
                    include_inline=args.include_inline,
                    include_starter=args.include_starter,
                    matched_only=args.matched_only,
                    before=args.before,
                    after=args.after,
                    output=output,
                    download_attachments=args.download_attachments,
                    download_archives=args.download_archives,
                    max_attachment_bytes=args.max_attachment_bytes,
                )
            )
    except discord.LoginFailure:
        logging.error("Discord rejected the token.")
        return 1
    except discord.Forbidden:
        logging.error(
            "Bot lacks access to thread %d. Check View Channel and "
            "Read Message History permissions.",
            args.thread,
        )
        return 1
    except discord.NotFound:
        logging.error("Thread %d was not found.", args.thread)
        return 1
    except discord.HTTPException as exc:
        logging.error("Discord API error: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
