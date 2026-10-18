#!/usr/bin/env python3
"""Mirror downloads.claude.ai installers to versioned GitHub Releases.

Subcommands
-----------
probe    Resolve the live artifact matrix (version API + science aliases).
publish  Download changed artifacts, verify them, publish release assets,
         and regenerate docs/data/manifest.json (+ manifest.js).
verify   Validate the generated manifest.

Standard library only.  Network writes happen exclusively through ``gh``
and ``curl`` subprocesses so both can be faked in tests.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import html
import http.client
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None  # type: ignore[assignment]

SCHEMA_VERSION = 1
USER_AGENT = "claude-downloads-mirror/1.0 (+https://github.com/)"
DEFAULT_MAX_ASSET_BYTES = 2_147_483_648
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
VERSION_RE = re.compile(
    r"^[0-9]+(?:\.[0-9A-Za-z]+)+(?:[-+][0-9A-Za-z][0-9A-Za-z.-]*)?$"
)

PRODUCT_IDS = {
    "desktop": "claude-desktop",
    "science": "claude-science",
    "code": "claude-code",
    "claude-code": "claude-code",
}
PRODUCT_ORDER = ["claude-desktop", "claude-science", "claude-code"]
PRODUCT_NAMES = {
    "claude-desktop": "Claude Desktop",
    "claude-science": "Claude Science",
    "claude-code": "Claude Code",
}
OS_ORDER = {"macOS": 0, "Windows": 1, "Linux": 2}


class MirrorError(Exception):
    """A user-facing mirror failure."""


# ---------------------------------------------------------------------------
# Artifact definitions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArtifactDef:
    id: str
    product: str
    os: str
    arch: str
    variant: str
    suffix: str
    kind: str  # "desktop" | "science" | "code"
    endpoint_path: str = ""  # desktop: <platform>/<arch>/<variant>; code: <platform>
    alias: str = ""  # science: latest alias filename
    hash_group: str = ""  # science manifest group: dmg_sha256 | sha256
    hash_key: str = ""  # science manifest key: darwin-arm64 | windows-x64 | ...

    def friendly_name(self, version: str) -> str:
        prefix = {
            "desktop": "Claude-Desktop",
            "science": "Claude-Science",
            "code": "Claude-Code",
        }.get(self.kind, "Claude")
        return f"{prefix}-{version}-{self.suffix}"

    def latest_url(self, desktop_api: str, science_base: str) -> str:
        if self.kind == "desktop":
            return f"{desktop_api}/{self.endpoint_path}/latest"
        if self.kind == "science":
            return f"{science_base}/{self.alias}"
        return ""


DESKTOP_DEFS: list[ArtifactDef] = [
    ArtifactDef(
        "macos-universal", "claude-desktop", "macOS", "Universal", "Installer",
        "macOS-universal.dmg", "desktop", "darwin/universal/dmg",
    ),
    ArtifactDef(
        "macos-intel-offline", "claude-desktop", "macOS", "Intel", "Offline Installer",
        "macOS-intel-offline.dmg", "desktop", "darwin/x64/offline",
    ),
    ArtifactDef(
        "macos-apple-silicon-offline", "claude-desktop", "macOS", "Apple Silicon",
        "Offline Installer", "macOS-apple-silicon-offline.dmg", "desktop",
        "darwin/arm64/offline",
    ),
    ArtifactDef(
        "windows-x64-setup", "claude-desktop", "Windows", "x64", "Online Installer",
        "Windows-x64-setup.exe", "desktop", "win32/x64/setup",
    ),
    ArtifactDef(
        "windows-arm64-setup", "claude-desktop", "Windows", "arm64", "Online Installer",
        "Windows-arm64-setup.exe", "desktop", "win32/arm64/setup",
    ),
    ArtifactDef(
        "windows-x64-exe", "claude-desktop", "Windows", "x64", "Installer",
        "Windows-x64.exe", "desktop", "win32/x64/exe",
    ),
    ArtifactDef(
        "windows-arm64-exe", "claude-desktop", "Windows", "arm64", "Installer",
        "Windows-arm64.exe", "desktop", "win32/arm64/exe",
    ),
    ArtifactDef(
        "windows-x64-msix", "claude-desktop", "Windows", "x64", "MSIX",
        "Windows-x64.msix", "desktop", "win32/x64/msix",
    ),
    ArtifactDef(
        "windows-arm64-msix", "claude-desktop", "Windows", "arm64", "MSIX",
        "Windows-arm64.msix", "desktop", "win32/arm64/msix",
    ),
    ArtifactDef(
        "windows-x64-offline", "claude-desktop", "Windows", "x64", "Offline MSIX",
        "Windows-x64-offline.msix", "desktop", "win32/x64/offline",
    ),
    ArtifactDef(
        "windows-arm64-offline", "claude-desktop", "Windows", "arm64", "Offline MSIX",
        "Windows-arm64-offline.msix", "desktop", "win32/arm64/offline",
    ),
    ArtifactDef(
        "linux-x64-deb", "claude-desktop", "Linux", "x64", "Debian Package",
        "Linux-x64.deb", "desktop", "linux/x64/deb",
    ),
    ArtifactDef(
        "linux-arm64-deb", "claude-desktop", "Linux", "arm64", "Debian Package",
        "Linux-arm64.deb", "desktop", "linux/arm64/deb",
    ),
]

SCIENCE_DEFS: list[ArtifactDef] = [
    ArtifactDef(
        "science-macos-apple-silicon", "claude-science", "macOS", "Apple Silicon",
        "Installer", "macOS-apple-silicon.dmg", "science", alias="mac-arm64.dmg",
        hash_group="dmg_sha256", hash_key="darwin-arm64",
    ),
    ArtifactDef(
        "science-macos-intel", "claude-science", "macOS", "Intel", "Installer",
        "macOS-intel.dmg", "science", alias="mac-x64.dmg",
        hash_group="dmg_sha256", hash_key="darwin-x64",
    ),
    ArtifactDef(
        "science-windows-x64", "claude-science", "Windows", "x64", "Installer",
        "Windows-x64.exe", "science", alias="windows-x64.exe",
        hash_group="sha256", hash_key="windows-x64",
    ),
    ArtifactDef(
        "science-windows-arm64", "claude-science", "Windows", "arm64", "Installer",
        "Windows-arm64.exe", "science", alias="windows-arm64.exe",
        hash_group="sha256", hash_key="windows-arm64",
    ),
    ArtifactDef(
        "science-linux-x64", "claude-science", "Linux", "x64", "Installer",
        "Linux-x64", "science", alias="linux-x64",
        hash_group="sha256", hash_key="linux-x64",
    ),
]

CODE_DEFS: list[ArtifactDef] = [
    ArtifactDef(
        "code-macos-apple-silicon", "claude-code", "macOS", "Apple Silicon",
        "Binary", "macOS-arm64", "code", endpoint_path="darwin-arm64",
    ),
    ArtifactDef(
        "code-macos-intel", "claude-code", "macOS", "Intel",
        "Binary", "macOS-intel", "code", endpoint_path="darwin-x64",
    ),
    ArtifactDef(
        "code-windows-x64", "claude-code", "Windows", "x64",
        "Binary", "Windows-x64.exe", "code", endpoint_path="win32-x64",
    ),
    ArtifactDef(
        "code-windows-arm64", "claude-code", "Windows", "arm64",
        "Binary", "Windows-arm64.exe", "code", endpoint_path="win32-arm64",
    ),
    ArtifactDef(
        "code-linux-x64", "claude-code", "Linux", "x64",
        "Binary", "Linux-x64", "code", endpoint_path="linux-x64",
    ),
    ArtifactDef(
        "code-linux-x64-musl", "claude-code", "Linux", "x64 (musl)",
        "Binary", "Linux-x64-musl", "code", endpoint_path="linux-x64-musl",
    ),
    ArtifactDef(
        "code-linux-arm64", "claude-code", "Linux", "arm64",
        "Binary", "Linux-arm64", "code", endpoint_path="linux-arm64",
    ),
    ArtifactDef(
        "code-linux-arm64-musl", "claude-code", "Linux", "arm64 (musl)",
        "Binary", "Linux-arm64-musl", "code", endpoint_path="linux-arm64-musl",
    ),
]

DEFS_BY_PRODUCT: dict[str, list[ArtifactDef]] = {
    "claude-desktop": DESKTOP_DEFS,
    "claude-science": SCIENCE_DEFS,
    "claude-code": CODE_DEFS,
}
ALL_DEFS: list[ArtifactDef] = DESKTOP_DEFS + SCIENCE_DEFS + CODE_DEFS
DEF_BY_ID: dict[str, ArtifactDef] = {d.id: d for d in ALL_DEFS}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Config:
    owner: str
    repo: str
    branch: str
    site_dir: str
    desktop_api: str
    science_base: str
    code_base: str
    source_site: str
    desktop_tag_prefix: str
    science_tag_prefix: str
    code_tag_prefix: str
    max_asset_bytes: int

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "Config":
        try:
            source = raw["source"]
            release = raw["release"]
            cfg = cls(
                owner=str(raw["owner"]),
                repo=str(raw["repo"]),
                branch=str(raw.get("branch", "main")),
                site_dir=str(raw.get("site_dir", "docs")),
                desktop_api=str(source["desktop_api"]).rstrip("/"),
                science_base=str(source["science_base"]).rstrip("/"),
                code_base=str(
                    source.get(
                        "code_base",
                        "https://downloads.claude.ai/claude-code-releases",
                    )
                ).rstrip("/"),
                source_site=str(source["site"]).rstrip("/"),
                desktop_tag_prefix=str(release.get("desktop_tag_prefix", "desktop-v")),
                science_tag_prefix=str(release.get("science_tag_prefix", "science-v")),
                code_tag_prefix=str(release.get("code_tag_prefix", "code-v")),
                max_asset_bytes=int(
                    release.get("max_asset_bytes", DEFAULT_MAX_ASSET_BYTES)
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MirrorError(f"invalid mirrorrc.json: {exc}") from exc
        if not cfg.owner or not cfg.repo:
            raise MirrorError("mirrorrc.json: owner and repo must be non-empty")
        return cfg

    @property
    def tag_prefixes(self) -> dict[str, str]:
        return {
            "claude-desktop": self.desktop_tag_prefix,
            "claude-science": self.science_tag_prefix,
            "claude-code": self.code_tag_prefix,
        }

    @property
    def site_url(self) -> str:
        return derive_site_url(self.owner, self.repo)

    def release_url(self, tag: str) -> str:
        return f"https://github.com/{self.owner}/{self.repo}/releases/tag/{tag}"

    def download_url(self, tag: str, filename: str) -> str:
        return (
            f"https://github.com/{self.owner}/{self.repo}/releases/download/"
            f"{tag}/{urllib.parse.quote(filename)}"
        )


def derive_site_url(owner: str, repo: str) -> str:
    if repo.lower().endswith(".github.io"):
        return f"https://{owner}.github.io/"
    return f"https://{owner}.github.io/{repo}/"


def load_config(path: Path) -> Config:
    try:
        with path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except OSError as exc:
        raise MirrorError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise MirrorError(f"invalid JSON in {path}: {exc}") from exc
    return Config.from_dict(raw)


# ---------------------------------------------------------------------------
# HTTP seam
# ---------------------------------------------------------------------------


@dataclass
class HeadResponse:
    status: int
    headers: dict[str, str]
    url: str

    def header(self, name: str) -> str | None:
        return self.headers.get(name.lower())


class UrllibHttp:
    """Small read-only HTTP client used for version/alias discovery."""

    RETRIES = 5
    RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

    def __init__(self, timeout: float = 45.0, retry_delay: float = 0.8) -> None:
        self.timeout = timeout
        self.retry_delay = retry_delay

    def _request(self, url: str, method: str) -> Any:
        req = urllib.request.Request(
            url,
            method=method,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        return urllib.request.urlopen(req, timeout=self.timeout)

    def _network_retry(self, exc: BaseException, attempt: int) -> None:
        if attempt + 1 >= self.RETRIES:
            raise MirrorError(f"network error: {exc}") from exc
        time.sleep(self.retry_delay * (attempt + 1))

    def get_json(self, url: str) -> dict[str, Any]:
        for attempt in range(self.RETRIES):
            try:
                with self._request(url, "GET") as resp:
                    body = resp.read()
                break
            except urllib.error.HTTPError as exc:
                if exc.code in self.RETRYABLE_STATUS and attempt + 1 < self.RETRIES:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                snippet = exc.read(300).decode("utf-8", "replace")
                raise MirrorError(f"GET {url} failed: HTTP {exc.code} {snippet}") from exc
            except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
                self._network_retry(exc, attempt)
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MirrorError(f"GET {url} returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise MirrorError(f"GET {url} returned a non-object JSON payload")
        return payload

    def get_text(self, url: str) -> str:
        for attempt in range(self.RETRIES):
            try:
                with self._request(url, "GET") as resp:
                    body = resp.read()
                break
            except urllib.error.HTTPError as exc:
                if exc.code in self.RETRYABLE_STATUS and attempt + 1 < self.RETRIES:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                snippet = exc.read(300).decode("utf-8", "replace")
                raise MirrorError(f"GET {url} failed: HTTP {exc.code} {snippet}") from exc
            except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
                self._network_retry(exc, attempt)
        try:
            return body.decode("utf-8").strip()
        except UnicodeDecodeError as exc:
            raise MirrorError(f"GET {url} returned non-UTF-8 text") from exc

    def head(self, url: str) -> HeadResponse:
        for attempt in range(self.RETRIES):
            try:
                with self._request(url, "HEAD") as resp:
                    headers = {k.lower(): v for k, v in resp.headers.items()}
                    return HeadResponse(int(resp.status), headers, resp.geturl() or url)
            except urllib.error.HTTPError as exc:
                if exc.code in self.RETRYABLE_STATUS and attempt + 1 < self.RETRIES:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                headers = (
                    {k.lower(): v for k, v in exc.headers.items()}
                    if exc.headers
                    else {}
                )
                return HeadResponse(int(exc.code), headers, url)
            except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
                self._network_retry(exc, attempt)
        raise MirrorError(f"HEAD {url} failed")

    def get_range(self, url: str) -> HeadResponse:
        """Fetch the first byte with ``Range: bytes=0-0`` to discover the size.

        Some GCS release endpoints omit ``Content-Length`` on HEAD but do return
        ``Content-Range: bytes 0-0/<total>`` for a ranged GET.
        """
        req = urllib.request.Request(
            url,
            method="GET",
            headers={
                "User-Agent": USER_AGENT,
                "Range": "bytes=0-0",
                "Accept-Encoding": "identity",
            },
        )
        for attempt in range(self.RETRIES):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    headers = {k.lower(): v for k, v in resp.headers.items()}
                    resp.read(1)  # never pull the whole asset
                    return HeadResponse(int(resp.status), headers, resp.geturl() or url)
            except urllib.error.HTTPError as exc:
                if exc.code in self.RETRYABLE_STATUS and attempt + 1 < self.RETRIES:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                headers = (
                    {k.lower(): v for k, v in exc.headers.items()}
                    if exc.headers
                    else {}
                )
                return HeadResponse(int(exc.code), headers, url)
            except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
                self._network_retry(exc, attempt)
        raise MirrorError(f"ranged GET {url} failed")


def header_size(headers: Mapping[str, str]) -> int | None:
    """Extract a byte size from HEAD headers (GCS omits Content-Length on HEAD)."""
    for name in ("content-length", "x-goog-stored-content-length"):
        value = headers.get(name)
        if value is None:
            continue
        try:
            size = int(value.strip())
        except (TypeError, ValueError):
            continue
        if size >= 0:
            return size
    return None


def content_range_total(headers: Mapping[str, str]) -> int | None:
    value = headers.get("content-range")
    if not value:
        return None
    match = re.match(r"bytes\s+\d+-\d+/(\d+)", value.strip())
    return int(match.group(1)) if match else None


def size_from_headers(headers: Mapping[str, str]) -> int | None:
    size = header_size(headers)
    return size if size is not None else content_range_total(headers)


def is_relay_only(size: int | None, max_bytes: int) -> bool:
    """Strict GitHub boundary: anything >= the cap cannot be a release asset."""
    return size is not None and size >= max_bytes


def relay_url_for(artifact_id: str) -> str:
    return f"relay/{artifact_id}.html"


# ---------------------------------------------------------------------------
# Subprocess / transfer / GitHub seams
# ---------------------------------------------------------------------------


@dataclass
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


class SubprocessRunner:
    def run(self, cmd: Sequence[str], cwd: Path | None = None) -> CommandResult:
        try:
            proc = subprocess.run(
                list(cmd),
                cwd=str(cwd) if cwd else None,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            return CommandResult(127, "", f"cannot execute {cmd[0]}: {exc}")
        return CommandResult(proc.returncode, proc.stdout, proc.stderr)


def sha256_file(path: Path, chunk_size: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


class CurlTransfer:
    """Resumable downloader backed by ``curl -C -``."""

    def __init__(self, runner: Any) -> None:
        self.runner = runner

    @staticmethod
    def command(url: str, part: Path) -> list[str]:
        return [
            "curl",
            "--fail",
            "--location",
            "--retry", "3",
            "--retry-delay", "2",
            "--continue-at", "-",
            "--output", str(part),
            url,
        ]

    def download(self, url: str, dest: Path, expected_size: int | None) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")

        # Reuse/stash an existing (possibly partial) download.
        if dest.exists():
            size = dest.stat().st_size
            if expected_size is not None and size == expected_size:
                return
            if expected_size is not None and size < expected_size:
                os.replace(dest, part)
            else:
                dest.unlink()

        if part.exists():
            size = part.stat().st_size
            if expected_size is not None and size == expected_size:
                os.replace(part, dest)
                return
            if expected_size is None or size > expected_size:
                part.unlink()

        result = self.runner.run(self.command(url, part))
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()[-500:]
            raise MirrorError(f"curl failed for {url}: {detail or 'exit ' + str(result.returncode)}")

        if not part.exists():
            raise MirrorError(f"curl reported success but produced no file for {url}")
        if expected_size is not None:
            actual = part.stat().st_size
            if actual != expected_size:
                raise MirrorError(
                    f"size mismatch for {url}: expected {expected_size} bytes, got {actual}"
                )
        os.replace(part, dest)


class GhCli:
    """GitHub Releases client backed by the maintainer's ``gh`` login."""

    def __init__(self, runner: Any, owner: str, repo: str, cwd: Path | None = None) -> None:
        self.runner = runner
        self.owner = owner
        self.repo = repo
        self.cwd = cwd

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.repo}"

    def _run(self, cmd: Sequence[str], what: str) -> CommandResult:
        result = self.runner.run(cmd, cwd=self.cwd)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()[-800:]
            raise MirrorError(f"{what} failed: {detail or 'exit ' + str(result.returncode)}")
        return result

    def release_exists(self, tag: str) -> bool:
        result = self.runner.run(
            ["gh", "api", f"repos/{self.slug}/releases/tags/{tag}"], cwd=self.cwd
        )
        if result.returncode == 0:
            return True
        text = (result.stderr or "") + (result.stdout or "")
        if "404" in text or "Not Found" in text or "not found" in text:
            return False
        detail = text.strip()[-800:]
        raise MirrorError(f"gh release lookup failed for {tag}: {detail}")

    def create_release(self, tag: str, title: str, notes: str, target: str) -> None:
        self._run(
            [
                "gh", "release", "create", tag,
                "--repo", self.slug,
                "--title", title,
                "--notes", notes,
                "--target", target,
                "--latest=false",
            ],
            f"create release {tag}",
        )

    def asset_names(self, tag: str) -> set[str]:
        result = self._run(
            [
                "gh", "api", f"repos/{self.slug}/releases/tags/{tag}",
                "--jq", ".assets[].name",
            ],
            f"list assets for {tag}",
        )
        return {line.strip() for line in result.stdout.splitlines() if line.strip()}

    def upload(self, tag: str, path: Path, *, clobber: bool = False) -> None:
        cmd = [
            "gh", "release", "upload", tag, str(path),
            "--repo", self.slug,
        ]
        if clobber:
            cmd.insert(5, "--clobber")
        self._run(cmd, f"upload {path.name} to {tag}")


