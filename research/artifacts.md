# Artifact inventory — downloads.claude.ai mirror

Probed **2026-10-17 ~07:25–07:55 UTC** by `scout`. Every row below was obtained with a
HEAD request (assets) or GET (version APIs). **No installer was downloaded.** All 18 live
artifacts returned HTTP 200 and every size is filled.

Machine-readable copy: [`probe-matrix.json`](probe-matrix.json). Raw headers:
`research/raw/head/`, `research/raw/head-science/`, `research/raw/neighbors/`,
`research/raw/absence/`.

## Method (reproducible)

Version resolution for Claude Desktop (no auth, no Cloudflare):

```bash
curl -sS --retry 5 --retry-delay 3 --retry-all-errors \
  "https://api.anthropic.com/api/desktop/<platform>/<arch>/<variant>/latest"
```

Size / filename / status for every asset:

```bash
curl -sS --retry 5 --retry-delay 3 --retry-all-errors -I -o /dev/null \
  -D headers.txt -w 'status=%{http_code}\n' "<source_url>"
```

Requests were issued one at a time with `sleep 1` between them. The earlier transient
`CONNECT tunnel failed, response 502` did not recur with this retry setting; all rows
returned 200 on the first successful attempt.

Version API used: `api.anthropic.com` only. `claude.ai/api/...` was not used (Cloudflare 403).

## Claude Desktop

Live version for all 13 rows: **2.42304.0**. Build hash embedded in every filename:
`e7f60e658f15cfece9efa384a78a39aec3c12845`.

