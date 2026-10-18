# Mirror brief — downloads.claude.ai → GitHub Pages + Releases

Verified 2026-10-17. This file is the shared contract for all team members.

## Mission

Rebuild `downloads.claude.ai` as a self-hosted static mirror:

- Portal published by GitHub Pages from `docs/`.
- Installers stored as **versioned GitHub Release assets** (one release per product version).
- The portal reads a generated `docs/data/manifest.json`; it never hardcodes release URLs.
- Updates are **manual**: the maintainer runs `python3 scripts/mirror.py publish`.
  No cron, no schedule, no auto-update workflow.
- No secrets beyond the maintainer's existing `gh` login.

## Source facts

`downloads.claude.ai` is a Google Cloud Storage bucket with public object reads but
directory listing disabled (root returns `403 AccessDenied`). There is no browsable
index and no directory listing to crawl. Artifact URLs must be discovered through the
official update API and fixed aliases.

### Claude Desktop — version API (no auth, no Cloudflare challenge)

```text
GET https://api.anthropic.com/api/desktop/<platform>/<arch>/<variant>/latest
→ {"version":"2.42304.0","url":"https://downloads.claude.ai/releases/.../Claude-<sha>.dmg"}
```

Do **not** use `claude.ai/api/desktop/...` — it is behind a Cloudflare challenge (403
"Just a moment..."). The `api.anthropic.com` host returns clean JSON.

Artifact matrix (all version `2.42304.0` at discovery time):

| id | platform/arch/variant | source filename / notes |
|---|---|---|
| macos-universal | darwin/universal/dmg | `Claude.dmg`, 388,258,098 B |
| macos-intel-offline | darwin/x64/offline | `Claude-offline-darwin-x64-2.42304.0.dmg`, 2,078,252,702 B |
| macos-apple-silicon-offline | darwin/arm64/offline | `Claude-offline-darwin-arm64-2.42304.0.dmg`, 2,000,405,037 B |
| windows-x64-setup | win32/x64/setup | `ClaudeSetup-<sha>.exe` (online bootstrapper) |
| windows-arm64-setup | win32/arm64/setup | `ClaudeSetup-<sha>.exe` |
| windows-x64-exe | win32/x64/exe | `Claude-<sha>.exe` |
| windows-arm64-exe | win32/arm64/exe | `Claude-<sha>.exe` |
| windows-x64-msix | win32/x64/msix | `Claude-<sha>.msix` |
| windows-arm64-msix | win32/arm64/msix | `Claude-<sha>.msix` |
| windows-x64-offline | win32/x64/offline | `Claude-offline-win32-x64-2.42304.0.msix`, **2,220,697,207 B — NOT mirrored: over GitHub's 2 GiB cap; relay only** |
| windows-arm64-offline | win32/arm64/offline | `Claude-offline-win32-arm64-2.42304.0.msix`, 2,142,449,767 B (only 5,033,881 B under cap) |
| linux-x64-deb | linux/x64/deb | `claude-desktop_amd64.deb`, 183,117,920 B |
| linux-arm64-deb | linux/arm64/deb | `claude-desktop_arm64.deb`, 176,002,208 B |

Excluded from the public portal: `linux/x64/cowork-readiness-check` (internal probe,
not an installer).

### Claude Science — fixed latest aliases (no version API)

```text
https://downloads.claude.ai/claude-science/latest/mac-arm64.dmg       # Claude-Science-<v>.dmg
https://downloads.claude.ai/claude-science/latest/mac-x64.dmg         # Claude-Science-<v>-Intel.dmg
https://downloads.claude.ai/claude-science/latest/windows-x64.exe     # Claude-Science-<v>.exe
https://downloads.claude.ai/claude-science/latest/windows-arm64.exe   # Claude-Science-<v>-arm64.exe
https://downloads.claude.ai/claude-science/latest/linux-x64           # claude-science-<v>-linux-x64
```

Version is in `Content-Disposition` (`attachment; filename="Claude-Science-0.1.63.dmg"`).
Versioned paths also work: `/claude-science/<version>/<same-name>`.
Current version: `0.1.63`, build date `2026-10-14T23:31:23Z`.
No arm64 Linux or universal macOS variant exists (verified 404).

**Official Science manifest:** `https://downloads.claude.ai/claude-science/latest/manifest.json`
returns `version`, `sha8`, `buildDate`, `sha256` (per executable) and `dmg_sha256`
(per DMG). Use `dmg_sha256` for the two DMGs and `sha256` for the EXE/Linux binaries.

## Critical constraints

- GitHub release assets: **strictly under 2 GiB** (2,147,483,648 B; official wording
  "under 2 GiB"). A `HEAD` may omit `Content-Length`; use `x-goog-stored-content-length`
  or a `Range: bytes=0-0` GET and parse `Content-Range`.
