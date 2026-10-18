#!/usr/bin/env python3
"""Unit tests for scripts/mirror.py (stdlib unittest, no network)."""

from __future__ import annotations

import copy
import io
import json
import hashlib
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mirror as engine  # noqa: E402

FIXED_NOW = datetime(2026, 10, 17, 8, 30, 0, tzinfo=timezone.utc)


def make_config(**overrides):
    raw = {
        "owner": "aresbit",
        "repo": "claude-downloads-mirror",
        "branch": "main",
        "site_dir": "docs",
        "source": {
            "desktop_api": "https://api.anthropic.com/api/desktop",
            "science_base": "https://downloads.claude.ai/claude-science/latest",
            "code_base": "https://downloads.claude.ai/claude-code-releases",
            "site": "https://downloads.claude.ai",
        },
        "release": {
            "desktop_tag_prefix": "desktop-v",
            "science_tag_prefix": "science-v",
            "code_tag_prefix": "code-v",
            "max_asset_bytes": engine.DEFAULT_MAX_ASSET_BYTES,
        },
    }
    raw.update(overrides)
    return engine.Config.from_dict(raw)


def fake_payload(url, size):
    """Deterministic bytes used by FakeTransfer and the fake official hashes."""
    seed = hashlib.sha256(url.encode()).digest()
    return (seed * ((size // len(seed)) + 1))[:size]


def fake_sha(url, size):
    return hashlib.sha256(fake_payload(url, size)).hexdigest()


DESKTOP_DEFAULT_SIZES = {
    # Over the 2 GiB cap: must never be downloaded, only relayed.
    "windows-x64-offline": 2_220_697_207,
}


def desktop_http(version="2.42304.0", sizes=None):
    """Fake HTTP responding to the 13 desktop version endpoints."""
    sizes = sizes or {}
    json_map = {}
    head_map = {}
    for index, definition in enumerate(engine.DESKTOP_DEFS):
        endpoint = definition.latest_url(
            "https://api.anthropic.com/api/desktop",
            "https://downloads.claude.ai/claude-science/latest",
        )
        source = (
            f"https://downloads.claude.ai/releases/{definition.endpoint_path}/"
            f"Claude-{index}.bin"
        )
        json_map[endpoint] = {"version": version, "url": source}
        size = sizes.get(
            definition.id, DESKTOP_DEFAULT_SIZES.get(definition.id, 1000 + index)
        )
        head_map[source] = engine.HeadResponse(
            200, {"x-goog-stored-content-length": str(size)}, source
        )
    return FakeHttp(json_map, head_map)


SCIENCE_SIZES = {
    # Small on purpose: the engine must not care about the concrete value and
    # fake downloads should stay fast. The live sizes are in the brief.
    "science-macos-apple-silicon": 2000,
    "science-macos-intel": 2001,
    "science-windows-x64": 2002,
    "science-windows-arm64": 2003,
    "science-linux-x64": 2004,
}


def science_http(
    version="0.1.63",
    version_overrides=None,
    sizes=None,
    hash_overrides=None,
):
    """Fake HTTP for the five science aliases, versioned paths, and manifest."""
    version_overrides = version_overrides or {}
    sizes = sizes or {}
    hash_overrides = hash_overrides or {}
    head_map = {}
    disposition_names = {
        "mac-arm64.dmg": f"Claude-Science-{version}.dmg",
        "mac-x64.dmg": f"Claude-Science-{version}-Intel.dmg",
        "windows-x64.exe": f"Claude-Science-{version}.exe",
        "windows-arm64.exe": f"Claude-Science-{version}-arm64.exe",
        "linux-x64": f"claude-science-{version}-linux-x64",
    }
    versioned_root = "https://downloads.claude.ai/claude-science"
    dmg_hashes = {}
    bin_hashes = {}
    for index, definition in enumerate(engine.SCIENCE_DEFS):
        size = sizes.get(definition.id, SCIENCE_SIZES[definition.id])
        alias_url = definition.latest_url(
            "", "https://downloads.claude.ai/claude-science/latest"
        )
        alias_name = disposition_names[definition.alias]
        v = version_overrides.get(definition.id, version)
        if v != version:
            alias_name = alias_name.replace(version, v)
        head_map[alias_url] = engine.HeadResponse(
            200,
            {
                "content-disposition": f'attachment; filename="{alias_name}"',
                "x-goog-stored-content-length": str(size),
            },
            alias_url,
        )
        versioned_url = f"{versioned_root}/{version}/{definition.alias}"
        head_map[versioned_url] = engine.HeadResponse(
            200,
            {
                "content-disposition": (
                    f'attachment; filename="{disposition_names[definition.alias]}"'
                ),
                "x-goog-stored-content-length": str(size),
            },
            versioned_url,
        )
        expected = hash_overrides.get(
            definition.id, fake_sha(versioned_url, size)
        )
        if definition.hash_group == "dmg_sha256":
            dmg_hashes[definition.hash_key] = expected
        else:
            bin_hashes[definition.hash_key] = expected
    json_map = {
        "https://downloads.claude.ai/claude-science/latest/manifest.json": {
            "version": version,
            "sha8": "12345678",
            "buildDate": "2026-10-14T23:31:23Z",
            "sha256": bin_hashes,
            "dmg_sha256": dmg_hashes,
        }
    }
    return FakeHttp(json_map, head_map)


CODE_SIZES = {definition.id: 3000 + index for index, definition in enumerate(engine.CODE_DEFS)}


def code_http(version="2.1.302", sizes=None, hash_overrides=None):
    """Fake Claude Code latest/manifest/binary endpoints."""
    sizes = sizes or {}
    hash_overrides = hash_overrides or {}
    base = "https://downloads.claude.ai/claude-code-releases"
    platforms = {}
    head_map = {}
    for definition in engine.CODE_DEFS:
        size = sizes.get(definition.id, CODE_SIZES[definition.id])
        binary = "claude.exe" if definition.endpoint_path.startswith("win32") else "claude"
        source = f"{base}/{version}/{definition.endpoint_path}/{binary}"
        checksum = hash_overrides.get(
            definition.id, fake_sha(source, size)
        )
        platforms[definition.endpoint_path] = {
            "binary": binary,
            "checksum": checksum,
            "size": size,
        }
        head_map[source] = engine.HeadResponse(
            200, {"x-goog-stored-content-length": str(size)}, source
        )
    json_map = {
        f"{base}/{version}/manifest.json": {
            "version": version,
            "platforms": platforms,
        }
    }
    text_map = {f"{base}/latest": version}
    return FakeHttp(json_map, head_map, text_map=text_map)


class FakeHttp:
    def __init__(self, json_map=None, head_map=None, range_map=None, text_map=None):
        self.json_map = json_map or {}
        self.head_map = head_map or {}
        self.range_map = range_map or {}
        self.text_map = text_map or {}
        self.json_calls = []
        self.head_calls = []
        self.range_calls = []
        self.text_calls = []

    def get_json(self, url):
        self.json_calls.append(url)
        if url not in self.json_map:
            raise engine.MirrorError(f"unexpected GET {url}")
        return copy.deepcopy(self.json_map[url])

    def get_text(self, url):
        self.text_calls.append(url)
        if url not in self.text_map:
            raise engine.MirrorError(f"unexpected text GET {url}")
        return self.text_map[url]

    def head(self, url):
        self.head_calls.append(url)
        if url not in self.head_map:
            raise engine.MirrorError(f"unexpected HEAD {url}")
        return self.head_map[url]

    def get_range(self, url):
        self.range_calls.append(url)
        if url not in self.range_map:
            raise engine.MirrorError(f"unexpected ranged GET {url}")
        return self.range_map[url]


class FakeTransfer:
    def __init__(self, body=b"payload!"):
        self.body = body
        self.calls = []

    def download(self, url, dest, expected_size):
        self.calls.append((url, str(dest), expected_size))
        dest.parent.mkdir(parents=True, exist_ok=True)
        if expected_size is None:
            dest.write_bytes(self.body)
        else:
            dest.write_bytes(fake_payload(url, expected_size))


class FakeGh:
    def __init__(self, releases=None, assets=None, fail_lookup=False):
        self.releases = set(releases or [])
        self.assets = {tag: set(names) for tag, names in (assets or {}).items()}
        self.fail_lookup = fail_lookup
        self.created = []
        self.uploaded = []
        self.clobbers = []
        self.create_args = []

    def release_exists(self, tag):
        if self.fail_lookup:
            raise engine.MirrorError("gh is not authenticated")
        return tag in self.releases

    def create_release(self, tag, title, notes, target):
        self.created.append(tag)
        self.create_args.append((tag, title, notes, target))
        self.releases.add(tag)
        self.assets.setdefault(tag, set())

    def asset_names(self, tag):
        return set(self.assets.get(tag, set()))

    def upload(self, tag, path, *, clobber=False):
        self.uploaded.append((tag, Path(path).name))
        self.clobbers.append(clobber)
        self.assets.setdefault(tag, set()).add(Path(path).name)


class FakeRunner:
    def __init__(self):
        self.calls = []

    def run(self, cmd, cwd=None):
        self.calls.append((list(cmd), cwd))
        return engine.CommandResult(0)


class WritingCurlRunner:
    """Simulates curl writes into the --output path."""

    def __init__(self):
        self.calls = []

    def run(self, cmd, cwd=None):
        self.calls.append(list(cmd))
        out = Path(cmd[cmd.index("--output") + 1])
        existing = out.stat().st_size if out.exists() else 0
        token = b"0123456789abcdef"
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("ab") as fh:
            fh.write((token * 100)[:max(0, 64 - existing)])
        return engine.CommandResult(0)


class TempRootCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.config = make_config()
        (self.root / "docs" / "data").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def engine(self, http=None, transfer=None, gh=None, runner=None):
        return engine.Mirror(
            self.root,
            self.config,
            http=http or desktop_http(),
            transfer=transfer or FakeTransfer(),
            github=gh or FakeGh(),
            runner=runner or FakeRunner(),
            clock=lambda: FIXED_NOW,
        )


# ---------------------------------------------------------------------------
# Version / naming
# ---------------------------------------------------------------------------


class VersionParsingTests(unittest.TestCase):
    def test_desktop_api_resolution(self):
        http = desktop_http()
        resolver = engine.Resolver(make_config(), http)
        artifact = resolver.resolve_one(engine.DESKTOP_DEFS[0])
        self.assertEqual(artifact.version, "2.42304.0")
        self.assertEqual(artifact.size, 1000)
        self.assertEqual(
            artifact.source_url,
            "https://downloads.claude.ai/releases/darwin/universal/dmg/Claude-0.bin",
        )

    def test_desktop_invalid_version_rejected(self):
        http = FakeHttp(
            {
                "https://api.anthropic.com/api/desktop/darwin/universal/dmg/latest": {
                    "version": "not-a-version",
                    "url": "https://downloads.claude.ai/x.dmg",
                }
            },
            {},
        )
        resolver = engine.Resolver(make_config(), http)
        with self.assertRaises(engine.MirrorError):
            resolver.resolve_one(engine.DESKTOP_DEFS[0])

    def test_desktop_missing_url_rejected(self):
        http = FakeHttp(
            {
                "https://api.anthropic.com/api/desktop/darwin/universal/dmg/latest": {
                    "version": "2.42304.0"
                }
            }
        )
        resolver = engine.Resolver(make_config(), http)
        with self.assertRaises(engine.MirrorError):
            resolver.resolve_one(engine.DESKTOP_DEFS[0])

    def test_science_versions_from_content_disposition(self):
        resolver = engine.Resolver(make_config(), science_http())
        expected = {
            "science-macos-apple-silicon": "0.1.63",
            "science-macos-intel": "0.1.63",
            "science-windows-x64": "0.1.63",
            "science-windows-arm64": "0.1.63",
            "science-linux-x64": "0.1.63",
        }
        for definition in engine.SCIENCE_DEFS:
            resolved = resolver.resolve_one(definition)
            self.assertEqual(resolved.version, expected[definition.id])
            self.assertTrue(resolved.source_filename.startswith(("Claude-Science", "claude-science")))

    def test_science_pins_versioned_source_and_expected_hash(self):
        http = science_http()
        versioned = "https://downloads.claude.ai/claude-science/0.1.63/mac-arm64.dmg"
        resolved = engine.Resolver(make_config(), http).resolve_one(
            engine.SCIENCE_DEFS[0]
        )
        self.assertEqual(resolved.source_url, versioned)
        self.assertEqual(resolved.size, SCIENCE_SIZES["science-macos-apple-silicon"])
        self.assertEqual(
            resolved.expected_sha256,
            fake_sha(versioned, SCIENCE_SIZES["science-macos-apple-silicon"]),
        )

    def test_science_rejects_alias_manifest_version_mismatch(self):
        http = science_http()
        alias = "https://downloads.claude.ai/claude-science/latest/mac-x64.dmg"
        http.head_map[alias] = engine.HeadResponse(
            200,
            {
                "content-disposition": 'attachment; filename="Claude-Science-0.1.64-Intel.dmg"',
                "x-goog-stored-content-length": "84",
            },
            alias,
        )
        with self.assertRaisesRegex(engine.MirrorError, "refusing to mix versions"):
            engine.Resolver(make_config(), http).resolve_one(engine.SCIENCE_DEFS[1])

    def test_relay_page_escapes_and_does_not_resubstitute(self):
        artifact = {
            "source_url": 'https://downloads.claude.ai/x?q=1&v="<tag>"',
            "file": '<file>.msix',
            "size": 1234,
        }
        page = engine.render_relay_page("__SOURCE__", "1.0", artifact, 2_147_483_648)
        self.assertIn("&amp;", page)
        self.assertIn("&quot;", page)
        self.assertIn("&lt;file&gt;.msix", page)
        # The literal product placeholder must survive (single-pass substitution).
        self.assertIn("__SOURCE__", page)
        self.assertIn('content="2;', page)
        self.assertIn("返回镜像首页", page)
        self.assertIn('href="../"', page)

    def test_parse_science_version_variants(self):
        cases = {
            "Claude-Science-0.1.63.dmg": "0.1.63",
            "Claude-Science-0.1.63-Intel.dmg": "0.1.63",
            "Claude-Science-0.1.63.exe": "0.1.63",
            "Claude-Science-0.1.63-arm64.exe": "0.1.63",
            "claude-science-0.1.63-linux-x64": "0.1.63",
            "Claude-Science-0.2.0-beta.1.dmg": "0.2.0-beta.1",
        }
        for filename, version in cases.items():
            self.assertEqual(engine.parse_science_version(filename, "test"), version)

    def test_parse_science_version_bad_name(self):
        with self.assertRaises(engine.MirrorError):
            engine.parse_science_version("Claude-Setup.exe", "test")

    def test_content_disposition_parsing(self):
        self.assertEqual(
            engine.parse_content_disposition_filename(
                'attachment; filename="Claude-Science-0.1.63-Intel.dmg"'
            ),
            "Claude-Science-0.1.63-Intel.dmg",
        )
        self.assertIsNone(engine.parse_content_disposition_filename(""))

    def test_mixed_science_versions_rejected(self):
        http = science_http(version_overrides={"science-macos-intel": "0.1.64"})
        resolver = engine.Resolver(make_config(), http)
        with self.assertRaisesRegex(engine.MirrorError, "refusing to mix versions"):
            resolver.resolve_product("claude-science")

    def test_size_header_prefers_content_length(self):
        self.assertEqual(
            engine.header_size({"content-length": "7", "x-goog-stored-content-length": "9"}),
            7,
        )
        self.assertEqual(engine.header_size({"x-goog-stored-content-length": "9"}), 9)


    def test_code_resolution(self):
        resolver = engine.Resolver(make_config(), code_http())
        for definition in engine.CODE_DEFS:
            resolved = resolver.resolve_one(definition)
            self.assertEqual(resolved.version, "2.1.302")
            self.assertEqual(resolved.size, CODE_SIZES[definition.id])
            self.assertTrue(engine.SHA256_RE.match(resolved.expected_sha256 or ""))
            self.assertIn(f"/{definition.endpoint_path}/", resolved.source_url)

    def test_code_missing_platform_rejected(self):
        http = code_http()
        manifest_url = "https://downloads.claude.ai/claude-code-releases/2.1.302/manifest.json"
        del http.json_map[manifest_url]["platforms"]["darwin-arm64"]
        resolver = engine.Resolver(make_config(), http)
        with self.assertRaises(engine.MirrorError):
            resolver.resolve_one(engine.CODE_DEFS[0])

    def test_code_size_mismatch_rejected(self):
        http = code_http()
        url = "https://downloads.claude.ai/claude-code-releases/2.1.302/darwin-arm64/claude"
        http.head_map[url] = engine.HeadResponse(
            200, {"x-goog-stored-content-length": "999"}, url
        )
        resolver = engine.Resolver(make_config(), http)
        with self.assertRaises(engine.MirrorError):
            resolver.resolve_one(engine.CODE_DEFS[0])

    def test_code_manifest_version_mismatch_rejected(self):
        http = code_http()
        manifest_url = "https://downloads.claude.ai/claude-code-releases/2.1.302/manifest.json"
        http.json_map[manifest_url]["version"] = "9.9.9"
        resolver = engine.Resolver(make_config(), http)
        with self.assertRaises(engine.MirrorError):
            resolver.resolve_one(engine.CODE_DEFS[0])


class NamingTests(unittest.TestCase):
    def test_desktop_friendly_names(self):
        version = "2.42304.0"
        names = {d.id: d.friendly_name(version) for d in engine.DESKTOP_DEFS}
        self.assertEqual(
            names,
            {
                "macos-universal": "Claude-Desktop-2.42304.0-macOS-universal.dmg",
                "macos-intel-offline": "Claude-Desktop-2.42304.0-macOS-intel-offline.dmg",
                "macos-apple-silicon-offline": "Claude-Desktop-2.42304.0-macOS-apple-silicon-offline.dmg",
                "windows-x64-setup": "Claude-Desktop-2.42304.0-Windows-x64-setup.exe",
                "windows-arm64-setup": "Claude-Desktop-2.42304.0-Windows-arm64-setup.exe",
                "windows-x64-exe": "Claude-Desktop-2.42304.0-Windows-x64.exe",
                "windows-arm64-exe": "Claude-Desktop-2.42304.0-Windows-arm64.exe",
                "windows-x64-msix": "Claude-Desktop-2.42304.0-Windows-x64.msix",
                "windows-arm64-msix": "Claude-Desktop-2.42304.0-Windows-arm64.msix",
                "windows-x64-offline": "Claude-Desktop-2.42304.0-Windows-x64-offline.msix",
                "windows-arm64-offline": "Claude-Desktop-2.42304.0-Windows-arm64-offline.msix",
                "linux-x64-deb": "Claude-Desktop-2.42304.0-Linux-x64.deb",
                "linux-arm64-deb": "Claude-Desktop-2.42304.0-Linux-arm64.deb",
            },
        )

    def test_science_friendly_names(self):
        version = "0.1.63"
        names = {d.id: d.friendly_name(version) for d in engine.SCIENCE_DEFS}
        self.assertEqual(
            names,
            {
                "science-macos-apple-silicon": "Claude-Science-0.1.63-macOS-apple-silicon.dmg",
                "science-macos-intel": "Claude-Science-0.1.63-macOS-intel.dmg",
                "science-windows-x64": "Claude-Science-0.1.63-Windows-x64.exe",
                "science-windows-arm64": "Claude-Science-0.1.63-Windows-arm64.exe",
                "science-linux-x64": "Claude-Science-0.1.63-Linux-x64",
            },
        )

    def test_code_friendly_names(self):
        version = "2.1.302"
        names = {d.id: d.friendly_name(version) for d in engine.CODE_DEFS}
        self.assertEqual(
            names,
            {
                "code-macos-apple-silicon": "Claude-Code-2.1.302-macOS-arm64",
                "code-macos-intel": "Claude-Code-2.1.302-macOS-intel",
                "code-windows-x64": "Claude-Code-2.1.302-Windows-x64.exe",
                "code-windows-arm64": "Claude-Code-2.1.302-Windows-arm64.exe",
                "code-linux-x64": "Claude-Code-2.1.302-Linux-x64",
                "code-linux-x64-musl": "Claude-Code-2.1.302-Linux-x64-musl",
                "code-linux-arm64": "Claude-Code-2.1.302-Linux-arm64",
                "code-linux-arm64-musl": "Claude-Code-2.1.302-Linux-arm64-musl",
            },
        )

    def test_site_url_derivation(self):
        self.assertEqual(
            engine.derive_site_url("aresbit", "claude-downloads-mirror"),
            "https://aresbit.github.io/claude-downloads-mirror/",
        )
        self.assertEqual(
            engine.derive_site_url("aresbit", "aresbit.github.io"),
            "https://aresbit.github.io/",
        )


# ---------------------------------------------------------------------------
# Diff / guard
# ---------------------------------------------------------------------------


class DiffTests(TempRootCase):
    def _resolved(self, product="claude-desktop", version="2.42304.0"):
        http = desktop_http(version=version) if product == "claude-desktop" else science_http(version=version)
        return engine.Resolver(self.config, http).resolve_product(product)

    def test_missing_manifest_needs_update(self):
        self.assertTrue(engine.needs_update(self._resolved(), None, self.config.max_asset_bytes))

    def test_same_version_same_artifacts_is_unchanged(self):
        live = self._resolved()
        existing = {
            "id": live.id,
            "version": live.version,
            "artifacts": [
                {
                    "id": a.definition.id,
                    "file": a.filename,
                    "source_url": a.source_url,
                    "mirrored": not engine.is_relay_only(
                        a.size, self.config.max_asset_bytes
                    ),
                    "os": a.definition.os,
                    "arch": a.definition.arch,
                    "variant": a.definition.variant,
                }
                for a in live.artifacts
            ],
        }
        self.assertFalse(
            engine.needs_update(live, existing, self.config.max_asset_bytes)
        )

    def test_version_change_needs_update(self):
        live = self._resolved()
        existing = {
            "id": live.id,
            "version": "2.40000.0",
            "artifacts": [
                {"id": a.definition.id, "file": a.filename} for a in live.artifacts
            ],
        }
        self.assertTrue(
            engine.needs_update(live, existing, self.config.max_asset_bytes)
        )

    def test_source_url_change_needs_update(self):
        live = self._resolved()
        existing = {
            "id": live.id,
            "version": live.version,
            "artifacts": [
                {
                    "id": a.definition.id,
                    "file": a.filename,
                    "source_url": a.source_url + "?moved",
                    "mirrored": not engine.is_relay_only(
                        a.size, self.config.max_asset_bytes
                    ),
                }
                for a in live.artifacts
            ],
        }
        self.assertTrue(
            engine.needs_update(live, existing, self.config.max_asset_bytes)
        )

    def test_mirrored_flag_change_needs_update(self):
        live = self._resolved()
        existing = {
            "id": live.id,
            "version": live.version,
            "artifacts": [
                {
                    "id": a.definition.id,
                    "file": a.filename,
                    "source_url": a.source_url,
                    "mirrored": True,
                }
                for a in live.artifacts
            ],
        }
        # live marks windows-x64-offline as relay-only
        self.assertTrue(
            engine.needs_update(live, existing, self.config.max_asset_bytes)
        )

    def test_new_artifact_needs_update(self):
        live = self._resolved()
        existing = {
            "id": live.id,
            "version": live.version,
            "artifacts": [
                {"id": a.definition.id, "file": a.filename}
                for a in live.artifacts[:-1]
            ],
        }
        self.assertTrue(
            engine.needs_update(live, existing, self.config.max_asset_bytes)
        )


class RelayPolicyTests(TempRootCase):
    def test_strict_predicate_boundary(self):
        limit = 2_147_483_648
        self.assertFalse(engine.is_relay_only(limit - 1, limit))
        self.assertTrue(engine.is_relay_only(limit, limit))
        self.assertTrue(engine.is_relay_only(limit + 1, limit))
        self.assertFalse(engine.is_relay_only(None, limit))

    def test_over_limit_artifact_is_relay_only_not_downloaded(self):
        transfer = FakeTransfer()
        gh = FakeGh()
        mirror = self.engine(http=desktop_http(), transfer=transfer, gh=gh)
        out = io.StringIO()
        with redirect_stdout(out):
            mirror.publish(["desktop"])
        manifest = json.loads((self.root / "docs/data/manifest.json").read_text())
        artifacts = manifest["products"][0]["artifacts"]
        artifact = next(a for a in artifacts if a["id"] == "windows-x64-offline")
        self.assertEqual(artifact["size"], 2_220_697_207)
        self.assertFalse(artifact["mirrored"])
        self.assertIsNone(artifact["download_url"])
        self.assertEqual(artifact["relay_url"], "relay/windows-x64-offline.html")
        self.assertNotIn("sha256", artifact)
        self.assertTrue(artifact["source_url"].startswith("https://"))
        self.assertFalse(
            any("win32/x64/offline" in call[0] for call in transfer.calls)
        )
        self.assertNotIn(
            "Claude-Desktop-2.42304.0-Windows-x64-offline.msix",
            [name for _, name in gh.uploaded],
        )
        page = self.root / "docs/relay/windows-x64-offline.html"
        self.assertTrue(page.exists())
        body = page.read_text()
        self.assertIn('http-equiv="refresh"', body)
        self.assertIn(f'href="{artifact["source_url"]}"', body)
        self.assertIn(artifact["file"], body)
        self.assertIn("2,147,483,648", body)
        # 12 mirrored desktop artifacts + SHA256SUMS.txt are uploaded.
        self.assertEqual(len(gh.uploaded), 13)

    def test_exactly_at_limit_is_relay_only(self):
        config = make_config(
            release={
                "desktop_tag_prefix": "desktop-v",
                "science_tag_prefix": "science-v",
                "max_asset_bytes": 1000,
            }
        )
        transfer = FakeTransfer()
        mirror = engine.Mirror(
            self.root, config,
            http=desktop_http(sizes={"macos-universal": 1000}),
            transfer=transfer, github=FakeGh(), clock=lambda: FIXED_NOW,
        )
        out = io.StringIO()
        with redirect_stdout(out):
            mirror.publish(
                ["desktop"],
                excludes=[d.id for d in engine.DESKTOP_DEFS[1:]],
            )
        manifest = json.loads((self.root / "docs/data/manifest.json").read_text())
        artifact = manifest["products"][0]["artifacts"][0]
        self.assertFalse(artifact["mirrored"])
        self.assertEqual(transfer.calls, [])

    def test_unknown_size_refuses_download(self):
        http = desktop_http()
        source = "https://downloads.claude.ai/releases/darwin/universal/dmg/Claude-0.bin"
        http.head_map[source] = engine.HeadResponse(200, {}, source)
        mirror = self.engine(http=http)
        with self.assertRaisesRegex(engine.MirrorError, "cannot determine the size"):
            mirror.publish(
                ["desktop"],
                excludes=[d.id for d in engine.DESKTOP_DEFS[1:]],
            )

    def test_range_get_fallback_discovers_size(self):
        http = desktop_http()
        source = "https://downloads.claude.ai/releases/darwin/universal/dmg/Claude-0.bin"
        http.head_map[source] = engine.HeadResponse(200, {}, source)
        http.range_map[source] = engine.HeadResponse(
            206, {"content-range": "bytes 0-0/388258098"}, source
        )
        resolved = engine.Resolver(self.config, http).resolve_one(
            engine.DESKTOP_DEFS[0]
        )
        self.assertEqual(resolved.size, 388258098)
        self.assertEqual(http.range_calls, [source])


# ---------------------------------------------------------------------------
# Curl transfer
# ---------------------------------------------------------------------------


class CurlTransferTests(TempRootCase):
    def test_sums_not_clobbered_without_force(self):
        version = "2.42304.0"
        mirrored = {
            d.friendly_name(version)
            for d in engine.DESKTOP_DEFS
            if d.id != "windows-x64-offline"
        }
        missing = "Claude-Desktop-2.42304.0-macOS-universal.dmg"
        gh = FakeGh(
            releases=["desktop-v2.42304.0"],
            assets={"desktop-v2.42304.0": (mirrored - {missing}) | {"SHA256SUMS.txt"}},
        )
        mirror = self.engine(http=desktop_http(), transfer=FakeTransfer(), gh=gh)
        mirror.publish(["desktop"])
        uploaded = [name for _, name in gh.uploaded]
        # Only the genuinely missing installer is uploaded; the existing sums
        # file is never clobbered by a routine repair.
        self.assertEqual(uploaded, [missing])
        self.assertEqual(gh.clobbers, [False])

    def test_publish_lock_is_exclusive_and_released(self):
        if engine.fcntl is None:
            self.skipTest("fcntl unavailable on this platform")
        with engine.publish_lock(self.root):
            with self.assertRaisesRegex(engine.MirrorError, "another publish"):
                with engine.publish_lock(self.root):
                    pass
        # finally released the lock
        with engine.publish_lock(self.root):
            pass

    def test_missing_subprocess_is_reported(self):
        result = engine.SubprocessRunner().run(["definitely-not-a-real-command-xyz"])
        self.assertEqual(result.returncode, 127)
        self.assertIn("cannot execute", result.stderr)

    def test_gh_release_create_does_not_mark_latest(self):
        runner = FakeRunner()
        gh = engine.GhCli(runner, "aresbit", "claude-downloads-mirror")
        gh.create_release("desktop-v1", "title", "notes", "main")
        command = runner.calls[0][0]
        self.assertIn("--latest=false", command)

    def test_command_resumes(self):
        cmd = engine.CurlTransfer.command("https://example.test/x", Path("/tmp/x.part"))
        self.assertIn("--continue-at", cmd)
        self.assertEqual(cmd[cmd.index("--continue-at") + 1], "-")
        self.assertIn("--output", cmd)

    def test_download_resumes_partial_file(self):
        runner = WritingCurlRunner()
        transfer = engine.CurlTransfer(runner)
        dest = self.root / "file.bin"
        part = dest.with_name(dest.name + ".part")
        part.write_bytes(b"0123456789abcdef" * 2)  # 32 bytes
        transfer.download("https://example.test/file", dest, expected_size=64)
        self.assertEqual(dest.stat().st_size, 64)
        self.assertFalse(part.exists())
        self.assertIn("--continue-at", runner.calls[0])

    def test_download_size_mismatch_raises(self):
        class ShortRunner:
            def run(self, cmd, cwd=None):
                out = Path(cmd[cmd.index("--output") + 1])
                out.write_bytes(b"abc")
                return engine.CommandResult(0)

        transfer = engine.CurlTransfer(ShortRunner())
        with self.assertRaisesRegex(engine.MirrorError, "size mismatch"):
            transfer.download("https://example.test/file", self.root / "x", expected_size=10)


# ---------------------------------------------------------------------------
# Manifest writes / ordering
# ---------------------------------------------------------------------------


class ManifestTests(TempRootCase):
    def _publish_all(self, **kwargs):
        transfer = FakeTransfer()
        gh = FakeGh()
        engine_ = self.engine(
            http=self._both_http(), transfer=transfer, gh=gh
        )
        rc = engine_.publish(["desktop", "science"], **kwargs)
        return rc, transfer, gh, engine_

    def _both_http(self):
        d = desktop_http()
        s = science_http()
        return FakeHttp(
            {**d.json_map, **s.json_map},
            {**d.head_map, **s.head_map},
            {**d.range_map, **s.range_map},
        )

    def test_manifest_order_and_shapes(self):
        rc, _, _, _ = self._publish_all()
        self.assertEqual(rc, 0)
        manifest = json.loads((self.root / "docs/data/manifest.json").read_text())
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(manifest["generated_at"], "2026-10-17T08:30:00Z")
        self.assertEqual(
            manifest["mirror"]["site_url"],
            "https://aresbit.github.io/claude-downloads-mirror/",
        )
        self.assertEqual([p["id"] for p in manifest["products"]], ["claude-desktop", "claude-science"])
        desktop = manifest["products"][0]
        self.assertEqual(desktop["tag"], "desktop-v2.42304.0")
        self.assertEqual([a["id"] for a in desktop["artifacts"]], [d.id for d in engine.DESKTOP_DEFS])
        self.assertEqual(
            [a["os"] for a in desktop["artifacts"]][:3], ["macOS", "macOS", "macOS"]
        )
        self.assertEqual(desktop["artifacts"][-1]["download_url"],
            "https://github.com/aresbit/claude-downloads-mirror/releases/download/"
            "desktop-v2.42304.0/Claude-Desktop-2.42304.0-Linux-arm64.deb")
        science = manifest["products"][1]
        self.assertEqual(science["tag"], "science-v0.1.63")
        self.assertEqual(
            [a["id"] for a in science["artifacts"]],
            [
                "science-macos-apple-silicon",
                "science-macos-intel",
                "science-windows-x64",
                "science-windows-arm64",
                "science-linux-x64",
            ],
        )
        self.assertTrue(all(a["mirrored"] for a in science["artifacts"]))
        relay = next(a for a in desktop["artifacts"] if a["id"] == "windows-x64-offline")
        self.assertFalse(relay["mirrored"])
        self.assertIsNone(relay["download_url"])
        self.assertEqual(relay["relay_url"], "relay/windows-x64-offline.html")
        self.assertNotIn("sha256", relay)

    def test_manifest_js_mirrors_json(self):
        self._publish_all()
        body = json.loads((self.root / "docs/data/manifest.json").read_text())
        js = (self.root / "docs/data/manifest.js").read_text()
        self.assertTrue(js.startswith("window.MIRROR_MANIFEST = "))
        embedded = js[len("window.MIRROR_MANIFEST = "):].rstrip()
        self.assertTrue(embedded.endswith(";"))
        self.assertEqual(json.loads(embedded[:-1]), body)

    def test_atomic_write_leaves_no_temp_files(self):
        self._publish_all()
        leftovers = list((self.root / "docs/data").glob("*.tmp"))
        self.assertEqual(leftovers, [])
        later = self.root / "docs/data/manifest.json"
        engine.atomic_write_text(later, '{"ok": true}\n')
        self.assertEqual(later.read_text(), '{"ok": true}\n')
        self.assertEqual(list((self.root / "docs/data").glob("*.tmp")), [])

    def test_sha256sums_content(self):
        _, _, gh, _ = self._publish_all()
        tag = "desktop-v2.42304.0"
        sums_path = (
            self.root / ".cache/downloads/claude-desktop/2.42304.0/SHA256SUMS.txt"
        )
        self.assertTrue(sums_path.exists())
        lines = sums_path.read_text().strip().splitlines()
        self.assertEqual(len(lines), 12)  # relay-only artifact is excluded
        manifest = json.loads((self.root / "docs/data/manifest.json").read_text())
        by_file = {
            a["file"]: a["sha256"]
            for a in manifest["products"][0]["artifacts"]
            if a["mirrored"]
        }
        for line in lines:
            sha, filename = line.split("  ", 1)
            self.assertEqual(by_file[filename], sha)
            actual = hashlib.sha256(
                (self.root / ".cache/downloads/claude-desktop/2.42304.0" / filename).read_bytes()
            ).hexdigest()
            self.assertEqual(sha, actual)
        self.assertIn((tag, "SHA256SUMS.txt"), gh.uploaded)

    def test_publish_creates_release_and_uploads_all_assets(self):
        _, transfer, gh, _ = self._publish_all()
        self.assertEqual(len(transfer.calls), 17)  # 12 mirrored desktop + 5 science
        self.assertEqual(gh.created, ["desktop-v2.42304.0", "science-v0.1.63"])
        self.assertEqual(len(gh.uploaded), 19)  # 12 + 1 sums, 5 + 1 sums


# ---------------------------------------------------------------------------
# Idempotency, dry-run, force, missing assets, excludes
# ---------------------------------------------------------------------------


class PublishFlowTests(TempRootCase):
    def _http(self):
        d = desktop_http()
        s = science_http()
        return FakeHttp(
            {**d.json_map, **s.json_map},
            {**d.head_map, **s.head_map},
            {**d.range_map, **s.range_map},
        )

    def test_second_run_is_byte_identical_and_inert(self):
        http = self._http()
        transfer = FakeTransfer()
        gh = FakeGh()
        mirror = self.engine(http=http, transfer=transfer, gh=gh)
        self.assertEqual(mirror.publish(["desktop", "science"]), 0)
        before = (self.root / "docs/data/manifest.json").read_bytes()
        downloads = len(transfer.calls)
        uploads = len(gh.uploaded)
        lookup_count = len(gh.created)

        second = self.engine(http=http, transfer=transfer, gh=gh)
        self.assertEqual(second.publish(["desktop", "science"]), 0)
        after = (self.root / "docs/data/manifest.json").read_bytes()
        self.assertEqual(before, after)
        self.assertEqual(len(transfer.calls), downloads)
        self.assertEqual(len(gh.uploaded), uploads)
        self.assertEqual(len(gh.created), lookup_count)
        # A no-op run makes no release/upload calls at all.
        self.assertEqual(len(gh.created), 2)

    def test_dry_run_writes_nothing(self):
        transfer = FakeTransfer()
        gh = FakeGh()
        mirror = self.engine(http=self._http(), transfer=transfer, gh=gh)
        out = io.StringIO()
        with redirect_stdout(out):
            rc = mirror.publish(["desktop", "science"], dry_run=True)
        self.assertEqual(rc, 0)
        text = out.getvalue()
        self.assertIn("download https://downloads.claude.ai", text)
        self.assertIn("create release desktop-v2.42304.0", text)
        self.assertIn("upload Claude-Desktop-2.42304.0-macOS-universal.dmg", text)
        self.assertIn("relay-only Claude-Desktop-2.42304.0-Windows-x64-offline.msix", text)
        self.assertIn("dry run: no downloads", text)
        self.assertEqual(transfer.calls, [])
        self.assertEqual(gh.created, [])
        self.assertEqual(gh.uploaded, [])
        self.assertFalse((self.root / "docs/data/manifest.json").exists())
        self.assertFalse((self.root / "docs/data/manifest.js").exists())
        self.assertFalse((self.root / "docs/relay").exists())
        self.assertFalse((self.root / ".cache").exists())

    def test_dry_run_unchanged_reports_no_work_and_writes_nothing(self):
        transfer = FakeTransfer()
        gh = FakeGh()
        first = self.engine(http=self._http(), transfer=transfer, gh=gh)
        first.publish(["desktop", "science"])
        before = (self.root / "docs/data/manifest.json").read_bytes()
        downloads = len(transfer.calls)
        uploads = len(gh.uploaded)

        second = self.engine(http=self._http(), transfer=transfer, gh=gh)
        out = io.StringIO()
        with redirect_stdout(out):
            rc = second.publish(["desktop", "science"], dry_run=True)
        self.assertEqual(rc, 0)
        self.assertIn("no changes", out.getvalue())
        self.assertEqual(len(transfer.calls), downloads)
        self.assertEqual(len(gh.uploaded), uploads)
        self.assertEqual((self.root / "docs/data/manifest.json").read_bytes(), before)

    def test_dry_run_survives_gh_failure(self):
        mirror = self.engine(
            http=self._http(), transfer=FakeTransfer(), gh=FakeGh(fail_lookup=True)
        )
        out = io.StringIO()
        with redirect_stdout(out):
            rc = mirror.publish(["desktop"], dry_run=True)
        self.assertEqual(rc, 0)
        self.assertIn("state unknown", out.getvalue())
        self.assertFalse((self.root / "docs/data/manifest.json").exists())

    def test_unchanged_publish_recreates_missing_relay_page_only(self):
        transfer = FakeTransfer()
        gh = FakeGh()
        first = self.engine(http=self._http(), transfer=transfer, gh=gh)
        first.publish(["desktop", "science"])
        before = (self.root / "docs/data/manifest.json").read_bytes()
        page = self.root / "docs/relay/windows-x64-offline.html"
        page.unlink()
        downloads = len(transfer.calls)
        uploads = len(gh.uploaded)

        second = self.engine(http=self._http(), transfer=transfer, gh=gh)
        second.publish(["desktop", "science"])
        self.assertEqual((self.root / "docs/data/manifest.json").read_bytes(), before)
        self.assertTrue(page.exists())
        self.assertEqual(len(transfer.calls), downloads)
        self.assertEqual(len(gh.uploaded), uploads)

    def test_existing_release_uploads_only_missing_assets(self):
        gh = FakeGh(
            releases=["desktop-v2.42304.0"],
            assets={
                "desktop-v2.42304.0": {
                    "Claude-Desktop-2.42304.0-macOS-universal.dmg",
                }
            },
        )
        mirror = self.engine(http=desktop_http(), transfer=FakeTransfer(), gh=gh)
        self.assertEqual(
            mirror.publish(["desktop"],
                          excludes=[d.id for d in engine.DESKTOP_DEFS[1:]]),
            0,
        )
        self.assertEqual(gh.created, [])
        uploaded = [name for _, name in gh.uploaded]
        self.assertNotIn("Claude-Desktop-2.42304.0-macOS-universal.dmg", uploaded)
        self.assertIn("SHA256SUMS.txt", uploaded)

    def test_force_republishes_and_clobbers(self):
        transfer = FakeTransfer()
        gh = FakeGh()
        mirror = self.engine(http=desktop_http(), transfer=transfer, gh=gh)
        mirror.publish(["desktop"])
        first_uploads = len(gh.uploaded)
        first_downloads = len(transfer.calls)

        mirror2 = self.engine(http=desktop_http(), transfer=transfer, gh=gh)
        self.assertEqual(mirror2.publish(["desktop"], force=True), 0)
        self.assertGreater(len(gh.uploaded), first_uploads)
        self.assertTrue(any(gh.clobbers))
        # Cached files are reused, not re-downloaded.
        self.assertEqual(len(transfer.calls), first_downloads)

    def test_science_official_hash_mismatch_fails_publish(self):
        s = science_http(hash_overrides={"science-windows-x64": "0" * 64})
        http = FakeHttp(s.json_map, s.head_map, s.range_map)
        mirror = self.engine(http=http, transfer=FakeTransfer(), gh=FakeGh())
        with self.assertRaisesRegex(engine.MirrorError, "SHA-256 mismatch"):
            mirror.publish(["science"])

    def test_science_manifest_is_fetched_once(self):
        s = science_http()
        http = FakeHttp(s.json_map, s.head_map, s.range_map)
        mirror = self.engine(http=http, transfer=FakeTransfer(), gh=FakeGh())
        with redirect_stdout(io.StringIO()):
            mirror.publish(["science"])
        manifest_url = "https://downloads.claude.ai/claude-science/latest/manifest.json"
        self.assertEqual(http.json_calls.count(manifest_url), 1)

    def test_reused_release_does_not_create(self):
        gh = FakeGh(releases=["desktop-v2.42304.0"])
        mirror = self.engine(http=desktop_http(), transfer=FakeTransfer(), gh=gh)
        mirror.publish(["desktop"])
        self.assertEqual(gh.created, [])

    def test_exclude_removes_artifact_from_manifest(self):
        transfer = FakeTransfer()
        mirror = self.engine(http=desktop_http(), transfer=transfer, gh=FakeGh())
        mirror.publish(["desktop"], excludes=["macos-intel-offline"])
        manifest = json.loads((self.root / "docs/data/manifest.json").read_text())
        ids = [a["id"] for a in manifest["products"][0]["artifacts"]]
        self.assertNotIn("macos-intel-offline", ids)
        self.assertEqual(len(ids), 12)
        self.assertNotIn(
            "https://downloads.claude.ai/releases/darwin/x64/offline/Claude-1.bin",
            [call[0] for call in transfer.calls],
        )

    def test_unknown_exclude_is_an_error(self):
        mirror = self.engine(http=desktop_http())
        with self.assertRaisesRegex(engine.MirrorError, "unknown artifact"):
            mirror.publish(["desktop"], excludes=["nope"])

    def test_commit_runs_git_add_and_commit(self):
        runner = FakeRunner()
        mirror = self.engine(http=desktop_http(), runner=runner)
        mirror.publish(["desktop"], commit=True)
        commands = [call[0] for call in runner.calls]
        add_command = next(cmd for cmd in commands if cmd[:2] == ["git", "add"])
        self.assertIn("docs/data/manifest.json", add_command)
        self.assertIn("docs/data/manifest.js", add_command)
        self.assertIn("docs/relay", add_command)
        self.assertTrue(any(cmd[:2] == ["git", "commit"] for cmd in commands))
        self.assertFalse(any(cmd[:2] == ["git", "push"] for cmd in commands))

    def test_push_requires_explicit_flag(self):
        runner = FakeRunner()
        mirror = self.engine(http=desktop_http(), runner=runner)
        mirror.publish(["desktop"], push=True)
        commands = [call[0] for call in runner.calls]
        self.assertTrue(any(cmd[:2] == ["git", "add"] for cmd in commands))
        self.assertTrue(any(cmd[:2] == ["git", "commit"] for cmd in commands))
        self.assertTrue(any(cmd[:2] == ["git", "push"] for cmd in commands))

    def test_push_is_not_triggered_by_commit(self):
        runner = FakeRunner()
        mirror = self.engine(http=desktop_http(), runner=runner)
        mirror.publish(["desktop"], commit=True)
        self.assertFalse(
            any(call[0][:2] == ["git", "push"] for call in runner.calls)
        )

    def test_both_products_ordering_in_manifest(self):
        mirror = self.engine(http=self._http())
        mirror.publish(["desktop", "science"])
        manifest = json.loads((self.root / "docs/data/manifest.json").read_text())
        self.assertEqual([p["id"] for p in manifest["products"]],
                         ["claude-desktop", "claude-science"])

    def test_partial_product_publish_preserves_other(self):
        mirror = self.engine(http=self._http())
        mirror.publish(["desktop", "science"])
        before = json.loads((self.root / "docs/data/manifest.json").read_text())
        mirror.publish(["desktop"], force=True)
        after = json.loads((self.root / "docs/data/manifest.json").read_text())
        self.assertEqual(before["products"][1], after["products"][1])


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------


    def test_publish_code_creates_release_and_uploads_all_assets(self):
        gh = FakeGh()
        mirror = self.engine(http=code_http(), transfer=FakeTransfer(), gh=gh)
        self.assertEqual(mirror.publish(["code"]), 0)
        self.assertIn("code-v2.1.302", gh.created)
        self.assertEqual(len(gh.uploaded), 9)
        manifest = json.loads(
            (self.root / "docs/data/manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual([p["id"] for p in manifest["products"]], ["claude-code"])
        product = manifest["products"][0]
        self.assertEqual(product["version"], "2.1.302")
        self.assertEqual(len(product["artifacts"]), 8)
        self.assertTrue(all(a["mirrored"] for a in product["artifacts"]))
        self.assertTrue(
            all("code-v2.1.302" in a["download_url"] for a in product["artifacts"])
        )


class VerifyTests(TempRootCase):
    def _valid_manifest(self):
        d = desktop_http()
        s = science_http()
        c = code_http()
        http = FakeHttp(
            {**d.json_map, **s.json_map, **c.json_map},
            {**d.head_map, **s.head_map, **c.head_map},
            {**d.range_map, **s.range_map, **c.range_map},
            text_map={**c.text_map},
        )
        mirror = self.engine(http=http, transfer=FakeTransfer(), gh=FakeGh())
        mirror.publish(["desktop", "science", "code"])
        return json.loads((self.root / "docs/data/manifest.json").read_text())

    def test_valid_manifest_passes(self):
        manifest = self._valid_manifest()
        self.assertEqual(engine.verify_manifest(manifest, self.config), [])

    def test_missing_download_url_field_fails(self):
        manifest = copy.deepcopy(self._valid_manifest())
        del manifest["products"][0]["artifacts"][0]["download_url"]
        errors = engine.verify_manifest(manifest, self.config)
        self.assertTrue(any("download_url" in e for e in errors))

    def test_download_url_wrong_tag_fails(self):
        manifest = copy.deepcopy(self._valid_manifest())
        manifest["products"][0]["artifacts"][0]["download_url"] = (
            "https://github.com/aresbit/claude-downloads-mirror/releases/download/"
            "desktop-v0.0.0/Claude-Desktop-2.42304.0-macOS-universal.dmg"
        )
        errors = engine.verify_manifest(manifest, self.config)
        self.assertTrue(any("download_url" in e for e in errors))

    def test_bad_sha_fails(self):
        manifest = copy.deepcopy(self._valid_manifest())
        manifest["products"][0]["artifacts"][0]["sha256"] = "ABC"
        errors = engine.verify_manifest(manifest, self.config)
        self.assertTrue(any("sha256" in e for e in errors))

    def test_wrong_tag_fails(self):
        manifest = copy.deepcopy(self._valid_manifest())
        manifest["products"][1]["tag"] = "desktop-v0.1.63"
        errors = engine.verify_manifest(manifest, self.config)
        self.assertTrue(any("tag" in e for e in errors))

    def test_oversized_asset_fails(self):
        manifest = copy.deepcopy(self._valid_manifest())
        manifest["products"][0]["artifacts"][0]["size"] = 2_147_483_648
        errors = engine.verify_manifest(manifest, self.config)
        self.assertTrue(any("GitHub asset limit" in e for e in errors))

    def test_relay_artifact_marked_mirrored_fails(self):
        manifest = copy.deepcopy(self._valid_manifest())
        relay = next(
            a for a in manifest["products"][0]["artifacts"]
            if a["id"] == "windows-x64-offline"
        )
        relay["mirrored"] = True
        relay["sha256"] = "0" * 64
        relay["download_url"] = (
            "https://github.com/aresbit/claude-downloads-mirror/releases/download/"
            "desktop-v2.42304.0/Claude-Desktop-2.42304.0-Windows-x64-offline.msix"
        )
        errors = engine.verify_manifest(manifest, self.config)
        self.assertTrue(any("must not be marked mirrored" in e for e in errors))

    def test_relay_artifact_with_sha_fails(self):
        manifest = copy.deepcopy(self._valid_manifest())
        relay = next(
            a for a in manifest["products"][0]["artifacts"]
            if a["id"] == "windows-x64-offline"
        )
        relay["sha256"] = "0" * 64
        errors = engine.verify_manifest(manifest, self.config)
        self.assertTrue(any("must omit sha256" in e for e in errors))

    def test_relay_artifact_with_download_url_fails(self):
        manifest = copy.deepcopy(self._valid_manifest())
        relay = next(
            a for a in manifest["products"][0]["artifacts"]
            if a["id"] == "windows-x64-offline"
        )
        relay["download_url"] = "https://example.test/x"
        errors = engine.verify_manifest(manifest, self.config)
        self.assertTrue(any("download_url: null" in e for e in errors))

    def test_verify_command_fails_when_relay_page_missing(self):
        self._valid_manifest()
        page = self.root / "docs/relay/windows-x64-offline.html"
        page.unlink()
        mirror = self.engine(http=desktop_http())
        self.assertEqual(mirror.verify(), 1)

    def test_unsorted_artifacts_fail(self):
        manifest = copy.deepcopy(self._valid_manifest())
        manifest["products"][0]["artifacts"].reverse()
        errors = engine.verify_manifest(manifest, self.config)
        self.assertTrue(any("ordered macOS" in e for e in errors))

    def test_products_wrong_order_fail(self):
        manifest = copy.deepcopy(self._valid_manifest())
        manifest["products"].reverse()
        errors = engine.verify_manifest(manifest, self.config)
        self.assertTrue(any("desktop then science" in e for e in errors))

    def test_verify_command_nonzero_on_broken_manifest(self):
        path = self.root / "docs/data/manifest.json"
        path.write_text('{"schema_version": 1}')
        mirror = self.engine(http=desktop_http())
        self.assertEqual(mirror.verify(), 1)

    def test_verify_command_zero_on_valid_manifest(self):
        self._valid_manifest()
        mirror = self.engine(http=desktop_http())
        self.assertEqual(mirror.verify(), 0)


# ---------------------------------------------------------------------------
# Probe
# ---------------------------------------------------------------------------


    def _combined_http(self):
        d = desktop_http()
        s = science_http()
        return FakeHttp(
            {**d.json_map, **s.json_map},
            {**d.head_map, **s.head_map},
            {**d.range_map, **s.range_map},
        )

    def _mark_sample(self):
        path = self.root / "docs/data/manifest.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["sample"] = True
        body = json.dumps(data, indent=2) + "\n"
        path.write_text(body, encoding="utf-8")
        (self.root / "docs/data/manifest.js").write_text(
            f"window.MIRROR_MANIFEST = {body};",
            encoding="utf-8",
        )
        return data

    def test_sample_fixture_rejected_unless_allowed(self):
        self._valid_manifest()
        self._mark_sample()
        mirror = self.engine(
            http=self._combined_http(), transfer=FakeTransfer(), gh=FakeGh()
        )
        with redirect_stderr(io.StringIO()):
            self.assertEqual(mirror.verify(), 1)
            self.assertEqual(mirror.verify(allow_sample=True), 0)

    def test_manifest_js_mismatch_fails(self):
        self._valid_manifest()
        (self.root / "docs/data/manifest.js").write_text(
            "window.MIRROR_MANIFEST = {};\n", encoding="utf-8"
        )
        mirror = self.engine(
            http=self._combined_http(), transfer=FakeTransfer(), gh=FakeGh()
        )
        with redirect_stderr(io.StringIO()):
            self.assertEqual(mirror.verify(), 1)

    def test_sample_fixture_forces_full_publish_on_dry_run(self):
        self._valid_manifest()
        self._mark_sample()
        transfer = FakeTransfer()
        gh = FakeGh()
        mirror = self.engine(
            http=self._combined_http(), transfer=transfer, gh=gh
        )
        out = io.StringIO()
        with redirect_stdout(out):
            rc = mirror.publish(["desktop", "science"], dry_run=True)
        self.assertEqual(rc, 0)
        text = out.getvalue()
        self.assertIn("new product", text)
        self.assertIn("download https://downloads.claude.ai", text)
        self.assertNotIn("no changes; manifest unchanged", text)
        self.assertEqual(transfer.calls, [])
        self.assertEqual(gh.created, [])
        self.assertTrue(
            json.loads(
                (self.root / "docs/data/manifest.json").read_text(encoding="utf-8")
            )["sample"]
        )

    def test_relay_page_is_localized_and_contains_source(self):
        manifest = self._valid_manifest()
        page = self.root / "docs/relay/windows-x64-offline.html"
        body = page.read_text(encoding="utf-8")
        relay = next(
            artifact
            for artifact in manifest["products"][0]["artifacts"]
            if artifact["id"] == "windows-x64-offline"
        )
        self.assertIn('lang="zh-CN"', body)
        self.assertIn('content="2;', body)
        self.assertIn("返回镜像首页", body)
        self.assertIn(relay["source_url"], body)


class ProbeTests(TempRootCase):
    def test_probe_json_exit_zero(self):
        d = desktop_http()
        s = science_http()
        http = FakeHttp(
            {**d.json_map, **s.json_map},
            {**d.head_map, **s.head_map},
            {**d.range_map, **s.range_map},
        )
        mirror = self.engine(http=http)
        out = io.StringIO()
        with redirect_stdout(out):
            code, products, errors = mirror.probe(["desktop", "science"], as_json=True)
        self.assertEqual(code, 0)
        self.assertEqual(errors, [])
        payload = json.loads(out.getvalue())
        self.assertEqual([p["id"] for p in payload["products"]],
                         ["claude-desktop", "claude-science"])
        self.assertEqual(len(payload["products"][0]["artifacts"]), 13)
        self.assertEqual(len(payload["products"][1]["artifacts"]), 5)
        total = sum(len(p["artifacts"]) for p in payload["products"])
        self.assertEqual(total, 18)
        relay = next(
            a for a in payload["products"][0]["artifacts"]
            if a["id"] == "windows-x64-offline"
        )
        self.assertFalse(relay["mirrored"])
        self.assertEqual(relay["relay_url"], "relay/windows-x64-offline.html")
        arm64 = next(
            a for a in payload["products"][1]["artifacts"]
            if a["id"] == "science-windows-arm64"
        )
        self.assertTrue(arm64["mirrored"])
        self.assertEqual(arm64["file"], "Claude-Science-0.1.63-Windows-arm64.exe")
        self.assertEqual(arm64["source_url"],
                         "https://downloads.claude.ai/claude-science/0.1.63/windows-arm64.exe")

    def test_probe_tolerates_partial_failure(self):
        http = desktop_http()
        http.json_map.pop(
            "https://api.anthropic.com/api/desktop/darwin/universal/dmg/latest"
        )
        mirror = self.engine(http=http)
        out = io.StringIO()
        with redirect_stdout(out):
            code, products, errors = mirror.probe(["desktop"], as_json=True)
        self.assertEqual(code, 0)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["artifact"], "macos-universal")
        self.assertEqual(len(products[0]["artifacts"]), 12)


if __name__ == "__main__":
    unittest.main()