| # | product | id | platform | arch | variant | live ver | source URL | source filename (Content-Disposition) | Content-Length (B) | HTTP | surprise |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Claude Desktop | macos-universal | darwin | universal | dmg | 2.42304.0 | https://downloads.claude.ai/releases/darwin/universal/2.42304.0/Claude-e7f60e658f15cfece9efa384a78a39aec3c12845.dmg | `Claude.dmg` | 388,258,098 | 200 | Filename has no version/hash/arch — must rename in mirror |
| 2 | Claude Desktop | macos-intel-offline | darwin | x64 | offline | 2.42304.0 | https://downloads.claude.ai/releases-offline/darwin/x64/2.42304.0/Claude-e7f60e658f15cfece9efa384a78a39aec3c12845-offline.dmg | `Claude-offline-darwin-x64-2.42304.0.dmg` | 2,078,252,702 | 200 | Uses `/releases-offline/`; 69,230,946 B under the 2 GiB GitHub cap |
| 3 | Claude Desktop | macos-apple-silicon-offline | darwin | arm64 | offline | 2.42304.0 | https://downloads.claude.ai/releases-offline/darwin/arm64/2.42304.0/Claude-e7f60e658f15cfece9efa384a78a39aec3c12845-offline.dmg | `Claude-offline-darwin-arm64-2.42304.0.dmg` | 2,000,405,037 | 200 | Uses `/releases-offline/`; 147,078,611 B under cap |
| 4 | Claude Desktop | windows-x64-setup | win32 | x64 | setup | 2.42304.0 | https://downloads.claude.ai/releases/win32/x64/2.42304.0/ClaudeSetup-e7f60e658f15cfece9efa384a78a39aec3c12845.exe | `Claude Setup.exe` | 7,178,400 | 200 | Generic filename; 7 MB online bootstrapper, not a full installer |
| 5 | Claude Desktop | windows-arm64-setup | win32 | arm64 | setup | 2.42304.0 | https://downloads.claude.ai/releases/win32/arm64/2.42304.0/ClaudeSetup-e7f60e658f15cfece9efa384a78a39aec3c12845.exe | `Claude Setup.exe` | 6,579,360 | 200 | Same generic filename as x64 setup — collision if used as asset name |
| 6 | Claude Desktop | windows-x64-exe | win32 | x64 | exe | 2.42304.0 | https://downloads.claude.ai/releases/win32/x64/2.42304.0/Claude-e7f60e658f15cfece9efa384a78a39aec3c12845.exe | `Claude Setup.exe` | 262,888,096 | 200 | Served as "Claude Setup.exe", indistinguishable from setup variants by name |
| 7 | Claude Desktop | windows-arm64-exe | win32 | arm64 | exe | 2.42304.0 | https://downloads.claude.ai/releases/win32/arm64/2.42304.0/Claude-e7f60e658f15cfece9efa384a78a39aec3c12845.exe | `Claude Setup.exe` | 257,629,856 | 200 | Same generic filename as #4/#6 |
| 8 | Claude Desktop | windows-x64-msix | win32 | x64 | msix | 2.42304.0 | https://downloads.claude.ai/releases/win32/x64/2.42304.0/Claude-e7f60e658f15cfece9efa384a78a39aec3c12845.msix | `Claude.msix` | 297,191,037 | 200 | No version in filename |
| 9 | Claude Desktop | windows-arm64-msix | win32 | arm64 | msix | 2.42304.0 | https://downloads.claude.ai/releases/win32/arm64/2.42304.0/Claude-e7f60e658f15cfece9efa384a78a39aec3c12845.msix | `Claude.msix` | 290,955,054 | 200 | Same generic filename as x64 MSIX |
| 10 | Claude Desktop | windows-x64-offline | win32 | x64 | offline | 2.42304.0 | https://downloads.claude.ai/releases-offline/win32/x64/2.42304.0/Claude-e7f60e658f15cfece9efa384a78a39aec3c12845-offline.msix | `Claude-offline-win32-x64-2.42304.0.msix` | **2,220,697,207** | 200 | **EXCEEDS the 2 GiB GitHub Release asset cap by 73,213,559 B (69.83 MiB). Brief missed this.** |
| 11 | Claude Desktop | windows-arm64-offline | win32 | arm64 | offline | 2.42304.0 | https://downloads.claude.ai/releases-offline/win32/arm64/2.42304.0/Claude-e7f60e658f15cfece9efa384a78a39aec3c12845-offline.msix | `Claude-offline-win32-arm64-2.42304.0.msix` | 2,142,449,767 | 200 | Only 5,033,881 B under the 2 GiB cap — dangerously tight; do not assume GitHub's decimal vs binary interpretation |
| 12 | Claude Desktop | linux-x64-deb | linux | x64 | deb | 2.42304.0 | https://downloads.claude.ai/releases/linux/x64/2.42304.0/Claude-e7f60e658f15cfece9efa384a78a39aec3c12845.deb | `claude-desktop_amd64.deb` | 183,117,920 | 200 | Source name uses `amd64`, URL uses `x64` |
| 13 | Claude Desktop | linux-arm64-deb | linux | arm64 | deb | 2.42304.0 | https://downloads.claude.ai/releases/linux/arm64/2.42304.0/Claude-e7f60e658f15cfece9efa384a78a39aec3c12845.deb | `claude-desktop_arm64.deb` | 176,002,208 | 200 | No ARM64 AppImage or RPM exists |

Note: only #2, #3, #10, #11 are under `/releases-offline/`. All others are under
`/releases/`. Both roots are the same GCS bucket; `/releases-offline/` is a path prefix,
not a different service.

Excluded but live (not an installer, do not publish): `linux/x64/cowork-readiness-check`
resolves via the API to `https://downloads.claude.ai/releases/linux/x64/2.42304.0/cowork-readiness-check-e7f60e658f15cfece9efa384a78a39aec3c12845`
(version 2.42304.0, HTTP 200). The API enumerates Linux variants as exactly
`deb, cowork-readiness-check`.

## Claude Science

No version API. Fixed `latest` aliases; version comes from `Content-Disposition`.
Live version: **0.1.63** (manifest `sha8`: `98087847`, build date `2026-10-14T23:31:23Z`).