- **Over-limit policy (user decision, 2026-10-17): no splitting and no failure.**
  Any artifact ≥ 2,147,483,648 B is *not* uploaded. It is recorded in the manifest with
  `"mirrored": false`, its true size and `source_url`, plus a generated relay page
  `docs/relay/<id>.html` that redirects to the official source. The portal labels it
  "中转下载 / 官方源".
  Current affected artifact: `windows-x64-offline`.
- GitHub Pages site: serve from `docs/` on the default branch, plus `docs/.nojekyll`.
- Download URLs have the form
  `https://github.com/<owner>/<repo>/releases/download/<tag>/<asset>`.
- GitHub Pages URL has the form `https://<owner>.github.io/<repo>/`.
- Everything must be idempotent: re-running publish must not duplicate releases/assets.
- Multi-GB downloads must be resumable (`curl -C -` / HTTP Range) and verified by size
  plus SHA-256. Science artifacts also verify against the official manifest hash;
  Desktop artifacts have no published hash, so record the locally computed SHA-256.

## Repo layout and ownership

```text
mirrorrc.json              # owner/repo/branch/site_dir/source endpoints
scripts/mirror.py          # probe → download → verify → release → manifest → publish
scripts/test_mirror.py     # stdlib unittest
docs/index.html            # portal (no build step, no framework)
docs/assets/styles.css
docs/assets/app.js
docs/data/manifest.json    # generated; the only contract between engine and site
docs/.nojekyll
research/                  # brief, findings, evaluation (not published)
README.md                  # quick start + manual publish runbook
```

Ownership: `forge` owns `scripts/`, `mirrorrc.json`, engine docs; `prism` owns `docs/`
except `docs/data/manifest.json`; `scout`/`archivist` write only under `research/`;
`sentinel` writes only `research/evaluation-report.md`.

## Manifest schema (v1)

```json
{
  "schema_version": 1,
  "generated_at": "2026-10-17T08:00:00Z",
  "mirror": {
    "owner": "aresbit",
    "repo": "claude-downloads-mirror",
    "site_url": "https://aresbit.github.io/claude-downloads-mirror/",
    "source": "https://downloads.claude.ai"
  },
  "products": [
    {
      "id": "claude-desktop",
      "name": "Claude Desktop",
      "version": "2.42304.0",
      "tag": "desktop-v2.42304.0",
      "release_url": "https://github.com/aresbit/claude-downloads-mirror/releases/tag/desktop-v2.42304.0",
      "released_at": "2026-10-17T08:00:00Z",
      "artifacts": [
        {
          "id": "macos-universal",
          "os": "macOS",
          "arch": "Universal",
          "variant": "Installer",
          "file": "Claude-Desktop-2.42304.0-macOS-universal.dmg",
          "size": 388258098,
          "mirrored": true,
          "sha256": "…",
          "download_url": "https://github.com/aresbit/claude-downloads-mirror/releases/download/desktop-v2.42304.0/Claude-Desktop-2.42304.0-macOS-universal.dmg",
          "source_url": "https://downloads.claude.ai/releases/darwin/universal/2.42304.0/Claude-<sha>.dmg"
        }
```

Over-limit artifacts appear in the same array but with
`"mirrored": false`, `"download_url": null`, `"relay_url": "relay/<id>.html"`, and no
`sha256` (unknown until downloaded, which we intentionally do not do). Example:

```json
{
  "id": "windows-x64-offline",
  "os": "Windows",
  "arch": "x64",
  "variant": "Offline MSIX",
  "file": "Claude-Desktop-2.42304.0-Windows-x64-offline.msix",
  "size": 2220697207,
  "mirrored": false,
  "download_url": null,
  "relay_url": "relay/windows-x64-offline.html",
  "source_url": "https://downloads.claude.ai/releases-offline/win32/x64/2.42304.0/Claude-<sha>-offline.msix"
}
```

Artifacts are sorted in the engine (macOS, Windows, Linux; stable within OS). The site
must render gracefully when a product or artifact is absent and must never invent data.
Expected inventory: 18 artifacts total (13 Desktop + 5 Science), of which 17 are mirrored
and `windows-x64-offline` is relay-only.

## Definition of done

1. `python3 scripts/mirror.py probe` prints the live 18-artifact matrix as JSON and exits 0.
2. `python3 -m unittest scripts/test_mirror.py -v` passes.
3. `python3 scripts/mirror.py publish --dry-run` resolves versions, validates the
   manifest/site, performs no downloads and writes nothing remote. It may make read-only
   version/HEAD requests; idempotency is defined as **no remote mutations and an
   unchanged manifest** on a second run.
4. `docs/index.html` renders both products from `docs/data/manifest.json`, links every
   mirrored artifact to its GitHub Release URL, routes the over-limit artifact through
   its relay page, shows size + SHA-256, and works on a static host.
