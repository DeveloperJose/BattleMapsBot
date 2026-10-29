#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

PII_FILENAMES = {"replaystorage.json", "usernamestorage.json"}
GENERIC_STEMS = {"hotkeys", "index", "message", "notes", "readme", "script"}
MAX_FILE_BYTES = 2_000_000
SENSITIVE_PATTERNS = (
    ("private key", re.compile(rb"BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY")),
    (
        "Discord token",
        re.compile(
            rb"(?:mfa\.[\w-]{20,}|[A-Za-z0-9_-]{24,26}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27,})"
        ),
    ),
    ("AWS access key", re.compile(rb"AKIA[0-9A-Z]{16}")),
    (
        "credential assignment",
        re.compile(
            rb"(?i)(api[_-]?key|secret|password|passwd|token)\s*[:=]\s*['\"][^'\"\s]{8,}"
        ),
    ),
    (
        "Discord webhook",
        re.compile(rb"https://(?:discord|discordapp)\.com/api/webhooks/"),
    ),
    ("email address", re.compile(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
)
LANG_EXTENSIONS = {
    "": ".txt",
    "c": ".c",
    "c#": ".cs",
    "c++": ".cpp",
    "cpp": ".cpp",
    "cs": ".cs",
    "csharp": ".cs",
    "css": ".css",
    "html": ".html",
    "java": ".java",
    "javascript": ".js",
    "js": ".js",
    "json": ".json",
    "jsx": ".jsx",
    "lua": ".lua",
    "php": ".php",
    "py": ".py",
    "python": ".py",
    "rb": ".rb",
    "ruby": ".rb",
    "rs": ".rs",
    "rust": ".rs",
    "sh": ".sh",
    "bash": ".sh",
    "sql": ".sql",
    "text": ".txt",
    "ts": ".ts",
    "tsx": ".tsx",
    "txt": ".txt",
    "typescript": ".ts",
    "xml": ".xml",
    "yaml": ".yml",
    "yml": ".yml",
}
LANG_LABELS = {
    ".c": "C",
    ".cpp": "C++",
    ".cs": "C#",
    ".css": "CSS",
    ".html": "HTML",
    ".java": "Java",
    ".js": "JavaScript",
    ".json": "JSON",
    ".jsx": "JSX",
    ".lua": "Lua",
    ".php": "PHP",
    ".py": "Python",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".sh": "Shell",
    ".sql": "SQL",
    ".ts": "TypeScript",
    ".tsx": "TSX",
    ".txt": "Text",
    ".xml": "XML",
    ".yml": "YAML",
}


@dataclass
class FileArtifact:
    original_name: str
    public_name: str
    relative_path: str
    source_path: Path
    size: int
    sha256: str
    date: str
    message_id: int
    jump_url: str


@dataclass
class Snippet:
    public_name: str
    relative_path: str
    body: str
    sha256: str
    extension: str
    date: str
    message_id: int
    jump_url: str


@dataclass
class ExternalLink:
    url: str
    title: str
    host: str
    date: str
    message_id: int
    jump_url: str
    occurrences: int = 1


@dataclass
class Author:
    id: int
    name: str
    slug: str
    messages: int = 0
    code_messages: int = 0
    files: list[FileArtifact] = field(default_factory=list)
    snippets: list[Snippet] = field(default_factory=list)
    links: list[ExternalLink] = field(default_factory=list)

    @property
    def content_count(self) -> int:
        return len(self.files) + len(self.snippets) + len(self.links)


@dataclass
class Exclusion:
    author: str
    name: str
    reason: str
    size: int
    message_url: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def slugify(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
    return slug or "unknown"


def safe_filename(value: str) -> str:
    name = Path(value).name
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_name)
    safe = re.sub(r"_+", "_", safe).strip("._-")
    if not safe:
        safe = "file"
    stem = Path(safe).stem[:80] or "file"
    suffix = Path(safe).suffix[:20]
    return f"{stem}{suffix}"


def extension_for_language(language: str) -> str:
    return LANG_EXTENSIONS.get(language.strip().lower(), ".txt")


def language_label(extension: str) -> str:
    return LANG_LABELS.get(extension, extension.lstrip(".").upper() or "Text")


def human_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KiB"
    return f"{size / (1024 * 1024):.1f} MiB"


def md_cell(value: object) -> str:
    text = " ".join(str(value).splitlines())
    return text.replace("\\", "\\\\").replace("|", "\\|")


def md_link(label: str, url: str) -> str:
    return f"[{md_cell(label)}](<{url}>)"


def message_link(message_id: int, jump_url: str) -> str:
    return md_link(str(message_id), jump_url)


def link_label(url: str) -> str:
    parsed = urlsplit(url)
    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.strip("/")
    if host == "github.com" and path:
        parts = path.split("/")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
    if host in {"greasyfork.org", "update.greasyfork.org"}:
        match = re.search(r"/scripts/\d+-([^/]+)", parsed.path)
        if match:
            return match.group(1).replace("-", " ")
    if path:
        return f"{host}/{path}" if host else path
    return host or url


def load_records(exports_dir: Path) -> list[dict]:
    records: dict[int, dict] = {}
    for path in sorted(exports_dir.rglob("batch_*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                records[int(record["message_id"])] = record
    return sorted(
        records.values(), key=lambda item: (item["created_at"], item["message_id"])
    )


def load_state(exports_dir: Path) -> dict:
    states = []
    for path in sorted(exports_dir.glob("crawl_*.state.json")):
        with path.open(encoding="utf-8") as handle:
            states.append(json.load(handle))
    for state in reversed(states):
        if state.get("complete"):
            return state
    return states[-1] if states else {}


def unique_author_slugs(author_names: dict[int, str]) -> dict[int, str]:
    slugs: dict[int, str] = {}
    used: set[str] = set()
    for author_id, name in sorted(author_names.items()):
        base = slugify(name)
        candidate = base
        if candidate in used:
            candidate = f"{base}-{author_id}"
        counter = 2
        while candidate in used:
            candidate = f"{base}-{author_id}-{counter}"
            counter += 1
        used.add(candidate)
        slugs[author_id] = candidate
    return slugs


def choose_file_name(
    original_name: str, date: str, message_id: int, used: set[str]
) -> str:
    safe = safe_filename(original_name)
    stem = Path(safe).stem
    suffix = Path(safe).suffix
    if stem.lower() not in GENERIC_STEMS and safe not in used:
        used.add(safe)
        return safe
    candidate = f"{stem}__{date}{suffix}"
    if candidate not in used:
        used.add(candidate)
        return candidate
    candidate = f"{stem}__{date}__{message_id}{suffix}"
    if candidate not in used:
        used.add(candidate)
        return candidate
    counter = 2
    while True:
        candidate = f"{stem}__{date}__{message_id}_{counter}{suffix}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        counter += 1


def sensitive_reason(path: Path) -> str | None:
    data = path.read_bytes()[:2_000_000]
    for label, pattern in SENSITIVE_PATTERNS:
        if pattern.search(data):
            return label
    return None


def collect_archive(
    exports_dir: Path, max_file_bytes: int
) -> tuple[list[dict], list[Author], list[Exclusion], dict, Counter]:
    records = load_records(exports_dir)
    if not records:
        raise SystemExit(f"No batch_*.jsonl files found under {exports_dir}")

    author_names = {
        int(record["author"]["id"]): record["author"]["name"] for record in records
    }
    slugs = unique_author_slugs(author_names)
    authors = {
        author_id: Author(id=author_id, name=name, slug=slugs[author_id])
        for author_id, name in author_names.items()
    }

    embed_titles: dict[str, str] = {}
    for record in records:
        for embed in record.get("embeds", []):
            url = embed.get("url")
            title = embed.get("title")
            if url and title:
                embed_titles.setdefault(url, title)

    exclusions: list[Exclusion] = []
    attachment_stats: Counter = Counter()
    used_file_names: dict[int, set[str]] = defaultdict(set)
    seen_file_hashes: dict[int, set[str]] = defaultdict(set)
    seen_snippet_hashes: dict[int, set[str]] = defaultdict(set)
    author_links: dict[int, dict[str, ExternalLink]] = defaultdict(dict)

    for record in records:
        author = authors[int(record["author"]["id"])]
        author.messages += 1
        if "code" in record.get("kinds", []):
            author.code_messages += 1
        date = record["created_at"][:10]
        message_id = int(record["message_id"])
        jump_url = record["jump_url"]

        for attachment in record.get("attachments", []):
            downloaded_path = attachment.get("downloaded_path")
            if not downloaded_path:
                if attachment.get("is_media"):
                    attachment_stats["media"] += 1
                elif (
                    attachment.get("archive_like")
                    or attachment.get("download_skipped") == "archive_disabled"
                ):
                    attachment_stats["archive"] += 1
                else:
                    attachment_stats["other"] += 1
                continue
            source_path = Path(downloaded_path)
            if not source_path.exists():
                attachment_stats["missing"] += 1
                continue
            attachment_stats["downloaded"] += 1
            original_name = attachment["filename"]
            size = int(attachment.get("size") or source_path.stat().st_size)
            if original_name.lower() in PII_FILENAMES:
                exclusions.append(
                    Exclusion(
                        author.name,
                        original_name,
                        "personal data storage dump",
                        size,
                        jump_url,
                    )
                )
                continue
            if size > max_file_bytes:
                exclusions.append(
                    Exclusion(
                        author.name,
                        original_name,
                        f"oversized file (> {human_size(max_file_bytes)})",
                        size,
                        jump_url,
                    )
                )
                continue
            reason = sensitive_reason(source_path)
            if reason:
                exclusions.append(
                    Exclusion(
                        author.name,
                        original_name,
                        f"sensitive content: {reason}",
                        size,
                        jump_url,
                    )
                )
                continue
            digest = sha256_file(source_path)
            if digest in seen_file_hashes[author.id]:
                exclusions.append(
                    Exclusion(
                        author.name, original_name, "exact duplicate", size, jump_url
                    )
                )
                continue
            seen_file_hashes[author.id].add(digest)
            public_name = choose_file_name(
                original_name, date, message_id, used_file_names[author.id]
            )
            relative_path = f"authors/{author.slug}/files/{public_name}"
            author.files.append(
                FileArtifact(
                    original_name=original_name,
                    public_name=public_name,
                    relative_path=relative_path,
                    source_path=source_path,
                    size=size,
                    sha256=digest,
                    date=date,
                    message_id=message_id,
                    jump_url=jump_url,
                )
            )

        for index, block in enumerate(record.get("code_blocks", []), start=1):
            body = block.get("body", "")
            if not body.strip():
                continue
            digest = sha256_bytes(body.encode("utf-8"))
            if digest in seen_snippet_hashes[author.id]:
                continue
            seen_snippet_hashes[author.id].add(digest)
            extension = extension_for_language(block.get("lang", ""))
            public_name = f"snippet__{date}__{message_id}__{index:02d}{extension}"
            relative_path = f"authors/{author.slug}/snippets/{public_name}"
            author.snippets.append(
                Snippet(
                    public_name=public_name,
                    relative_path=relative_path,
                    body=body,
                    sha256=digest,
                    extension=extension,
                    date=date,
                    message_id=message_id,
                    jump_url=jump_url,
                )
            )

        for url in record.get("script_links", []):
            existing = author_links[author.id].get(url)
            if existing:
                existing.occurrences += 1
                continue
            author_links[author.id][url] = ExternalLink(
                url=url,
                title=embed_titles.get(url) or link_label(url),
                host=urlsplit(url).netloc.lower().removeprefix("www."),
                date=date,
                message_id=message_id,
                jump_url=jump_url,
            )

    for author_id, links in author_links.items():
        authors[author_id].links = list(links.values())

    ordered_authors = sorted(
        authors.values(),
        key=lambda author: (
            -author.content_count,
            -len(author.files),
            -len(author.snippets),
            -len(author.links),
            -author.code_messages,
            author.name.lower(),
        ),
    )
    return (
        records,
        ordered_authors,
        exclusions,
        load_state(exports_dir),
        attachment_stats,
    )


def author_stats_line(author: Author) -> str:
    return (
        f"Messages: **{author.messages}** · Code messages: **{author.code_messages}** · "
        f"Files: **{len(author.files)}** · Snippets: **{len(author.snippets)}** · "
        f"External links: **{len(author.links)}**"
    )


def render_file_table(author: Author, prefix: str) -> list[str]:
    if not author.files:
        return []
    lines = [
        "| File | Date | Size | SHA-256 | Source |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for artifact in author.files:
        lines.append(
            f"| {md_link(artifact.public_name, f'{prefix}/files/{artifact.public_name}')} "
            f"| {artifact.date} | {human_size(artifact.size)} "
            f"| `{artifact.sha256[:12]}` "
            f"| {message_link(artifact.message_id, artifact.jump_url)} |"
        )
    return lines


def render_snippet_table(author: Author, prefix: str) -> list[str]:
    if not author.snippets:
        return []
    lines = [
        "| Snippet | Language | Date | Source |",
        "| --- | --- | --- | --- |",
    ]
    for snippet in author.snippets:
        lines.append(
            f"| {md_link(snippet.public_name, f'{prefix}/snippets/{snippet.public_name}')} "
            f"| {language_label(snippet.extension)} | {snippet.date} "
            f"| {message_link(snippet.message_id, snippet.jump_url)} |"
        )
    return lines


def render_link_table(author: Author) -> list[str]:
    if not author.links:
        return []
    lines = [
        "| Link | Host | Date | Source |",
        "| --- | --- | --- | --- |",
    ]
    for link in author.links:
        suffix = f" ({link.occurrences}×)" if link.occurrences > 1 else ""
        lines.append(
            f"| {md_link(link.title, link.url)}{suffix} | {md_cell(link.host)} "
            f"| {link.date} | {message_link(link.message_id, link.jump_url)} |"
        )
    return lines


def render_author_section(author: Author) -> list[str]:
    lines = [
        f'<a id="author-{author.slug}"></a>',
        f"### {md_cell(author.name)}",
        "",
        author_stats_line(author),
        "",
        f"[Author folder](authors/{author.slug}/README.md)",
        "",
    ]
    file_table = render_file_table(author, f"authors/{author.slug}")
    snippet_table = render_snippet_table(author, f"authors/{author.slug}")
    link_table = render_link_table(author)
    if file_table:
        lines.extend(["#### Files", "", *file_table, ""])
    if snippet_table:
        lines.extend(["#### Snippets", "", *snippet_table, ""])
    if link_table:
        lines.extend(["#### External links", "", *link_table, ""])
    return lines


def render_author_readme(author: Author) -> str:
    lines = [
        f"# {author.name}",
        "",
        "[Back to archive index](../../README.md)",
        "",
        author_stats_line(author),
        "",
    ]
    file_table = render_file_table(author, ".")
    snippet_table = render_snippet_table(author, ".")
    link_table = render_link_table(author)
    if file_table:
        lines.extend(["## Files", "", *file_table, ""])
    if snippet_table:
        lines.extend(["## Snippets", "", *snippet_table, ""])
    if link_table:
        lines.extend(["## External links", "", *link_table, ""])
    lines.extend(
        [
            "---",
            "",
            "Files and snippets are provided for reference only and are not audited. "
            "See [NOTICE.md](../../NOTICE.md).",
            "",
        ]
    )
    return "\n".join(lines)


def thread_url(records: list[dict], state: dict) -> str:
    thread_id = state.get("thread_id")
    if not thread_id:
        thread_id = next(
            (
                record["channel_id"]
                for record in records
                if record.get("channel_id") != record["jump_url"].split("/")[4]
            ),
            records[0]["channel_id"],
        )
    guild_id = records[0]["jump_url"].split("/")[4]
    return f"https://discord.com/channels/{guild_id}/{thread_id}"


def render_main(
    records: list[dict],
    authors: list[Author],
    exclusions: list[Exclusion],
    state: dict,
    attachment_stats: Counter,
    max_file_bytes: int,
) -> str:
    content_authors = [author for author in authors if author.content_count]
    code_messages = sum(1 for record in records if "code" in record.get("kinds", []))
    fenced_total = sum(len(record.get("code_blocks", [])) for record in records)
    inline_total = sum(len(record.get("inline_code", [])) for record in records)
    link_total = sum(len(record.get("script_links", [])) for record in records)
    unique_link_urls = len({link.url for author in authors for link in author.links})
    included_files = sum(len(author.files) for author in authors)
    included_snippets = sum(len(author.snippets) for author in authors)
    pii_exclusions = [
        item for item in exclusions if item.reason.startswith("personal data")
    ]
    oversized_exclusions = [
        item for item in exclusions if item.reason.startswith("oversized")
    ]
    duplicate_exclusions = [
        item for item in exclusions if item.reason == "exact duplicate"
    ]
    sensitive_exclusions = [
        item
        for item in exclusions
        if item.reason.startswith("sensitive content") and item not in pii_exclusions
    ]
    date_min = records[0]["created_at"][:10]
    date_max = records[-1]["created_at"][:10]
    thread = thread_url(records, state)

    lines = [
        "# BattleMaps Community Code Archive",
        "",
        "Scripts, snippets, and project links shared by the community in the "
        f'[BattleMaps "Community Development" thread]({thread}). '
        "The archive is generated from the exported Discord thread. It does not include "
        "raw message dumps, media, archives, or personal data files.",
        "",
        "> These files are shared for reference only. They are not audited, and running "
        "unknown userscripts or programs is risky. See [NOTICE.md](NOTICE.md).",
        "",
        "## At a glance",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Thread records | {len(records):,} |",
        f"| Authors | {len(authors):,} |",
        f"| Date range | {date_min} to {date_max} |",
        f"| Code messages | {code_messages:,} |",
        f"| Fenced snippets captured | {fenced_total:,} |",
        f"| Inline snippets captured | {inline_total:,} |",
        f"| Script links captured | {link_total:,} |",
        f"| Unique script URLs | {unique_link_urls:,} |",
        f"| Downloaded files | {attachment_stats.get('downloaded', 0):,} |",
        f"| Included files | {included_files:,} |",
        f"| Included snippets | {included_snippets:,} |",
        f"| Authors with artifacts | {len(content_authors):,} |",
        f"| Media attachments excluded | {attachment_stats.get('media', 0):,} |",
        f"| Archives excluded | {attachment_stats.get('archive', 0):,} |",
        f"| Other non-script attachments excluded | {attachment_stats.get('other', 0):,} |",
        f"| Personal-data files excluded | {len(pii_exclusions):,} |",
        f"| Oversized files excluded | {len(oversized_exclusions):,} |",
        f"| Exact duplicate files excluded | {len(duplicate_exclusions):,} |",
        "",
    ]
    if state.get("batches_completed"):
        lines.extend(
            [
                f"The crawl completed {state['batches_completed']:,} batches and reached the "
                "start of the thread.",
                "",
            ]
        )

    lines.extend(
        [
            "## Contents",
            "",
            "- [Authors](#authors)",
            "- [Author details](#author-details)",
            "- [Other code contributors](#other-code-contributors)",
            "- [Excluded material](#excluded-material)",
            "- [Method](#method)",
            "- [Licensing and removal](#licensing-and-removal)",
            "- [Provenance data](sources.csv)",
            "",
            "## Authors",
            "",
            "| Author | Messages | Code messages | Files | Snippets | Links |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for author in content_authors:
        lines.append(
            f"| {md_link(author.name, f'authors/{author.slug}/README.md')} "
            f"| {author.messages:,} | {author.code_messages:,} "
            f"| {len(author.files):,} | {len(author.snippets):,} | {len(author.links):,} |"
        )

    lines.extend(["", "## Author details", ""])
    for author in content_authors:
        lines.extend(render_author_section(author))

    content_author_ids = {author.id for author in content_authors}
    inline_only: dict[int, list[dict]] = defaultdict(list)
    for record in records:
        author_id = int(record["author"]["id"])
        if author_id not in content_author_ids and record.get("inline_code"):
            inline_only[author_id].append(record)
    if inline_only:
        lines.extend(
            [
                "## Other code contributors",
                "",
                "These authors posted inline code only. Inline snippets are not exported as "
                "files; the source messages are linked instead.",
                "",
                "| Author | Inline messages | Source messages |",
                "| --- | ---: | --- |",
            ]
        )
        for author_id, author_records in sorted(
            inline_only.items(),
            key=lambda item: (-len(item[1]), item[1][0]["author"]["name"].lower()),
        ):
            name = author_records[0]["author"]["name"]
            source_links = ", ".join(
                message_link(int(record["message_id"]), record["jump_url"])
                for record in author_records
            )
            lines.append(
                f"| {md_cell(name)} | {len(author_records)} | {source_links} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Excluded material",
            "",
            "The archive intentionally excludes raw conversation text, media, archives, and "
            "data dumps that are not useful as community code. This keeps the repository "
            "focused and avoids republishing personal data.",
            "",
            "| Material | Count | Reason |",
            "| --- | ---: | --- |",
            f"| Media attachments | {attachment_stats.get('media', 0):,} "
            "| Images, video, audio, and other media |",
            f"| Archives | {attachment_stats.get('archive', 0):,} "
            "| ZIP/7z archives, including music packs |",
            f"| Other non-script attachments | {attachment_stats.get('other', 0):,} "
            "| PDF, AHK, DLL, spreadsheets, and replay files |",
            f"| Personal-data files | {len(pii_exclusions):,} "
            "| Storage dumps containing email addresses |",
            f"| Oversized files | {len(oversized_exclusions):,} "
            f"| Files larger than {human_size(max_file_bytes)} |",
            f"| Sensitive-content files | {len(sensitive_exclusions):,} "
            "| Files with credentials or email addresses |",
            f"| Exact duplicates | {len(duplicate_exclusions):,} "
            "| Same author and identical SHA-256 |",
        ]
    )
    specific_exclusions = pii_exclusions + oversized_exclusions + duplicate_exclusions
    specific_exclusions += sensitive_exclusions
    if specific_exclusions:
        lines.extend(
            [
                "",
                "| Excluded file | Author | Reason | Size | Source |",
                "| --- | --- | --- | ---: | --- |",
            ]
        )
        for item in specific_exclusions:
            lines.append(
                f"| {md_cell(item.name)} | {md_cell(item.author)} | {md_cell(item.reason)} "
                f"| {human_size(item.size)} | {md_link('message', item.message_url)} |"
            )

    lines.extend(
        [
            "",
            "## Method",
            "",
            '- Source: the exported "Community Development" thread; every message was '
            "captured with a resumable crawl that reached the start of the thread.",
            "- Message classification and link extraction are generated from the Discord "
            "export; artifacts are copied only when they were downloaded under the "
            "script/text filter.",
            "- Media and archives were never downloaded. Non-script attachments were skipped.",
            "- Files larger than the size limit are excluded and linked through their source "
            "message instead.",
            "- Exact duplicate files from the same author are collapsed by SHA-256.",
            "- Fenced code blocks are saved as snippets. Untagged blocks are saved as `.txt` "
            "and should be reviewed before use.",
            "- Inline code is counted but not exported because it is mostly short commands "
            "and field references; it remains available through the source messages.",
            "- Filenames are sanitized. When a name repeats, the date and message ID are "
            "added so versions do not overwrite each other.",
            "",
            "## Licensing and removal",
            "",
            "Copyright remains with the original authors. This repository does not grant a "
            "license to third-party files. If a file carries its own license header, that "
            "license applies. Authors can request corrections or removal through the "
            "process in [NOTICE.md](NOTICE.md).",
            "",
            "Provenance for every included file, snippet, and link is in [sources.csv](sources.csv).",
            "",
        ]
    )
    return "\n".join(lines)


def notice_text() -> str:
    return """# Notice

This directory indexes scripts, snippets, and project links shared by community members in the BattleMaps Discord "Community Development" thread.

## Copyright and licensing

Copyright remains with the original authors. Inclusion here does not transfer ownership and does not grant a license unless the author has stated one. If a file contains its own license header, that license applies to that file.

The BattleMaps Bot source code and this archive are separate. This notice covers the contents of `community-code/`.

## No warranty

The files are provided for reference only. They have not been audited. Do not run unknown userscripts, scripts, or binaries without reviewing them first.

## Corrections and removal

If you are an author and want a file corrected, credited differently, or removed, open an issue in this repository or contact the maintainer. Removal requests will be honored.

## Excluded material

Raw Discord messages, media, archives, personal-data dumps, and oversized data dumps are not published here. See the main [README](README.md) for details.
"""


def write_sources_csv(path: Path, authors: list[Author]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                "kind",
                "author",
                "author_id",
                "date",
                "message_id",
                "message_url",
                "name",
                "path",
                "bytes",
                "sha256",
                "language",
                "external_url",
            ]
        )
        for author in authors:
            for artifact in sorted(
                author.files, key=lambda item: (item.date, item.public_name)
            ):
                writer.writerow(
                    [
                        "file",
                        author.name,
                        author.id,
                        artifact.date,
                        artifact.message_id,
                        artifact.jump_url,
                        artifact.original_name,
                        artifact.relative_path,
                        artifact.size,
                        artifact.sha256,
                        "",
                        "",
                    ]
                )
            for snippet in sorted(
                author.snippets, key=lambda item: (item.date, item.public_name)
            ):
                writer.writerow(
                    [
                        "snippet",
                        author.name,
                        author.id,
                        snippet.date,
                        snippet.message_id,
                        snippet.jump_url,
                        snippet.public_name,
                        snippet.relative_path,
                        len(snippet.body.encode("utf-8")),
                        snippet.sha256,
                        language_label(snippet.extension),
                        "",
                    ]
                )
            for link in sorted(author.links, key=lambda item: (item.date, item.url)):
                writer.writerow(
                    [
                        "link",
                        author.name,
                        author.id,
                        link.date,
                        link.message_id,
                        link.jump_url,
                        link.title,
                        "",
                        "",
                        "",
                        "",
                        link.url,
                    ]
                )


def write_archive(
    output_dir: Path,
    records: list[dict],
    authors: list[Author],
    exclusions: list[Exclusion],
    state: dict,
    attachment_stats: Counter,
    max_file_bytes: int,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    authors_dir = output_dir / "authors"
    if authors_dir.exists():
        shutil.rmtree(authors_dir)
    authors_dir.mkdir()

    (output_dir / "README.md").write_text(
        render_main(
            records, authors, exclusions, state, attachment_stats, max_file_bytes
        ),
        encoding="utf-8",
    )
    (output_dir / "NOTICE.md").write_text(notice_text(), encoding="utf-8")
    write_sources_csv(output_dir / "sources.csv", authors)

    for author in authors:
        if not author.content_count:
            continue
        author_dir = authors_dir / author.slug
        author_dir.mkdir()
        (author_dir / "README.md").write_text(
            render_author_readme(author), encoding="utf-8"
        )
        if author.files:
            files_dir = author_dir / "files"
            files_dir.mkdir()
            for artifact in author.files:
                shutil.copyfile(artifact.source_path, files_dir / artifact.public_name)
        if author.snippets:
            snippets_dir = author_dir / "snippets"
            snippets_dir.mkdir()
            for snippet in author.snippets:
                (snippets_dir / snippet.public_name).write_text(
                    snippet.body, encoding="utf-8"
                )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the public community code archive from exported Discord JSONL."
    )
    parser.add_argument("--exports", type=Path, default=Path("exports"))
    parser.add_argument("--output", type=Path, default=Path("community-code"))
    parser.add_argument("--max-file-bytes", type=int, default=MAX_FILE_BYTES)
    args = parser.parse_args()

    records, authors, exclusions, state, attachment_stats = collect_archive(
        args.exports, args.max_file_bytes
    )
    write_archive(
        args.output,
        records,
        authors,
        exclusions,
        state,
        attachment_stats,
        args.max_file_bytes,
    )
    included_files = sum(len(author.files) for author in authors)
    included_snippets = sum(len(author.snippets) for author in authors)
    included_links = sum(len(author.links) for author in authors)
    content_authors = sum(1 for author in authors if author.content_count)
    print(
        f"Wrote {args.output}: {content_authors} authors, {included_files} files, "
        f"{included_snippets} snippets, {included_links} links"
    )


if __name__ == "__main__":
    main()