| # | product | id | platform | arch | variant | live ver | source URL | source filename (Content-Disposition) | Content-Length (B) | HTTP | surprise |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 14 | Claude Science | claude-science-macos-arm64 | darwin | arm64 | dmg | 0.1.63 | https://downloads.claude.ai/claude-science/latest/mac-arm64.dmg | `Claude-Science-0.1.63.dmg` | 79,907,185 | 200 | — |
| 15 | Claude Science | claude-science-macos-intel | darwin | x64 | dmg | 0.1.63 | https://downloads.claude.ai/claude-science/latest/mac-x64.dmg | `Claude-Science-0.1.63-Intel.dmg` | 84,030,121 | 200 | Filename says `Intel`, not `x64` |
| 16 | Claude Science | claude-science-windows-x64 | win32 | x64 | exe | 0.1.63 | https://downloads.claude.ai/claude-science/latest/windows-x64.exe | `Claude-Science-0.1.63.exe` | 168,830,624 | 200 | — |
| 17 | Claude Science | claude-science-windows-arm64 | win32 | arm64 | exe | 0.1.63 | https://downloads.claude.ai/claude-science/latest/windows-arm64.exe | `Claude-Science-0.1.63-arm64.exe` | 154,804,896 | 200 | **SURPRISE: the brief says this does not exist. It does, and `manifest.json` publishes its SHA-256. Bare `windows-arm64` is 404; the `.exe` alias is 200.** |
| 18 | Claude Science | claude-science-linux-x64 | linux | x64 | bin | 0.1.63 | https://downloads.claude.ai/claude-science/latest/linux-x64 | `claude-science-0.1.63-linux-x64` | 150,714,336 | 200 | Extensionless standalone binary |

Versioned paths `/claude-science/0.1.63/<same-name>` all return 200 and are the stable
choice for pinning. All five versioned paths were HEAD-checked successfully.

### Claude Science manifest (public, extra discovery)

`https://downloads.claude.ai/claude-science/latest/manifest.json` → HTTP 200, 944 B,
`content-type: application/json`. It is an official signed-ish build manifest and gives
the expected SHA-256 for every platform, including Windows ARM64:

```json
{
  "version": "0.1.63",
  "sha8": "98087847",
  "buildDate": "2026-10-14T23:31:23Z",
  "sha256": {
    "linux-x64": "8d3e659c27b0083918aaa9f5284174434ef1fc07af216d2a833c560d405bf716",
    "darwin-arm64": "ccd317d1b1733a2054be92ac1bb7023a8f785d4515e20f517a328d0ccda4a479",
    "darwin-x64": "1b314bbe0d4b5b0697cccc5e8baa02b0b0eda71faf3270ce21f8a6f9340496ed",
    "windows-x64": "2aaf4d4c051499943ad2ad340906193b4ca212cf46d7b50b060cc53f34cf4f0e",
    "windows-arm64": "45bda5c5666f51dbf63ea3dd397f1f1ecd362f65060fa09035da073d7633d947"
  },
  "dmg_sha256": { "darwin-arm64": "...", "darwin-x64": "..." },
  "desktop_app_dmg_sha256": { "darwin-arm64": "...", "darwin-x64": "..." }
}
```

The manifest's `sha256` map is a ready-made verification source for the mirror: download
the installer once, verify against this, then publish. It is keyed `darwin-arm64`,
`darwin-x64`, `windows-x64`, `windows-arm64`, `linux-x64` — not by alias name.

One caveat: `latest` aliases and versioned paths can be **distinct physical objects** with
identical bytes. For `windows-x64.exe` and `linux-x64`, the alias and versioned objects
differ in `x-goog-generation` and composite ETag while sharing `content-length` and
`crc32c`. The DMGs share the same ETag. Use the versioned URL + manifest SHA-256 for
reproducibility; use `latest` only to discover the current version.

## Confirmed absences (HTTP codes)