# ---------------------------------------------------------------------------
# Live resolution
# ---------------------------------------------------------------------------


@dataclass
class LiveArtifact:
    definition: ArtifactDef
    version: str
    source_url: str
    source_filename: str
    size: int | None
    content_disposition: str = ""
    expected_sha256: str | None = None

    @property
    def filename(self) -> str:
        return self.definition.friendly_name(self.version)


@dataclass
class LiveProduct:
    id: str
    version: str
    tag: str
    artifacts: list[LiveArtifact] = field(default_factory=list)

    @property
    def name(self) -> str:
        return PRODUCT_NAMES[self.id]


def _validate_version(version: str, source: str) -> str:
    if not VERSION_RE.match(version):
        raise MirrorError(f"unexpected version {version!r} from {source}")
    return version


def parse_content_disposition_filename(value: str) -> str | None:
    if not value:
        return None
    match = re.search(
        r"filename\*?=(?:UTF-8'')?\"?([^\";]+)\"?", value, re.IGNORECASE
    )
    return match.group(1).strip() if match else None


def parse_science_version(filename: str, source: str) -> str:
    """Parse ``Claude-Science-0.1.63[-Intel].dmg`` / ``claude-science-0.1.63-linux-x64``."""
    name = urllib.parse.unquote(Path(filename).name)
    patterns = (
        r"^[Cc]laude-[Ss]cience-(.+?)(?:-[Ii]ntel|-arm64)?\.(?:dmg|exe)$",
        r"^[Cc]laude-[Ss]cience-(.+?)-linux-(?:x64|arm64)$",
    )
    for pattern in patterns:
        match = re.match(pattern, name)
        if match:
            return _validate_version(match.group(1), source)
    raise MirrorError(f"cannot parse science version from {filename!r} ({source})")