5. README documents: create repo → enable Pages (`/docs`) → run publish → verify.
6. Independent evaluator finds no blocking defects; report stored in
   `research/evaluation-report.md`.

## Amendment 1 — 2026-10-17 (after live inventory)

This supersedes any conflicting sentence above.

1. **Claude Science has 5 artifacts**, not 4: `mac-arm64.dmg`, `mac-x64.dmg`,
   `windows-x64.exe`, `windows-arm64.exe`, `linux-x64`. The last two are 154,804,896 B
   and 150,714,336 B. Official SHA-256 is published in
   `https://downloads.claude.ai/claude-science/latest/manifest.json`; use `dmg_sha256`
   for DMGs, `sha256` for EXE/Linux. **Verified 2026-10-17:** the downloaded
   `Claude-Science-0.1.63.dmg` (mac-arm64) hashes to
   `4522773ec26c0f62977ff746f33cf968fe6cab6bad7c9fdf617adff5481714cb`, exactly
   `dmg_sha256.darwin-arm64` (not `sha256.darwin-arm64`); the Windows x64 EXE hashes
   to `2aaf4d4c051499943ad2ad340906193b4ca212cf46d7b50b060cc53f34cf4f0e`, exactly
   `sha256.windows-x64`. Pin downloads to
   `/claude-science/0.1.63/...`, not `latest`, so an alias flip mid-publish cannot mix
   versions.
2. **Do not mirror `windows-x64-offline` (2,220,697,207 B).** Per user decision, no
   splitting: record it as `mirrored:false` with a relay page to the official URL.
   Never upload an asset ≥ 2,147,483,648 B; `verify` must fail if one is marked mirrored.
3. GitHub boundary is strict: allowed `< 2,147,483,648`; reject exactly 2,147,483,648.
   `windows-arm64-offline` (2,142,449,767 B) is allowed but only 5 MB of headroom — if a
   future build crosses the line it automatically becomes relay-only.
4. **HEAD trap:** direct release objects may return `x-goog-stored-content-length` and no
   `Content-Length`. Resolve sizes with `x-goog-stored-content-length`, or a
   `Range: bytes=0-0` GET and parse `Content-Range`. Do not treat a missing
   `Content-Length` as zero.
5. **Content-Disposition names collide** (four `Claude Setup.exe`/`Claude.msix`, two
   debs). Always use the friendly mirror names in this brief.
6. **`--dry-run` semantics:** may perform read-only GET/HEAD; must perform zero
   downloads, zero remote mutations, and leave manifest bytes unchanged. A second
   dry-run must report "no changes" without creating anything.
7. **Manifest canonicality:** `manifest.json` is canonical; `manifest.js` is generated
   from the exact same payload (`window.MIRROR_MANIFEST = ...;`). Publish writes both
   atomically. `--commit` may commit them locally; publish never pushes unless
   `--push` is explicitly passed.
8. **Science relay:** all Science artifacts are mirrored (none over limit).
9. **Expected totals:** 18 artifacts; 17 mirrored; desktop ~10.31 GB source, science
   ~0.64 GB; total ~10.95 GB before excluding the 2.22 GB relay-only asset
   (~8.73 GB actually uploaded).

## Amendment 2 — Claude Code (2026-10-18)

The mirror now covers a third product. This supersedes the inventory in Amendment 1.

- Product id `claude-code`, display name `Claude Code`, tag prefix `code-v`.
- Version discovery: `GET https://downloads.claude.ai/claude-code-releases/latest`
  returns a plain-text version (currently `2.1.302`).
- Build manifest: `GET .../claude-code-releases/<version>/manifest.json` with
  `platforms.<platform>.{binary,checksum,size}`.
- Eight native binaries (no installers): `darwin-arm64`, `darwin-x64`,
  `win32-x64`, `win32-arm64`, `linux-x64`, `linux-x64-musl`, `linux-arm64`,
  `linux-arm64-musl`. Source URL:
  `.../<version>/<platform>/<binary>` (`claude` or `claude.exe`).
- Official SHA-256 is taken from the build manifest and verified after download.
- Sizes are ~268–290 MB each (~2.24 GB total); all are under the 2 GiB asset cap.
- Friendly names: `Claude-Code-<version>-macOS-arm64`, `...-macOS-intel`,
  `...-Windows-x64.exe`, `...-Windows-arm64.exe`, `...-Linux-x64`,
  `...-Linux-x64-musl`, `...-Linux-arm64`, `...-Linux-arm64-musl`.
- Inventory is now **26 artifacts: 25 mirrored + 1 relay-only**
  (`windows-x64-offline`). Total mirror size is ~11.0 GB.
- UI: the “sample data / not yet published” banner was removed at the user's
  request. The fixture still carries `"sample": true` so the engine forces a full
  publish; the site simply renders the fixture without a banner.