| Probe | Request | Status | Evidence / note |
|---|---|---|---|
| desktop darwin/arm64/dmg | `GET api.../desktop/darwin/arm64/dmg/latest` | **400** | `"Arch must be universal for darwin platform."` No per-arch macOS DMG. |
| desktop darwin/universal/offline | `GET api.../desktop/darwin/universal/offline/latest` | **400** | `"Arch must be x64 or arm64 for darwin offline variant."` |
| desktop linux appimage (x64) | `GET api.../desktop/linux/x64/appimage/latest` | **400** | `"Variant must be one of deb, cowork-readiness-check for linux platform."` |
| desktop linux appimage (arm64) | `GET api.../desktop/linux/arm64/appimage/latest` | **400** | Same message. |
| linux AppImage direct URLs | HEAD `Claude-<sha>.AppImage`, `.appimage`, `claude-desktop_amd64.AppImage`, `claude-desktop_arm64.AppImage` | **404** | All four spellings 404. No AppImage. |
| science linux-arm64 | HEAD `/claude-science/latest/linux-arm64` | **404** | Also `linux-arm64.deb` 404 and `linux-arm64.AppImage` 404; absent from manifest sha256 map. |
| science windows-arm64 **without** `.exe` | HEAD `/claude-science/latest/windows-arm64` | **404** | But `windows-arm64.exe` is 200 — see #17. |
| science mac-universal | HEAD `/claude-science/latest/mac-universal.dmg` | **404** | Bare `mac-universal` also 404. No universal Science DMG. |
| science pkg/msi | HEAD `mac-arm64.pkg`, `mac-x64.pkg`, `windows-x64.msi`, `windows-arm64.msi` | **404** | No `.pkg` or `.msi` Science builds. |
| win32 exe/msix/offline both arches | HEAD (rows 6–11) | **200** | These are real, not exclusions. All four Win32 variants exist for both x64 and arm64. |
| version directory listing | HEAD `/releases/win32/x64/2.42304.0/` and `/releases/darwin/universal/2.42304.0/` | **404** | No bucket listing. |
| bucket root | HEAD `https://downloads.claude.ai/` | **403** | `AccessDenied` (matches brief). `releases/` and `releases-offline/` prefixes return 404, not 403. |

## Neighbor discovery (bounded, no guessing in the matrix)

| Prefix | Probes | Result |
|---|---|---|
| `claude-code/latest/...` | `linux-x64`, `linux-arm64`, `darwin-arm64`, `darwin-x64`, `win32-x64`, `windows-x64.exe`, `manifest.json`, directory, root | **All 404.** No public `claude-code` assets on this host. |
| `claude-science/latest/...` | `manifest.json` | **200**, 944 B — see above. This is the only extra public Science asset found. |
| `releases/win32/x64/2.42304.0/...` | `Claude-<sha>.msi`, `-offline.exe`, `ClaudeSetup-<sha>-offline.exe`, `ClaudeSetup-<sha>.msi`, `ClaudeSetup-<sha>.msix`, `Claude-<sha>.appx`, `-unsigned.exe` | **All 404.** Only the four variants in the matrix exist. |
| `releases/linux/x64/2.42304.0/...` | `Claude-<sha>.AppImage`, `.rpm`, `.tar.gz`, `-offline.AppImage`, `claude-desktop_amd64.deb` | **All 404.** The deb is served only under the hashed URL. |
| `releases/darwin/universal/2.42304.0/...` | `Claude-<sha>-offline.dmg`, `Claude-2.42304.0.dmg`, `-universal.dmg` | **All 404.** The universal DMG has no offline sibling; offline DMGs live under `/releases-offline/darwin/{x64,arm64}/`. |

Conclusion: the public surface is exactly **13 Claude Desktop artifacts + 5 Claude Science
artifacts + the Science manifest**. No additional public installer families were found.

## GCS object metadata

Every asset is a plain GCS object with `accept-ranges: bytes`, `cache-control:
public,max-age=3600,immutable` (desktop) or `public,max-age=0` (Science aliases), and
`x-goog-hash` md5/crc32c. `probe-matrix.json` records ETag, base64 MD5, base64 CRC32C,
GCS generation, and Last-Modified per object. These are useful as a cheap pre-download
integrity check (MD5) and to detect a re-publish of the same version.

Largest-to-smallest (all bytes):