class Resolver:
    def __init__(self, config: Config, http: Any) -> None:
        self.config = config
        self.http = http
        self._science_manifest_cache: dict[str, Any] | None = None
        self._code_version_cache: str | None = None
        self._code_manifest_cache: dict[str, Any] | None = None

    def resolve_one(self, definition: ArtifactDef) -> LiveArtifact:
        if definition.kind == "desktop":
            return self._resolve_desktop(definition)
        if definition.kind == "code":
            return self._resolve_code(definition)
        return self._resolve_science(definition)

    def _size_for(self, url: str, head: HeadResponse) -> int | None:
        size = size_from_headers(head.headers)
        if size is not None:
            return size
        try:
            ranged = self.http.get_range(url)
        except MirrorError:
            return None
        if ranged.status not in (200, 206):
            return None
        return size_from_headers(ranged.headers)

    def _resolve_desktop(self, definition: ArtifactDef) -> LiveArtifact:
        endpoint = definition.latest_url(self.config.desktop_api, self.config.science_base)
        payload = self.http.get_json(endpoint)
        version = _validate_version(str(payload.get("version", "")), endpoint)
        url = payload.get("url")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            raise MirrorError(f"desktop API {endpoint} returned no usable url")
        size = None
        try:
            head = self.http.head(url)
            if head.status == 200:
                size = self._size_for(url, head)
        except MirrorError:
            size = None
        return LiveArtifact(
            definition=definition,
            version=version,
            source_url=url,
            source_filename=Path(urllib.parse.urlparse(url).path).name,
            size=size,
        )

    def _science_manifest(self) -> dict[str, Any]:
        if self._science_manifest_cache is not None:
            return self._science_manifest_cache
        url = f"{self.config.science_base}/manifest.json"
        payload = self.http.get_json(url)
        _validate_version(str(payload.get("version", "")), url)
        self._science_manifest_cache = payload
        return payload

    def _science_expected_hash(
        self, definition: ArtifactDef, manifest: Mapping[str, Any]
    ) -> str:
        group = manifest.get(definition.hash_group)
        value = group.get(definition.hash_key) if isinstance(group, Mapping) else None
        if not isinstance(value, str) or not SHA256_RE.match(value.lower()):
            raise MirrorError(
                f"official science manifest has no valid "
                f"{definition.hash_group}.{definition.hash_key} for {definition.id}"
            )
        return value.lower()

    def _resolve_science(self, definition: ArtifactDef) -> LiveArtifact:
        manifest = self._science_manifest()
        manifest_version = str(manifest["version"])

        alias_url = definition.latest_url(
            self.config.desktop_api, self.config.science_base
        )
        alias_head = self.http.head(alias_url)
        if alias_head.status != 200:
            raise MirrorError(f"science alias {alias_url} returned HTTP {alias_head.status}")
        disposition = alias_head.header("content-disposition") or ""
        alias_name = parse_content_disposition_filename(disposition)
        if not alias_name:
            alias_name = Path(urllib.parse.urlparse(alias_head.url or alias_url).path).name
        alias_version = parse_science_version(alias_name, alias_url)
        if alias_version != manifest_version:
            raise MirrorError(
                f"science alias {alias_url} is {alias_version} but the official "
                f"manifest says {manifest_version}; refusing to mix versions"
            )

        # Pin the download to the versioned path so an alias flip mid-publish
        # cannot mix versions into one release.
        base = self.config.science_base
        versioned_root = base[:-len("/latest")] if base.endswith("/latest") else base
        source_url = f"{versioned_root}/{manifest_version}/{definition.alias}"
        head = self.http.head(source_url)
        if head.status != 200:
            raise MirrorError(
                f"versioned science path {source_url} returned HTTP {head.status}"
            )
        versioned_name = parse_content_disposition_filename(
            head.header("content-disposition") or ""
        ) or Path(urllib.parse.urlparse(head.url or source_url).path).name
        if parse_science_version(versioned_name, source_url) != manifest_version:
            raise MirrorError(
                f"versioned science file {source_url} does not match manifest "
                f"version {manifest_version}"
            )

        return LiveArtifact(
            definition=definition,
            version=manifest_version,
            source_url=source_url,
            source_filename=versioned_name,
            size=self._size_for(source_url, head),
            content_disposition=disposition,
            expected_sha256=self._science_expected_hash(definition, manifest),
        )

    def _code_version(self) -> str:
        if self._code_version_cache is not None:
            return self._code_version_cache
        url = f"{self.config.code_base}/latest"
        version = _validate_version(self.http.get_text(url), url)
        self._code_version_cache = version
        return version

    def _code_manifest(self, version: str) -> dict[str, Any]:
        if self._code_manifest_cache is not None:
            return self._code_manifest_cache
        url = f"{self.config.code_base}/{version}/manifest.json"
        payload = self.http.get_json(url)
        if str(payload.get("version", "")) != version:
            raise MirrorError(
                f"Claude Code manifest {url} reports version "
                f"{payload.get('version')!r}, expected {version!r}"
            )
        platforms = payload.get("platforms")
        if not isinstance(platforms, Mapping):
            raise MirrorError(f"Claude Code manifest {url} has no platforms map")
        self._code_manifest_cache = payload
        return payload

    def _resolve_code(self, definition: ArtifactDef) -> LiveArtifact:
        version = self._code_version()
        manifest = self._code_manifest(version)
        platform = definition.endpoint_path
        info = manifest["platforms"].get(platform)
        if not isinstance(info, Mapping):
            raise MirrorError(
                f"Claude Code {version} has no platform {platform!r}"
            )
        default_binary = "claude.exe" if platform.startswith("win32") else "claude"
        binary = str(info.get("binary") or default_binary)
        checksum = str(info.get("checksum") or "").lower()
        expected_size = info.get("size")
        if not SHA256_RE.match(checksum):
            raise MirrorError(
                f"Claude Code manifest has no valid checksum for {platform}"
            )
        if not isinstance(expected_size, int) or expected_size <= 0:
            raise MirrorError(
                f"Claude Code manifest has no valid size for {platform}"
            )
        source_url = f"{self.config.code_base}/{version}/{platform}/{binary}"
        head = self.http.head(source_url)
        if head.status != 200:
            raise MirrorError(
                f"Claude Code binary {source_url} returned HTTP {head.status}"
            )
        actual_size = self._size_for(source_url, head)
        if actual_size is not None and actual_size != expected_size:
            raise MirrorError(
                f"Claude Code binary {source_url} is {actual_size} bytes, "
                f"manifest says {expected_size}"
            )
        return LiveArtifact(
            definition=definition,
            version=version,
            source_url=source_url,
            source_filename=binary,
            size=expected_size,
            expected_sha256=checksum,
        )

    def resolve_product(self, product_id: str, exclude: Iterable[str] = ()) -> LiveProduct:
        excluded = set(exclude)
        artifacts = [
            self.resolve_one(d)
            for d in DEFS_BY_PRODUCT[product_id]
            if d.id not in excluded
        ]
        if not artifacts:
            raise MirrorError(f"product {product_id} has no artifacts after exclusions")
        versions = {a.version for a in artifacts}
        if len(versions) != 1:
            detail = ", ".join(f"{a.definition.id}={a.version}" for a in artifacts)
            raise MirrorError(
                f"{product_id} artifacts resolved to different versions ({detail})"
            )
        version = versions.pop()
        tag = self.config.tag_prefixes[product_id] + version
        return LiveProduct(product_id, version, tag, artifacts)


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------