| Artifact | Bytes | GiB | 2 GiB headroom |
|---|---:|---:|---:|
| windows-x64-offline | 2,220,697,207 | 2.068 | **−73,213,559 (over)** |
| windows-arm64-offline | 2,142,449,767 | 1.995 | +5,033,881 |
| macos-intel-offline | 2,078,252,702 | 1.936 | +69,230,946 |
| macos-apple-silicon-offline | 2,000,405,037 | 1.863 | +147,078,611 |
| macos-universal | 388,258,098 | 0.362 | +1,759,225,550 |
| windows-x64-msix | 297,191,037 | 0.277 | +1,850,292,611 |
| windows-arm64-msix | 290,955,054 | 0.271 | +1,856,528,594 |
| windows-x64-exe | 262,888,096 | 0.245 | +1,884,595,552 |
| windows-arm64-exe | 257,629,856 | 0.240 | +1,889,853,792 |
| linux-x64-deb | 183,117,920 | 0.171 | +1,964,365,728 |
| linux-arm64-deb | 176,002,208 | 0.164 | +1,971,481,440 |
| science windows-x64 | 168,830,624 | 0.157 | +1,978,653,024 |
| science windows-arm64 | 154,804,896 | 0.144 | +1,992,678,752 |
| science linux-x64 | 150,714,336 | 0.140 | +1,996,769,312 |
| science mac-x64 | 84,030,121 | 0.078 | +2,063,453,527 |
| science mac-arm64 | 79,907,185 | 0.074 | +2,067,576,463 |
| windows-x64-setup | 7,178,400 | 0.007 | +2,140,305,248 |
| windows-arm64-setup | 6,579,360 | 0.006 | +2,140,904,288 |

Totals: Desktop **10,311,604,742 B (9.604 GiB)**, Science **638,287,162 B (0.594 GiB)**,
all **10,949,891,904 B (10.198 GiB)**.

## Risks / unknowns

1. **`windows-x64-offline` cannot be a GitHub Release asset.** At 2,220,697,207 B it is
   73,213,559 B (69.83 MiB) over the 2 GiB (2,147,483,648 B) per-file limit. The brief only
   flagged the macOS offline DMGs; the actual hard blocker is the Windows x64 offline MSIX.
   Options (decision not made here): split archive parts, host that one file outside
   Releases, omit it with an explicit "not mirrored" note, or shrink/repack — never silently
   publish a truncated asset. The publish engine must fail closed before upload, not after.
2. **`windows-arm64-offline` is 5,033,881 B under the cap** (4.80 MiB). If GitHub enforces
   2,000,000,000 B decimal instead of 2,147,483,648 B binary, this row *and*
   `macos-intel-offline` (2,078,252,702 B) also fail. Verify GitHub's exact enforcement
   empirically once with a small test asset or read the current docs; keep a per-row
   `max_asset_bytes` guard configurable rather than hardcoding a single assumption.
3. **The two macOS offline DMGs are only 69 MB / 147 MB under the cap.** Any upstream
   rebuild with the same version but a slightly larger payload will break them. Re-probe
   sizes on every publish; do not cache sizes across runs.
4. **Content-Disposition names are non-unique and sometimes generic.** Four Windows
   binaries are all `Claude Setup.exe` / `Claude.msix`; the two debs are
   `claude-desktop_{amd64,arm64}.deb`. The mirror must assign its own versioned asset
   names (as the brief's manifest example does) and must not derive names from the URL
   basename or Content-Disposition without disambiguation.
5. **Brief correction required:** Claude Science **Windows ARM64 exists**
   (`Claude-Science-0.1.63-arm64.exe`, 154,804,896 B, SHA-256 in manifest). The
   "windows-arm64 absent" claim in `brief.md` is false. The Science product now has 5
   artifacts, not 4.
6. **`latest` aliases are mutable and not necessarily the same physical object as the
   versioned path.** For `windows-x64.exe` and `linux-x64`, alias vs versioned objects
   differ in generation/ETag (identical CRC32C and length). Mirror from the versioned URL
   and verify with the manifest SHA-256, so a mid-publish alias flip cannot produce a
   mismatched asset.
7. **No checksum is available from the Desktop API.** Desktop multipart GCS objects expose
   only base64 MD5/CRC32C in response headers; the mirror must still stream each download
   once to compute SHA-256 for the manifest. MD5/CRC32C can be used as a cheap preliminary
   check.
8. **Transient network errors are real.** One `SSL_ERROR_SYSCALL` was observed on a
   `mac-arm64.pkg` probe (retried to a clean 404). Always use
   `--retry 5 --retry-delay 3 --retry-all-errors`; do not interpret a single curl exit 35/56
   as an absence.
9. **GitHub Releases upload of ~2 GB files may be slow/flaky** even when under the limit;
   the engine should use resumable download (`curl -C -`), verify size + SHA-256 before
   claiming success, and treat a failed `gh release upload` as retryable without creating a
   duplicate release.