def iso_now(clock: Callable[[], datetime] | None = None) -> str:
    moment = (clock or (lambda: datetime.now(timezone.utc)))()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sort_artifacts(artifacts: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    order = {d.id: index for index, d in enumerate(ALL_DEFS)}
    return sorted(
        artifacts,
        key=lambda a: (OS_ORDER.get(a.get("os"), 99), order.get(a.get("id"), 10_000)),
    )


def sort_products(products: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    order = {pid: index for index, pid in enumerate(PRODUCT_ORDER)}
    return sorted(products, key=lambda p: order.get(p.get("id"), 10_000))


def make_artifact_entry(
    live: LiveArtifact,
    config: Config,
    tag: str,
    size: int,
    sha256: str | None,
    *,
    mirrored: bool = True,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "id": live.definition.id,
        "os": live.definition.os,
        "arch": live.definition.arch,
        "variant": live.definition.variant,
        "file": live.filename,
        "size": size,
        "mirrored": mirrored,
    }
    if mirrored:
        entry["sha256"] = sha256
        entry["download_url"] = config.download_url(tag, live.filename)
    else:
        entry["download_url"] = None
        entry["relay_url"] = relay_url_for(live.definition.id)
    entry["source_url"] = live.source_url
    return entry


def make_product_entry(
    live: LiveProduct,
    config: Config,
    artifacts: list[dict[str, Any]],
    released_at: str,
) -> dict[str, Any]:
    return {
        "id": live.id,
        "name": live.name,
        "version": live.version,
        "tag": live.tag,
        "release_url": config.release_url(live.tag),
        "released_at": released_at,
        "artifacts": sort_artifacts(artifacts),
    }


def build_manifest(
    config: Config, products: Sequence[dict[str, Any]], generated_at: str
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "mirror": {
            "owner": config.owner,
            "repo": config.repo,
            "site_url": config.site_url,
            "source": config.source_site,
        },
        "products": sort_products(products),
    }


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp_name, 0o644)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def manifest_paths(root: Path, config: Config) -> tuple[Path, Path]:
    data_dir = root / config.site_dir / "data"
    return data_dir / "manifest.json", data_dir / "manifest.js"


def write_manifest(root: Path, config: Config, manifest: Mapping[str, Any]) -> tuple[Path, Path]:
    json_path, js_path = manifest_paths(root, config)
    body = json.dumps(manifest, indent=2, ensure_ascii=False)
    atomic_write_text(json_path, body + "\n")
    atomic_write_text(js_path, f"window.MIRROR_MANIFEST = {body};\n")
    return json_path, js_path


def load_manifest(
    root: Path, config: Config, *, include_sample: bool = False
) -> dict[str, Any] | None:
    json_path, _ = manifest_paths(root, config)
    if not json_path.exists():
        return None
    try:
        with json_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise MirrorError(f"cannot read existing manifest {json_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise MirrorError(f"existing manifest {json_path} is not a JSON object")
    if data.get("sample") is True and not include_sample:
        # Development fixture, not a published manifest. Force a full publish.
        return None
    return data


@contextlib.contextmanager
def publish_lock(root: Path):
    """Prevent two concurrent publishes from interleaving downloads/uploads."""
    lock_path = root / ".cache" / "publish.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+")
    try:
        if fcntl is not None:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise MirrorError(
                    f"another publish is already running (lock: {lock_path})"
                ) from exc
        yield
    finally:
        if fcntl is not None:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        handle.close()


def needs_update(
    live: LiveProduct, existing: Mapping[str, Any] | None, max_bytes: int
) -> bool:
    if not existing:
        return True
    if existing.get("version") != live.version:
        return True
    old_artifacts = existing.get("artifacts")
    if not isinstance(old_artifacts, list):
        return True
    old_ids = [
        (
            a.get("id"),
            a.get("file"),
            a.get("source_url"),
            a.get("mirrored"),
            a.get("os"),
            a.get("arch"),
            a.get("variant"),
        )
        for a in old_artifacts
        if isinstance(a, dict)
    ]
    new_ids = [
        (
            a.definition.id,
            a.filename,
            a.source_url,
            not is_relay_only(a.size, max_bytes),
            a.definition.os,
            a.definition.arch,
            a.definition.variant,
        )
        for a in live.artifacts
    ]
    return old_ids != new_ids


def render_relay_page(
    product_name: str,
    version: str,
    artifact: Mapping[str, Any],
    max_bytes: int,
) -> str:
    """Build a zero-JavaScript, Chinese-first redirect page to the official download."""
    source = str(artifact["source_url"])
    size = artifact.get("size")
    size_text = f"{size:,} B" if _is_int(size) else "大小未知"
    replacements = {
        "SOURCE": html.escape(source, quote=True),
        "PRODUCT": html.escape(f"{product_name} {version}"),
        "FILE": html.escape(str(artifact.get("file", "installer"))),
        "SIZE": html.escape(size_text),
        "LIMIT": f"{max_bytes:,}",
    }
    template = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex">
  <meta http-equiv="refresh" content="2; url=__SOURCE__">
  <title>正在前往官方下载源 · __PRODUCT__</title>
  <style>
    :root { color-scheme: light dark; }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; display: grid; place-items: center;
      background: #f5f3ee; color: #29261f; padding: 24px;
      font: 16px/1.6 ui-sans-serif, -apple-system, "Segoe UI", "PingFang SC", "Noto Sans SC", sans-serif; }
    main { width: min(560px, 100%); background: #fffdf9; border: 1px solid #e5e0d6;
      border-radius: 16px; padding: 32px; box-shadow: 0 1px 2px rgba(41,38,31,.04); }
    .eyebrow { margin: 0 0 8px; color: #a64f36; font-size: 13px; font-weight: 600; letter-spacing: .04em; }
    h1 { margin: 0 0 12px; font-size: 24px; line-height: 1.3;
      font-family: ui-serif, Georgia, "Songti SC", serif; }
    p { margin: 0 0 14px; color: #555047; }
    code { font-size: 13px; word-break: break-all; color: #29261f; }
    .file { margin: 16px 0; padding: 12px 14px; background: #f7f4ed;
      border: 1px solid #e9e3d8; border-radius: 10px; display: grid; gap: 4px; }
    .meta { font-size: 13px; color: #777064; }
    .actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 22px; }
    .btn { display: inline-flex; align-items: center; justify-content: center;
      min-height: 42px; padding: 0 18px; border-radius: 999px; text-decoration: none;
      font-weight: 600; font-size: 14px; border: 1px solid transparent; }
    .btn-primary { background: #b05237; color: #fff; }
    .btn-primary:hover { background: #97452e; }
    .btn-secondary { background: transparent; color: #29261f; border-color: #d8d2c6; }
    .btn-secondary:hover { border-color: #b9b1a2; }
    .note { margin-top: 22px; padding-top: 16px; border-top: 1px solid #ece7dd;
      font-size: 13px; color: #777064; }
    a:focus-visible { outline: 2px solid #b05237; outline-offset: 3px; }
    @media (prefers-color-scheme: dark) {
      body { background: #1f1d19; color: #f2efe8; }
      main { background: #262420; border-color: #3a362f; }
      p, .meta, .note { color: #b9b2a5; }
      .file { background: #2d2a25; border-color: #3d3931; }
      code, .btn-secondary { color: #f2efe8; }
      .btn-secondary { border-color: #4a453c; }
      .note { border-color: #3a362f; }
    }
  </style>
</head>
<body>
  <main>
    <p class="eyebrow">__PRODUCT__ · 官方源中转</p>
    <h1>正在前往官方下载源</h1>
    <p>该文件超过 GitHub Release 单文件 2 GiB（__LIMIT__ B）上限，因此没有镜像到本仓库。
      页面将在 <strong>2 秒</strong>后跳转到下载源。</p>
    <div class="file">
      <code>__FILE__</code>
      <span class="meta">__SIZE__</span>
    </div>
    <div class="actions">
      <a class="btn btn-primary" href="__SOURCE__" rel="noopener noreferrer">继续下载（官方源）</a>
      <a class="btn btn-secondary" href="../">返回镜像首页</a>
    </div>
    <p class="note">This asset is not mirrored because it exceeds GitHub's 2 GiB per-release-asset limit.
      You will be redirected to the official Anthropic download source.</p>
  </main>
</body>
</html>
"""
    # Single-pass substitution so interpolated values are never re-scanned.
    return re.sub(
        r"__(SOURCE|PRODUCT|FILE|SIZE|LIMIT)__",
        lambda match: replacements[match.group(1)],
        template,
    )


def relay_page_path(root: Path, config: Config, artifact_id: str) -> Path:
    return root / config.site_dir / "relay" / f"{artifact_id}.html"


def write_relay_pages(
    root: Path,
    config: Config,
    product: LiveProduct,
    artifacts: Sequence[Mapping[str, Any]],
    plan: list[str],
) -> None:
    for artifact in artifacts:
        if artifact.get("mirrored", True):
            continue
        path = relay_page_path(root, config, str(artifact["id"]))
        page = render_relay_page(product.name, product.version, artifact, config.max_asset_bytes)
        if path.exists():
            try:
                if path.read_text(encoding="utf-8") == page:
                    continue
            except OSError:
                pass
        atomic_write_text(path, page)
        plan.append(f"  wrote {path.relative_to(root)}")


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _parse_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        return True
    except ValueError:
        return False


def verify_manifest(
    manifest: Any,
    config: Config,
    max_asset_bytes: int | None = None,
    *,
    allow_sample: bool = False,
) -> list[str]:
    max_bytes = (
        config.max_asset_bytes if max_asset_bytes is None else max_asset_bytes
    )
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["manifest: root must be a JSON object"]
    if manifest.get("sample") is True and not allow_sample:
        return ["manifest: sample fixture; run publish first"]
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"manifest: schema_version must be {SCHEMA_VERSION}")
    if not _parse_timestamp(manifest.get("generated_at")):
        errors.append("manifest: generated_at must be a UTC ISO-8601 timestamp ending in Z")

    mirror = manifest.get("mirror")
    if not isinstance(mirror, dict):
        errors.append("manifest: mirror must be an object")
        mirror = {}
    owner = mirror.get("owner")
    repo = mirror.get("repo")
    if not isinstance(owner, str) or not owner:
        errors.append("manifest.mirror: owner must be a non-empty string")
    if not isinstance(repo, str) or not repo:
        errors.append("manifest.mirror: repo must be a non-empty string")
    site_url = mirror.get("site_url")
    if not isinstance(site_url, str) or not site_url.startswith("https://"):
        errors.append("manifest.mirror: site_url must be an https URL")
    if isinstance(owner, str) and isinstance(repo, str) and owner and repo:
        if site_url != derive_site_url(owner, repo):
            errors.append(
                f"manifest.mirror: site_url does not match owner/repo "
                f"(expected {derive_site_url(owner, repo)})"
            )
    if not isinstance(mirror.get("source"), str) or not mirror.get("source"):
        errors.append("manifest.mirror: source must be a non-empty string")

    products = manifest.get("products")
    if not isinstance(products, list) or not products:
        errors.append("manifest: products must be a non-empty array")
        return errors

    product_ids: list[str] = []
    for index, product in enumerate(products):
        where = f"products[{index}]"
        if not isinstance(product, dict):
            errors.append(f"{where}: must be an object")
            continue
        pid = product.get("id")
        label = f"{where}({pid})" if isinstance(pid, str) else where
        if not isinstance(pid, str) or pid not in DEFS_BY_PRODUCT:
            errors.append(f"{label}: unknown product id")
            continue
        product_ids.append(pid)
        if product.get("name") != PRODUCT_NAMES[pid]:
            errors.append(f"{label}: name must be {PRODUCT_NAMES[pid]!r}")
        version = product.get("version")
        if not isinstance(version, str) or not VERSION_RE.match(version):
            errors.append(f"{label}: invalid version")
            version = ""
        expected_tag = config.tag_prefixes[pid] + version if version else None
        tag = product.get("tag")
        if not isinstance(tag, str) or not tag:
            errors.append(f"{label}: tag must be a non-empty string")
            tag = ""
        elif expected_tag and tag != expected_tag:
            errors.append(f"{label}: tag must be {expected_tag!r}")
        expected_release = (
            f"https://github.com/{owner}/{repo}/releases/tag/{tag}"
            if isinstance(owner, str) and isinstance(repo, str) and tag
            else None
        )
        if expected_release and product.get("release_url") != expected_release:
            errors.append(f"{label}: release_url must be {expected_release!r}")
        if not _parse_timestamp(product.get("released_at")):
            errors.append(f"{label}: released_at must be a UTC ISO-8601 timestamp ending in Z")

        artifacts = product.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            errors.append(f"{label}: artifacts must be a non-empty array")
            continue
        seen_ids: set[str] = set()
        seen_files: set[str] = set()
        os_indexes: list[int] = []
        for a_index, artifact in enumerate(artifacts):
            awhere = f"{label}.artifacts[{a_index}]"
            if not isinstance(artifact, dict):
                errors.append(f"{awhere}: must be an object")
                continue
            aid = artifact.get("id")
            if not isinstance(aid, str) or aid not in DEF_BY_ID:
                errors.append(f"{awhere}: unknown artifact id")
                continue
            definition = DEF_BY_ID[aid]
            if definition.product != pid:
                errors.append(f"{awhere}: artifact {aid} belongs to {definition.product}")
            if aid in seen_ids:
                errors.append(f"{awhere}: duplicate artifact id {aid}")
            seen_ids.add(aid)
            for field_name in ("os", "arch", "variant"):
                if artifact.get(field_name) != getattr(definition, field_name):
                    errors.append(
                        f"{awhere}: {field_name} must be {getattr(definition, field_name)!r}"
                    )
            filename = artifact.get("file")
            expected_file = definition.friendly_name(version) if version else None
            if not isinstance(filename, str) or not filename:
                errors.append(f"{awhere}: file must be a non-empty string")
            elif expected_file and filename != expected_file:
                errors.append(f"{awhere}: file must be {expected_file!r}")
            elif filename in seen_files:
                errors.append(f"{awhere}: duplicate file {filename}")
            else:
                seen_files.add(filename)
            size = artifact.get("size")
            size_valid = _is_int(size) and size > 0
            if not size_valid:
                errors.append(f"{awhere}: size must be a positive integer")
            mirrored = artifact.get("mirrored")
            if not isinstance(mirrored, bool):
                errors.append(f"{awhere}: mirrored must be a boolean")
                mirrored = True
            if size_valid and size >= max_bytes and mirrored:
                errors.append(
                    f"{awhere}: size {size} is at or above the GitHub asset limit "
                    f"({max_bytes}) and must not be marked mirrored"
                )
            sha = artifact.get("sha256")
            download_url = artifact.get("download_url")
            expected_download = (
                f"https://github.com/{owner}/{repo}/releases/download/{tag}/{filename}"
                if isinstance(owner, str) and isinstance(repo, str) and tag
                and isinstance(filename, str)
                else None
            )
            if mirrored:
                if not isinstance(sha, str) or not SHA256_RE.match(sha):
                    errors.append(f"{awhere}: sha256 must be 64 lowercase hex characters")
                if not isinstance(download_url, str) or not download_url:
                    errors.append(f"{awhere}: download_url must be a non-empty string")
                elif expected_download and download_url != expected_download:
                    errors.append(
                        f"{awhere}: download_url must point at tag {tag!r} "
                        f"(expected {expected_download!r})"
                    )
                if "relay_url" in artifact:
                    errors.append(f"{awhere}: mirrored artifacts must not have relay_url")
            else:
                if "sha256" in artifact:
                    errors.append(
                        f"{awhere}: relay-only artifacts must omit sha256 "
                        "(the file is intentionally not downloaded)"
                    )
                if download_url is not None:
                    errors.append(
                        f"{awhere}: relay-only artifacts must have download_url: null"
                    )
                if artifact.get("relay_url") != relay_url_for(aid):
                    errors.append(
                        f"{awhere}: relay_url must be {relay_url_for(aid)!r}"
                    )
            source_url = artifact.get("source_url")
            if not isinstance(source_url, str) or not source_url.startswith(("https://", "http://")):
                errors.append(f"{awhere}: source_url must be an http(s) URL")
            os_indexes.append(OS_ORDER.get(artifact.get("os"), 99))
        if os_indexes != sorted(os_indexes):
            errors.append(f"{label}: artifacts must be ordered macOS, Windows, Linux")

    if len(product_ids) != len(set(product_ids)):
        errors.append("manifest: duplicate product id")
    known_order = [PRODUCT_ORDER.index(pid) for pid in product_ids]
    if known_order != sorted(known_order):
        errors.append("manifest: products must be ordered desktop then science")
    return errors


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class Mirror:
    def __init__(
        self,
        root: Path,
        config: Config,
        *,
        http: Any | None = None,
        transfer: Any | None = None,
        github: Any | None = None,
        runner: Any | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.root = root
        self.config = config
        self.runner = runner or SubprocessRunner()
        self.http = http or UrllibHttp()
        self.transfer = transfer or CurlTransfer(self.runner)
        self.github = github or GhCli(self.runner, config.owner, config.repo, cwd=root)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.resolver = Resolver(config, self.http)

    # -- probe ------------------------------------------------------------

    def probe(
        self, products: Sequence[str], as_json: bool = False
    ) -> tuple[int, list[dict[str, Any]], list[dict[str, str]]]:
        resolved: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        for product_key in products:
            pid = PRODUCT_IDS[product_key]
            artifacts: list[LiveArtifact] = []
            for definition in DEFS_BY_PRODUCT[pid]:
                try:
                    artifacts.append(self.resolver.resolve_one(definition))
                except MirrorError as exc:
                    errors.append({
                        "product": pid,
                        "artifact": definition.id,
                        "error": str(exc),
                    })
            versions = sorted({a.version for a in artifacts})
            if not artifacts:
                continue
            version = versions[0]
            if len(versions) > 1:
                errors.append({
                    "product": pid,
                    "artifact": "*",
                    "error": f"mixed versions: {', '.join(versions)}",
                })
            tag = self.config.tag_prefixes[pid] + version
            resolved.append({
                "id": pid,
                "name": PRODUCT_NAMES[pid],
                "version": version,
                "tag": tag,
                "artifacts": [
                    {
                        "id": a.definition.id,
                        "os": a.definition.os,
                        "arch": a.definition.arch,
                        "variant": a.definition.variant,
                        "file": a.filename,
                        "source_filename": a.source_filename,
                        "source_url": a.source_url,
                        "size": a.size,
                        "mirrored": not is_relay_only(a.size, self.config.max_asset_bytes),
                        "relay_url": (
                            relay_url_for(a.definition.id)
                            if is_relay_only(a.size, self.config.max_asset_bytes)
                            else None
                        ),
                        "expected_sha256": a.expected_sha256,
                    }
                    for a in artifacts
                ],
            })

        payload = {
            "generated_at": iso_now(self.clock),
            "products": resolved,
            "errors": errors,
        }
        if as_json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            self._print_probe_human(payload)
        if errors:
            for error in errors:
                print(
                    f"warning: {error['product']}/{error['artifact']}: {error['error']}",
                    file=sys.stderr,
                )
        exit_code = 1 if not resolved else 0
        return exit_code, resolved, errors

    @staticmethod
    def _print_probe_human(payload: Mapping[str, Any]) -> None:
        print(f"generated_at: {payload['generated_at']}")
        for product in payload["products"]:
            print(f"\n{product['name']} {product['version']} ({product['tag']})")
            for artifact in product["artifacts"]:
                size = artifact["size"]
                size_text = f"{size:>12}" if size is not None else "           ?"
                marker = "  [relay only]" if not artifact["mirrored"] else ""
                print(
                    f"  {artifact['id']:<30} {artifact['os']:<8} "
                    f"{artifact['arch']:<14} {size_text}{marker}  {artifact['source_url']}"
                )
        if not payload["products"]:
            print("\nno products resolved", file=sys.stderr)

    # -- publish ----------------------------------------------------------

    def publish(
        self,
        products: Sequence[str],
        *,
        excludes: Sequence[str] = (),
        force: bool = False,
        dry_run: bool = False,
        commit: bool = False,
        push: bool = False,
    ) -> int:
        unknown = sorted(set(excludes) - set(DEF_BY_ID))
        if unknown:
            raise MirrorError(f"unknown artifact id(s) for --exclude: {', '.join(unknown)}")
        if push:
            commit = True

        selected = list(dict.fromkeys(PRODUCT_IDS[p] for p in products))
        live_products: dict[str, LiveProduct] = {}
        for pid in selected:
            live_products[pid] = self.resolver.resolve_product(pid, excludes)

        existing = load_manifest(self.root, self.config)
        existing_by_id = {
            p.get("id"): p
            for p in (existing or {}).get("products", [])
            if isinstance(p, dict)
        }

        plan: list[str] = []
        entries: dict[str, dict[str, Any]] = {}
        to_publish: list[LiveProduct] = []
        changed_any = False

        for pid in PRODUCT_ORDER:
            if pid not in live_products:
                old = existing_by_id.get(pid)
                if old:
                    entries[pid] = old
                continue
            live = live_products[pid]
            old = existing_by_id.get(pid)
            if not force and not needs_update(live, old, self.config.max_asset_bytes):
                if old is not None:
                    entries[pid] = old
                plan.append(f"{pid}: no changes at {live.version} ({live.tag})")
                if not dry_run and old is not None:
                    # Local relay pages are cheap to reconcile and keep the
                    # manifest byte-identical.
                    write_relay_pages(
                        self.root, self.config, live,
                        old.get("artifacts") or [], plan,
                    )
                continue

            changed_any = True
            if force:
                reason = "forced"
            elif old is None:
                reason = "new product"
            elif old.get("version") != live.version:
                reason = f"version {old.get('version')} -> {live.version}"
            else:
                reason = "artifact set changed"
            plan.append(f"{pid}: changed ({reason}) -> {live.tag}")
            artifacts, sums = self._prepare_product(
                live, old, dry_run=dry_run, plan=plan
            )
            if dry_run:
                self._plan_release(live, artifacts, plan)
                continue
            self._publish_release(live, artifacts, sums, plan, force=force)
            write_relay_pages(self.root, self.config, live, artifacts, plan)
            released_at = iso_now(self.clock)
            if old is not None and old.get("version") == live.version and old.get("released_at"):
                released_at = str(old["released_at"])
            entries[pid] = make_product_entry(live, self.config, artifacts, released_at)
            to_publish.append(live)

        if dry_run:
            if not changed_any:
                plan.append("no changes; manifest unchanged")
            plan.append(
                "dry run: no downloads, uploads, relay pages, or manifest writes performed"
            )
            self._print_plan(plan)
            return 0

        if not to_publish:
            plan.append("no changes; manifest unchanged")
            self._print_plan(plan)
            return 0

        ordered = [entries[pid] for pid in PRODUCT_ORDER if pid in entries]
        manifest = build_manifest(self.config, ordered, iso_now(self.clock))
        errors = verify_manifest(manifest, self.config)
        if errors:
            raise MirrorError(
                "generated manifest failed verification:\n  " + "\n  ".join(errors)
            )
        json_path, js_path = write_manifest(self.root, self.config, manifest)
        plan.append(f"wrote {json_path.relative_to(self.root)}")
        plan.append(f"wrote {js_path.relative_to(self.root)}")
        if commit:
            self._commit(json_path, js_path, to_publish, plan)
        if push:
            self._push(plan)
        self._print_plan(plan)
        return 0

    def _prepare_product(
        self,
        live: LiveProduct,
        old: Mapping[str, Any] | None,
        *,
        dry_run: bool,
        plan: list[str],
    ) -> tuple[list[dict[str, Any]], dict[str, int | str]]:
        cache_dir = self.root / ".cache" / "downloads" / live.id / live.version
        old_artifacts = {
            a.get("id"): a
            for a in ((old or {}).get("artifacts") or [])
            if isinstance(a, dict)
        }
        artifacts: list[dict[str, Any]] = []
        sums: dict[str, int | str] = {}

        for item in live.artifacts:
            name = item.filename
            old_artifact = old_artifacts.get(item.definition.id)

            if is_relay_only(item.size, self.config.max_asset_bytes):
                artifacts.append(
                    make_artifact_entry(
                        item, self.config, live.tag, int(item.size),
                        None, mirrored=False,
                    )
                )
                if dry_run:
                    plan.append(
                        f"  relay-only {name} ({item.size} bytes) -> "
                        f"{relay_url_for(item.definition.id)}"
                    )
                continue

            if item.size is None and not dry_run:
                raise MirrorError(
                    f"cannot determine the size of {name}; refusing to download "
                    "because it may exceed the GitHub asset limit. The versioned "
                    "endpoint must expose Content-Length, "
                    "x-goog-stored-content-length, or Content-Range."
                )

            if dry_run:
                if item.size is not None:
                    plan.append(
                        f"  download {item.source_url}\n"
                        f"           -> {self._display(cache_dir / name)} ({item.size} bytes, resume)"
                    )
                else:
                    plan.append(
                        f"  download {item.source_url}\n"
                        f"           -> {self._display(cache_dir / name)} (size unknown, resume)"
                    )
                known_sha = str((old_artifact or {}).get("sha256") or "") or None
                artifacts.append(
                    make_artifact_entry(
                        item, self.config, live.tag,
                        item.size if item.size is not None else 0,
                        known_sha or (item.expected_sha256 or "0" * 64),
                    )
                )
                sums[name] = known_sha or item.expected_sha256 or "pending"
                continue

            dest = cache_dir / name
            sha, size = self._ensure_download(item, dest, plan)
            if is_relay_only(size, self.config.max_asset_bytes):
                # Defensive: the file grew after resolution. Never fail publish,
                # and never upload an over-limit asset.
                artifacts.append(
                    make_artifact_entry(
                        item, self.config, live.tag, size, None, mirrored=False
                    )
                )
                plan.append(
                    f"  relay-only {name} grew to {size} bytes; not uploaded"
                )
                continue
            artifacts.append(make_artifact_entry(item, self.config, live.tag, size, sha))
            sums[name] = sha

        return artifacts, sums

    def _ensure_download(
        self, item: LiveArtifact, dest: Path, plan: list[str]
    ) -> tuple[str, int]:
        expected = item.size
        if dest.exists() and (
            expected is None or dest.stat().st_size == expected
        ):
            plan.append(f"  reuse cached {self._display(dest)}")
        else:
            if dest.exists():
                plan.append(f"  refresh cached {self._display(dest)}")
            else:
                plan.append(f"  download {item.source_url} -> {self._display(dest)}")
            self.transfer.download(item.source_url, dest, expected)
        size = dest.stat().st_size
        if expected is not None and size != expected:
            raise MirrorError(
                f"size mismatch for {item.filename}: expected {expected} bytes, got {size}"
            )
        sha = sha256_file(dest)

        if item.expected_sha256 and sha != item.expected_sha256:
            plan.append(
                f"  cached hash mismatch for {item.filename}; redownloading"
            )
            dest.unlink(missing_ok=True)
            dest.with_name(dest.name + ".part").unlink(missing_ok=True)
            self.transfer.download(item.source_url, dest, expected)
            size = dest.stat().st_size
            if expected is not None and size != expected:
                raise MirrorError(
                    f"size mismatch for {item.filename}: expected {expected} bytes, "
                    f"got {size}"
                )
            sha = sha256_file(dest)
            if sha != item.expected_sha256:
                raise MirrorError(
                    f"SHA-256 mismatch for {item.filename}: official science "
                    f"manifest says {item.expected_sha256}, downloaded {sha}"
                )

        plan.append(f"  sha256 {item.filename} {sha}")
        return sha, size

    def _plan_release(
        self,
        live: LiveProduct,
        artifacts: Sequence[Mapping[str, Any]],
        plan: list[str],
    ) -> None:
        """Read-only release plan used by --dry-run."""
        tag = live.tag
        try:
            exists = self.github.release_exists(tag)
            names = self.github.asset_names(tag) if exists else set()
        except MirrorError as exc:
            plan.append(f"  release {tag}: state unknown ({exc}); would create if absent")
            names = set()
        else:
            if exists:
                plan.append(f"  release {tag} exists")
            else:
                plan.append(f"  create release {tag}")
        for artifact in artifacts:
            if not artifact.get("mirrored", True):
                plan.append(
                    f"  relay-only {artifact['file']} -> {artifact['relay_url']} "
                    "(not uploaded)"
                )
                continue
            filename = artifact["file"]
            if filename in names:
                plan.append(f"  asset {filename} already present")
            else:
                plan.append(f"  upload {filename} (sha256 computed at download)")
        if "SHA256SUMS.txt" in names:
            plan.append("  asset SHA256SUMS.txt already present")
        else:
            plan.append("  upload SHA256SUMS.txt")

    def _publish_release(
        self,
        live: LiveProduct,
        artifacts: list[dict[str, Any]],
        sums: Mapping[str, int | str],
        plan: list[str],
        *,
        force: bool = False,
    ) -> None:
        tag = live.tag
        exists = self.github.release_exists(tag)
        if exists:
            plan.append(f"  release {tag} exists")
            names = self.github.asset_names(tag)
        else:
            mirrored_count = sum(
                1 for artifact in artifacts if artifact.get("mirrored", True)
            )
            relay_count = len(artifacts) - mirrored_count
            notes = (
                f"{live.name} {live.version} mirrored from {self.config.source_site}.\n\n"
                f"Artifacts: {len(artifacts)} ({mirrored_count} mirrored"
                + (f", {relay_count} relay-only" if relay_count else "")
                + ").\n"
                "SHA256SUMS.txt contains the SHA-256 of every attached asset."
            )
            self.github.create_release(tag, f"{live.name} {live.version}", notes, self.config.branch)
            plan.append(f"  create release {tag}")
            names = set()
        if force:
            names = set()

        cache_dir = self.root / ".cache" / "downloads" / live.id / live.version
        uploaded_any = False
        for artifact in artifacts:
            if not artifact.get("mirrored", True):
                plan.append(
                    f"  relay-only {artifact['file']} -> {artifact['relay_url']}"
                )
                continue
            filename = artifact["file"]
            if filename in names:
                plan.append(f"  asset {filename} already present")
                continue
            self.github.upload(tag, cache_dir / filename, clobber=force)
            plan.append(f"  upload {filename}")

        sums_text = "".join(
            f"{sums[name]}  {name}\n" for name in sums
        )
        sums_path = cache_dir / "SHA256SUMS.txt"
        sums_path.parent.mkdir(parents=True, exist_ok=True)
        sums_path.write_text(sums_text, encoding="utf-8", newline="\n")
        sums_exists = "SHA256SUMS.txt" in names
        if sums_exists and not force:
            # clobber is delete-then-upload in gh 2.63.2 and is reserved for
            # explicit --force repairs. The first successful publish attached a
            # sums file covering the full mirrored set.
            plan.append("  asset SHA256SUMS.txt already present")
        else:
            self.github.upload(tag, sums_path, clobber=force)
            plan.append("  upload SHA256SUMS.txt")

    def _commit(
        self,
        json_path: Path,
        js_path: Path,
        published: Sequence[LiveProduct],
        plan: list[str],
    ) -> None:
        tags = ", ".join(live.tag for live in published)
        relay_dir = self.root / self.config.site_dir / "relay"
        add_paths = [
            str(json_path.relative_to(self.root)),
            str(js_path.relative_to(self.root)),
        ]
        if relay_dir.is_dir():
            add_paths.append(str(relay_dir.relative_to(self.root)))
        result = self.runner.run(
            ["git", "add", *add_paths],
            cwd=self.root,
        )
        if result.returncode != 0:
            raise MirrorError(f"git add failed: {result.stderr.strip()}")
        result = self.runner.run(
            ["git", "commit", "-m", f"mirror: publish {tags}"], cwd=self.root
        )
        if result.returncode != 0:
            raise MirrorError(f"git commit failed: {result.stderr.strip()}")
        plan.append(f"committed manifest update ({tags})")

    def _push(self, plan: list[str]) -> None:
        result = self.runner.run(["git", "push"], cwd=self.root)
        if result.returncode != 0:
            raise MirrorError(f"git push failed: {result.stderr.strip()}")
        plan.append("pushed manifest commit")

    @staticmethod
    def _display(path: Path) -> str:
        return str(path)

    @staticmethod
    def _print_plan(plan: Sequence[str]) -> None:
        for line in plan:
            print(line)

    # -- verify -----------------------------------------------------------

    def verify(self, *, allow_sample: bool = False) -> int:
        manifest = load_manifest(self.root, self.config, include_sample=True)
        if manifest is None:
            json_path, _ = manifest_paths(self.root, self.config)
            print(f"ERROR: {json_path} does not exist", file=sys.stderr)
            return 1
        if manifest.get("sample") is True and not allow_sample:
            print(
                "ERROR: manifest: sample fixture; run publish first",
                file=sys.stderr,
            )
            print("manifest verification failed (1 error(s))", file=sys.stderr)
            return 1
        errors = verify_manifest(manifest, self.config, allow_sample=allow_sample)
        json_path, js_path = manifest_paths(self.root, self.config)
        if not js_path.exists():
            errors.append(f"{js_path.relative_to(self.root)} is missing")
        else:
            try:
                js_text = js_path.read_text(encoding="utf-8")
            except OSError as exc:
                errors.append(f"{js_path.relative_to(self.root)} is unreadable: {exc}")
            else:
                match = re.fullmatch(
                    r"window\.MIRROR_MANIFEST = (.*);\n?", js_text, re.DOTALL
                )
                if not match:
                    errors.append(
                        f"{js_path.relative_to(self.root)} does not contain "
                        "window.MIRROR_MANIFEST"
                    )
                else:
                    try:
                        js_payload = json.loads(match.group(1))
                    except json.JSONDecodeError as exc:
                        errors.append(
                            f"{js_path.relative_to(self.root)} has invalid JSON: {exc}"
                        )
                    else:
                        if js_payload != manifest:
                            errors.append(
                                f"{js_path.relative_to(self.root)} payload differs "
                                f"from {json_path.relative_to(self.root)}"
                            )
        if not errors:
            for product in manifest.get("products", []):
                for artifact in product.get("artifacts", []):
                    if artifact.get("mirrored") is False:
                        page = relay_page_path(
                            self.root, self.config, str(artifact.get("id"))
                        )
                        if not page.exists():
                            errors.append(
                                f"relay page missing for {artifact.get('id')}: "
                                f"{page.relative_to(self.root)}"
                            )
                            continue
                        try:
                            body = page.read_text(encoding="utf-8")
                        except OSError as exc:
                            errors.append(
                                f"relay page unreadable for {artifact.get('id')}: {exc}"
                            )
                            continue
                        source_url = str(artifact.get("source_url") or "")
                        escaped_source = html.escape(source_url, quote=True)
                        if (
                            source_url
                            and source_url not in body
                            and escaped_source not in body
                        ):
                            errors.append(
                                f"relay page for {artifact.get('id')} does not "
                                f"contain its source_url"
                            )
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            print(f"manifest verification failed ({len(errors)} error(s))", file=sys.stderr)
            return 1
        products = manifest.get("products", [])
        artifact_count = sum(len(p["artifacts"]) for p in products)
        mirrored_count = sum(
            1
            for p in products
            for a in p["artifacts"]
            if a.get("mirrored", True)
        )
        print(
            f"manifest OK: {len(products)} product(s), {artifact_count} artifact(s), "
            f"{mirrored_count} mirrored, {artifact_count - mirrored_count} relay-only"
        )
        return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_products(values: Sequence[str] | None) -> list[str]:
    if not values:
        return ["desktop", "science", "code"]
    result: list[str] = []
    for value in values:
        for part in value.split(","):
            part = part.strip().lower()
            if not part:
                continue
            if part not in PRODUCT_IDS:
                raise MirrorError(
                    f"unknown product {part!r} (choose desktop, science or code)"
                )
            if part not in result:
                result.append(part)
    return result or ["desktop", "science", "code"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mirror.py",
        description="Mirror Claude Desktop/Science installers to GitHub Releases.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="project root (default: parent of scripts/)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="path to mirrorrc.json (default: <root>/mirrorrc.json)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    probe = sub.add_parser("probe", help="resolve the live artifact matrix")
    probe.add_argument("--product", action="append", metavar="desktop|science|code")
    probe.add_argument(
        "--json", action="store_true", dest="as_json",
        help="emit JSON (the default; kept for explicit scripting)",
    )
    probe.add_argument(
        "--table", action="store_true", help="emit a human-readable table instead of JSON"
    )

    publish = sub.add_parser("publish", help="publish changed artifacts and regenerate the manifest")
    publish.add_argument("--product", action="append", metavar="desktop|science|code")
    publish.add_argument("--exclude", default="", help="comma-separated artifact ids to skip")
    publish.add_argument("--force", action="store_true", help="republish even when versions are unchanged")
    publish.add_argument("--dry-run", action="store_true", help="print the plan without downloading or writing")
    publish.add_argument("--commit", action="store_true", help="git commit the generated manifest files")
    publish.add_argument(
        "--push", action="store_true",
        help="commit and git push the manifest (never implied otherwise)",
    )

    verify = sub.add_parser("verify", help="validate docs/data/manifest.json")
    verify.add_argument(
        "--allow-sample",
        action="store_true",
        help="accept the sample fixture (structural checks only; not for deployment)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = args.root.resolve()
    config_path = args.config or (root / "mirrorrc.json")
    try:
        config = load_config(config_path)
        mirror = Mirror(root, config)
        if args.command == "probe":
            products = parse_products(args.product)
            code, _, _ = mirror.probe(products, as_json=not args.table)
            return code
        if args.command == "publish":
            products = parse_products(args.product)
            excludes = [part.strip() for part in args.exclude.split(",") if part.strip()]
            if args.dry_run:
                return mirror.publish(
                    products,
                    excludes=excludes,
                    force=args.force,
                    dry_run=True,
                    commit=args.commit,
                    push=args.push,
                )
            with publish_lock(root):
                return mirror.publish(
                    products,
                    excludes=excludes,
                    force=args.force,
                    dry_run=False,
                    commit=args.commit,
                    push=args.push,
                )
        if args.command == "verify":
            return mirror.verify(allow_sample=args.allow_sample)
    except MirrorError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
