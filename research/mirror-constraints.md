# Mirror constraints — GitHub Releases + GitHub Pages

Research deliverable for `claude-downloads-mirror`. Verified 2026-10-17 against
GitHub Docs, the GitHub REST API, `gh` 2.63.2 (2024-12-05), and live HTTP probes.
No remote state was modified. Empirical checks are labelled **[observed]**.

**Verdicts up front**

1. Both offline macOS DMGs fit the 2 GiB per-asset limit. The Intel DMG is the
   closer one: **69,230,946 B (66.0 MiB, 3.22 %) below** the cap. **But the real
   boundary risk is Windows:** `windows-x64-offline` is **over** the cap
   (2,220,697,207 B, relay-only), and `windows-arm64-offline` is only
   **5,033,881 B (4.80 MiB) below** it.
2. Pages publishing from `/docs` on `main` works and yields
   `https://aresbit.github.io/claude-downloads-mirror/`. Add `docs/.nojekyll`.
   `manifest.json` is CDN-cached for **600 s**; **query-string cache busting does
   not work** at the Pages CDN [observed].
3. `gh` 2.63.2 supports an idempotent sequence, but `--clobber` is **delete then
   upload**, not an atomic replace. A publish with 17 mirrored assets is nowhere
   near API limits.
4. Release download URLs **do support Range/resume** (`206`, `Accept-Ranges:
   bytes`); stable URLs re-redirect to a short-lived signed CDN URL.
5. Prior art is worth copying for fingerprinting, checksum manifests, and release
   notes; avoid its cron, Cloudflare/R2 coupling, and implicit version-skew tags.
6. The dangerous failures are: a too-large future artifact, a `--clobber` repair
   that deletes an asset and then fails, and a manifest published before assets
   are verified. Over-limit artifacts are **relay-only**, never split or failed.
   Fail-closed ordering and digest checks are the guardrails.

**Evidence status / explicitly unverified**

- **Verified (official docs):** 2 GiB per-file limit, 1000 assets, no total
  size/bandwidth cap, Pages publishing model/URL, Pages limits, `.nojekyll`,
  rate-limit thresholds, REST upload/duplicate-name rules, digest availability.
- **Verified (observed 2026-10-17):** release 302 host, Range/206/416,
  `curl -C -`, Pages `cache-control: max-age=600`, query strings not creating
  distinct cache objects for HTML, JSON MIME on Pages, `gh release view` exit
  code, `gh` digest-null behavior.
- **Unverified:** the exact API error payload for an oversize upload; the exact
  Content-Type Pages chooses for ambiguous extensions (`.dmg`, `.exe`, `.deb`);
  whether the query-string cache behavior measured on HTML applies identically to
  `data/manifest.json` (poll regardless); GitHub availability/throttling in
  mainland China (only prior-art claims, no measurement). None is on the critical
  path; each has a check described below.

---

## 1. GitHub Releases asset limits

### Exact limit

GitHub's documentation: *"Up to 1000 release assets may be associated with a
single release. Each file included in a release must be under 2 GiB. There is no
limit on the total size of a release, nor bandwidth usage."*
([About releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases))

The docs use variables whose definitions are authoritative:

- `max_file_size: '2 GiB'`
  ([data/variables/large_files.yml](https://github.com/github/docs/blob/main/data/variables/large_files.yml))
- `release_asset_limit: '1000'`
  ([data/variables/releases.yml](https://github.com/github/docs/blob/main/data/variables/releases.yml))

**2 GiB = 2 × 1024³ = 2,147,483,648 bytes** (not 2,000,000,000, not 2 GB
decimal). The per-file cap is the only hard size cap; total release size and
download bandwidth are explicitly uncapped. The brief's expected upload is
**~8.73 GB** across 17 mirrored assets (Desktop ~10.31 GB source minus the
2.22 GB relay-only asset, plus Science ~0.64 GB), so expect a long first upload
but no quota issue.

### Do the offline assets fit?

| Asset | Bytes | Headroom to 2,147,483,648 | % of cap | Action |
|---|---:|---:|---:|---|
| `macos-apple-silicon-offline` DMG | 2,000,405,037 | +147,078,611 B = **140.3 MiB** | 93.15 % | Mirror |
| `macos-intel-offline` DMG | 2,078,252,702 | +69,230,946 B = **66.0 MiB** | 96.78 % | Mirror; watch growth |
| `windows-arm64-offline` MSIX | 2,142,449,767 | **+5,033,881 B = 4.80 MiB** | 99.77 % | Mirror; **critical** growth watch |
| `windows-x64-offline` MSIX | 2,220,697,207 | **−73,213,559 B = −69.8 MiB** | 103.41 % | **Never upload**; relay-only per brief |

Both macOS offline DMGs are strictly below 2,147,483,648 bytes, so they can be
uploaded as release assets today. Risk margin:

- The ARM64 macOS offline DMG has ~6.8 % headroom.
- The Intel macOS offline DMG has only ~3.2 % headroom. A future build that grows
  by ~66 MiB crosses the limit.
- `windows-arm64-offline` has only **4.80 MiB** of headroom (0.23 %). Any upstream
  growth, or a different interpretation of "2 GiB", makes it relay-only.
- `windows-x64-offline` is over the limit by **69.8 MiB** and must be recorded
  with `"mirrored": false`, a `relay_url`, its true size, and no `sha256`;
  generate the relay page and never attempt the upload.
- Use the docs' wording, *"under 2 GiB"*, literally: use
  `size >= 2147483648` as the fail-closed condition, matching the brief's
  `max_asset_bytes`. (Community reports of the exact API rejection vary; do not
  rely on the boundary being inclusive.)
- The over-limit policy is explicit (user decision, 2026-10-17): **no splitting
  and no failure**. Over-limit artifacts are relay-only; the publish run must
  succeed while labeling them "中转下载 / 官方源".
- All other artifacts are 388 MB or smaller (the universal DMG is 388,258,098 B);
  size risk is concentrated in the four offline assets above.

The file-size limit applies to the asset bytes, not HTTP framing, so the
Content-Length of each DMG is the number in the table.

All four offline assets are served from the `/releases-offline/` prefix
(`releases-offline/darwin/{x64,arm64}/…`, `releases-offline/win32/{x64,arm64}/…`);
the online/universal variants use `/releases/`. The brief's relay pages must use
the exact `source_url` (including the `/releases-offline/` prefix).

### Source size / HEAD trap

Direct GCS release objects may return `x-goog-stored-content-length` and **no**
`Content-Length` (this is called out in the brief amendment). Resolve sizes with:

1. `x-goog-stored-content-length` if present, else
2. `curl -r 0-0 -D -` and parse `Content-Range: bytes 0-0/<total>`.

Never interpret a missing `Content-Length` as `0`, and never derive a size from a
truncated or partial download. The same applies to the manifest and relay checks.

### Source inventory constraints (brief amendment 1)

- **18 artifacts total: 13 Desktop + 5 Science.** Science includes
  `windows-arm64.exe` (154,804,896 B); the original "no arm64 Windows" note was
  wrong. Only `windows-x64-offline` is relay-only.
- **Science is verifiable upstream.** `https://downloads.claude.ai/claude-science/latest/manifest.json`
  publishes `version`, `sha8`, `buildDate`, `sha256` per executable, and
  `dmg_sha256` per DMG. Verify downloaded Science bytes against these values.
  Desktop has no published hash: record the locally computed SHA-256.
- **Pin Science downloads to a versioned path, not `latest`.**
  `/claude-science/0.1.63/...` prevents an alias flip between probe and download
  from mixing versions. The live inventory (`research/artifacts.md`) recorded
  desktop source objects as `max-age=3600, immutable` and Science aliases as
  `max-age=0`.
- **Content-Disposition names collide.** Source names include four
  `Claude Setup.exe`/`Claude.msix` variants and two debs; never derive the mirror
  asset name from the source header. Use the brief's friendly names, e.g.
  `Claude-Desktop-2.42304.0-Windows-x64-offline.msix` and
  `Claude-Desktop-2.42304.0-macOS-universal.dmg`.

### What happens on upload failure

- **Oversize (≥ 2 GiB):** the documented contract is the limit; the REST upload
  endpoint rejects an oversize request (GitHub does not document the exact error
  payload; **unverified**). `gh` 2.63.2 performs **no client-side size check** before uploading
  ([shared/upload.go](https://github.com/cli/cli/blob/v2.63.2/pkg/cmd/release/shared/upload.go#L149-L191)),
  so without a preflight guard you can spend bandwidth before learning the file
  is too large. The known oversize artifact is `windows-x64-offline`
  (2,220,697,207 B); it must be classified relay-only **before** any upload call.
- **Duplicate name:** the API returns `422` and refuses the upload until the old
  asset is deleted
  ([REST: Upload a release asset](https://docs.github.com/en/rest/releases/assets?apiVersion=2022-11-28)).
- **Network / 5xx:** `gh` retries up to 3 times (constant 200 ms backoff) on
  network errors and HTTP ≥ 500. Each retry re-opens the file and **restarts from
  byte 0**; there is no resumable upload at the API level
  ([shared/upload.go](https://github.com/cli/cli/blob/v2.63.2/pkg/cmd/release/shared/upload.go#L121-L147)).
- **`gh release create <tag> <files...>` failure:** without `--draft`, gh creates
  the release as a draft, uploads assets with 5 workers, then publishes; on
  failure it **deletes the draft release** (the git tag may remain)
  ([create.go](https://github.com/cli/cli/blob/v2.63.2/pkg/cmd/release/create/create.go#L462-L529)).
  With `--draft`, a failed run leaves the draft and already-uploaded assets in
  place, which is what you want for resumability.

### Preflight guard (exact)

Classify over-limit artifacts as relay-only **before** staging uploads; run this
guard only on files intended for upload (they all must be under the cap).

```bash
MAX=2147483648                      # 2 GiB
WARN=$((MAX - 128*1024*1024))       # warn when within 128 MiB of the cap

find "$DIST" -maxdepth 1 -type f -print0 |
while IFS= read -r -d '' f; do
  name=$(basename "$f")
  size=$(stat -c %s "$f")           # macOS: stat -f %z "$f"
  if (( size >= MAX )); then
    printf 'FATAL: %s is %d bytes (>= 2 GiB)\n' "$name" "$size" >&2
    exit 1
  fi
  if (( size >= WARN )); then
    printf 'WARN: %s is only %d bytes below the 2 GiB cap\n' \
      "$name" "$((MAX - size))" >&2
  fi
done
```

---

## 2. GitHub Pages

### Publishing source and URL

A repository named `claude-downloads-mirror` under a user account is a **project
site**, not a user site. Project sites are served at
`http(s)://<owner>.github.io/<repositoryname>`; user sites (repository named
`<owner>.github.io`) are served at the root
([What is GitHub Pages?](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages#types-of-github-pages-sites)).

For this project: **`https://aresbit.github.io/claude-downloads-mirror/`**.

Configuration: repository **Settings → Pages → Build and deployment → Source:
Deploy from a branch → branch `main` → folder `/docs` → Save**. Pushing to the
publishing branch triggers the build; a missing `/docs` folder causes a build
error
([Configuring a publishing source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)).
The docs also warn that commits pushed by a GitHub Actions workflow using
`GITHUB_TOKEN` do **not** trigger a Pages build — another reason to keep this a
manual, local publish rather than a workflow.

### `.nojekyll`

Add an empty `docs/.nojekyll`. GitHub's docs: *"If you publish your site from a
source branch, GitHub Pages will use Jekyll to build your site by default. ...
disable the Jekyll build process by creating an empty file called `.nojekyll` in
the root of your publishing source"*
([Creating a GitHub Pages site](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site)).
Without it, Jekyll ignores files/folders beginning with `_`, `.`, or `#`, and
runs Liquid over the tree. `data/` happens to survive, but `.nojekyll` makes the
static-site contract explicit and avoids surprises.

### Caching: `docs/data/manifest.json`

**[observed 2026-10-17]** Pages responses come from Fastly (`Via: 1.1 varnish`,
`X-Served-By: cache-hkg…`) with:

```
cache-control: max-age=600
expires: <date> (+600 s)
age: <n>
x-cache: HIT|MISS
```

This applies to HTML and static assets; `https://pages.github.com/versions.json`
was observed with `Content-Type: application/json; charset=utf-8` and
`Cache-Control: max-age=600`. Treat `data/manifest.json` as cached for **up to
10 minutes** at the CDN.

**Query-string cache busting does not work at the Pages CDN [observed for Pages
HTML].** Two requests to the same Pages file with different random query strings
(`?alpha…`, `?omega…`) returned the same origin `x-github-request-id`; the second
was `x-cache: HIT`. Conditional requests are supported (`If-None-Match` returned
`304`), but a client cannot force a new origin fetch when the edge object is
still fresh. Extrapolating this to `data/manifest.json` is **unverified** for that
exact path; poll regardless.

Recommendation:

- In `app.js`, fetch `data/manifest.json` with `{cache: 'no-store'}` and/or
  `?v=<generated_at>` to avoid a stale **browser** cache, but do not claim this
  bypasses the CDN. Plan for up to ~10 min of CDN staleness. The generated
  `data/manifest.js` is subject to the same Pages caching; a `?v=` on its
  `<script>` tag has the same limitation.
- Display `generated_at` in the UI so users can see the data's age.
- After a publish, **poll** until the served manifest contains the new
  release/tag (allow 15 min: Pages build + deploy + 600 s cache). Do not treat a
  successful `git push` as a successful publish.
- Pages deployment itself has a 10-minute timeout
  ([Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)).

### Relay pages on a static host

GitHub Pages is static hosting; it cannot emit an HTTP `301`/`302` for
`docs/relay/<id>.html`. An over-limit relay page must be a real HTML file that
redirects client-side — for example `<meta http-equiv="refresh" content="0; url=…">`
plus `location.replace(sourceUrl)` and a visible clickable fallback link. The
manifest's `relay_url` therefore points at an HTML page, not at a downloadable
asset. Do not plan on server-side redirect rules; Pages does not run Apache/nginx
configuration for you.

### MIME types

GitHub Pages derives Content-Type from the extension; *"GitHub Pages supports
more than 750 MIME types across thousands of file extensions. The list of
supported MIME types is generated from the mime-db project"*
([Creating a GitHub Pages site — MIME types](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site#mime-types-on-github-pages);
see also the [archived MIME-types article](https://docs.github.com/en/enterprise/2.13/user/articles/mime-types-on-github-pages)).
There is no per-file or per-repository override; changes go through mime-db.

mime-db entries ([jshttp/mime-db](https://github.com/jshttp/mime-db)):

| Extension | mime-db entry/entries | Kind | Notes |
|---|---|---|---|
| `.dmg` | `application/x-apple-diskimage`; also listed under `application/octet-stream` | binary | mime-db has two entries; **the type Pages actually returns is unverified**. Check with `curl -I` after deploy. |
| `.exe` | `application/x-msdownload`, `application/x-msdos-program`; also `application/octet-stream` | binary | ambiguous in mime-db; **Pages' choice is unverified**; do not depend on a specific value. |
| `.msix` | `application/msix` | binary | unambiguous in mime-db; **Pages behavior still unverified**. |
| `.deb` | `application/x-debian-package`; also `application/octet-stream` | binary | ambiguous in mime-db; **Pages' choice is unverified**. |
| `.AppImage` | none in mime-db | binary | falls back to `application/octet-stream` (expected; **unverified**). |
| `.json` | `application/json` | text | observed on Pages: `application/json; charset=utf-8`. |

**Important:** in this design the installers are **not served by Pages**. GitHub
Releases serves them as `Content-Type: application/octet-stream` with
`Content-Disposition: attachment; filename=...` regardless of the stored
`content_type` metadata [observed]. Browsers download because of the attachment
disposition, not because of a precise MIME type. Pages is only HTML/CSS/JS/JSON.

### Pages limits (relevant because installers must not live here)

- Published site ≤ **1 GB**; source repository recommended ≤ 1 GB.
- Soft bandwidth limit **100 GB/month**; soft limit **10 builds/hour**.
- Deployment timeout **10 minutes**; rate limiting may return `429`.
  ([Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits))

The installers (several GB) belong in Releases, not in `docs/` or Git history.
Git's own 100 MiB file / 2 GiB push limits are separate from the release-asset
limit and are easy to confuse.

---

## 3. `gh` 2.63.2 idempotent publishing

Installed version in this workspace: `gh version 2.63.2 (2024-12-05)`, logged in
as `aresbit` with `repo` scope (verified).

### Command semantics

| Command | Behavior | Idempotency |
|---|---|---|
| `gh release view TAG --repo R` | Read release; exit **1** with `release not found` if absent [observed] | Safe probe |
| `gh release create TAG ...` | Create release; if assets given and not `--draft`, draft-upload-publish; error if a published release with that tag exists | Guard with `gh release view` |
| `gh release upload TAG FILE...` | Upload; errors if an asset with the same (sanitized) name exists | Upload only missing assets |
| `gh release upload TAG FILE --clobber` | **DELETE existing asset, then upload** ([source](https://github.com/cli/cli/blob/v2.63.2/pkg/cmd/release/shared/upload.go#L133-L147)) | Not atomic; repair only |
| `gh release edit TAG --draft=false` | Publish a draft (documented example) | Use after verifying assets |
| `gh release edit TAG --latest=false` | Do not mark this release as repo "Latest" | **Required for two product lines** |

`gh` uploads up to **5 assets concurrently** (hard-coded) and retries network/5xx
failures 3 times, restarting the whole file each time. It has no per-upload
resume and no client-side 2 GiB check.

### Asset naming rules

GitHub: *"GitHub renames asset filenames that have special characters,
non-alphanumeric characters, and leading or trailing periods. The 'List release
assets' endpoint lists the renamed filenames."*
([REST: Upload a release asset](https://docs.github.com/en/rest/releases/assets?apiVersion=2022-11-28))

`gh` 2.63.2 replicates that transform client-side so `--clobber` can find the
renamed asset
([upload.go#L128-L153](https://github.com/cli/cli/blob/v2.63.2/pkg/cmd/release/upload/upload.go#L128-L153)):
diacritics removed; every character outside `[A-Za-z0-9._+@-]` replaced with
`.`; runs of dots collapsed; leading/trailing dots trimmed; a name that would
start with `.` is prefixed with `default`; if sanitization leaves a bare token
with no dot (an "extension-only" name), it is prefixed with `default.`.

Practical rules:

- Spaces become dots (`Claude Desktop.dmg` → `Claude.Desktop.dmg`).
- Parentheses, `~`, `:`, unicode, etc. become dots.
- Avoid `#`: gh treats `file#label` as a display-label syntax.
- Use only `[A-Za-z0-9._+@-]`, start with an alphanumeric, and keep basenames
  unique. The brief's proposed names (`Claude-Desktop-2.42304.0-macOS-universal.dmg`,
  etc.) are safe.
- **Read the asset names back from the API after upload** and use those exact
  names in `manifest.json`; never assume the local basename survived.

### Rate limits for the 17 mirrored-asset publish

- Primary: **5,000 requests/hour** for an authenticated user
  ([rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)).
- Secondary: no more than **80 content-generating requests/minute**, **500/hour**;
  most `POST/PATCH/PUT/DELETE` cost **5 points**; no more than **900 points/minute
  per endpoint**; no more than **100 concurrent** requests.

A full publish of both products is **17 mirrored assets** (12 Desktop + 5
Science), plus 2 creates and 2 edits and a handful of GETs: ~21
content-generating requests, ~105 points, and at most 5 concurrent uploads (gh's
internal limit). The 18th artifact, `windows-x64-offline`, is relay-only and is
not uploaded. This is far below every published threshold. Rate limits are not
the risk; network timeouts and multi-GB re-transfers are.

### Minimal idempotent sequence

```bash
set -euo pipefail
REPO="aresbit/claude-downloads-mirror"
TAG="desktop-v2.42304.0"
DIST="dist/$TAG"          # mirrored assets only; never place relay-only files here
NOTES="dist/RELEASE_NOTES.md"

# 0) preflight
gh auth status >/dev/null
[[ $(gh api rate_limit --jq '.resources.core.remaining') -gt 50 ]]

# 1) refuse to run on an oversize/unsafe set (see guard in section 1)
#    also assert every filename matches ^[A-Za-z0-9][A-Za-z0-9._+@-]*$

# 2) create a DRAFT release if it does not exist (no assets yet)
if ! gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
  gh release create "$TAG" --repo "$REPO" --target main --draft \
    --title "Claude Desktop 2.42304.0" \
    --notes-file "$NOTES"
fi

# 3) upload only missing assets, one at a time (no --clobber)
existing=$(gh release view "$TAG" --repo "$REPO" --json assets --jq '.assets[].name')
find "$DIST" -maxdepth 1 -type f -print0 |
while IFS= read -r -d '' f; do
  name=$(basename "$f")
  if grep -Fxq "$name" <<<"$existing"; then
    echo "skip existing: $name"
  else
    gh release upload "$TAG" "$f" --repo "$REPO"
  fi
done

# 4) verify the full remote set (names, sizes, server digests) before publishing
release_id=$(gh api "repos/$REPO/releases/tags/$TAG" --jq '.id')
gh api --paginate "repos/$REPO/releases/$release_id/assets?per_page=100" \
  --jq '.[] | [.name, (.size|tostring), (.digest // "")] | @tsv' > /tmp/remote.tsv

while IFS=$'\t' read -r name size digest; do
  local="$DIST/$name"
  [[ -f "$local" ]] || { echo "FATAL: remote-only asset $name"; exit 1; }
  [[ $(stat -c %s "$local") == "$size" ]] || { echo "FATAL: size $name"; exit 1; }
  if [[ -n "$digest" ]]; then
    want="sha256:$(sha256sum "$local" | awk '{print $1}')"
    [[ "$digest" == "$want" ]] || { echo "FATAL: digest $name"; exit 1; }
  fi
done < /tmp/remote.tsv

# every local file must also be present remotely (catches a skipped/failed upload)
comm -23 \
  <(find "$DIST" -maxdepth 1 -type f -printf '%f\n' | LC_ALL=C sort) \
  <(cut -f1 /tmp/remote.tsv | LC_ALL=C sort) |
while IFS= read -r missing; do
  [[ -z "$missing" ]] || { echo "FATAL: missing remote asset $missing"; exit 1; }
done

# 5) publish the draft, not marked as repo "Latest"
if [[ $(gh release view "$TAG" --repo "$REPO" --json isDraft --jq .isDraft) == true ]]; then
  gh release edit "$TAG" --repo "$REPO" --draft=false --latest=false
fi

# 6) prove each stable URL exists and supports Range
while IFS= read -r name; do
  url="https://github.com/$REPO/releases/download/$TAG/$name"
  code=$(curl -fsSL --retry 3 --retry-all-errors -r 0-0 \
    -o /dev/null -w '%{http_code}' "$url")
  [[ "$code" == 206 ]] || { echo "FATAL: $url -> $code"; exit 1; }
done < <(gh api --paginate "repos/$REPO/releases/$release_id/assets?per_page=100" \
  --jq '.[].name')
```

Why the draft path: gh's `release create TAG file1 file2 ...` is shorter, but on
any upload failure it deletes the draft release and all uploaded assets. For two
~2 GB DMGs, the explicit draft makes a failed run resumable.

**Digests:** GitHub has exposed immutable `assets[].digest` (`sha256:…`) since
2025-06-03 ([changelog](https://github.blog/changelog/2025-06-03-releases-now-expose-digests-for-release-assets/)).
Assets uploaded before that feature can have `digest: null`. `gh` 2.63.2 predates
the feature: `gh release view --json assets` returned `digest: null` in testing,
so read the REST endpoint (`gh api .../releases/<id>/assets`) instead.

---

## 4. Release download URLs, Range/resume, and China notes

### Redirect and Range

**[observed 2026-10-17]** A request to
`https://github.com/cli/cli/releases/download/v2.63.2/gh_2.63.2_linux_amd64.tar.gz`
(and to a prior-art `.dmg`) returned:

```
HTTP/2 302
location: https://release-assets.githubusercontent.com/github-production-release-asset/<id>/<uuid>?...
```

The signed URL is Azure Blob storage behind Fastly (`server: Windows-Azure-Blob`,
`via: 1.1 varnish`) and returns:

```
HTTP/2 200
content-type: application/octet-stream
content-disposition: attachment; filename=...
content-length: 388258098
accept-ranges: bytes
```

Range tests:

- `Range: bytes=0-15` → **206**, exactly 16 bytes.
- Unsatisfiable range (`bytes=99999999999-`) → **416**.
- `curl -C -` (resume) against the stable URL completed a 13 MB file correctly;
  the resume request returned **206** and fetched only the missing bytes.

The signed URL expires quickly (**~30–60 minutes** in observed tokens:
`se=`/JWT `exp`). The stable
`https://github.com/<owner>/<repo>/releases/download/<tag>/<asset>` URL is
re-redirected on every request, so it is safe for `curl -C -` across long
downloads and is the only URL that belongs in `manifest.json`.

Recommended client command (document in README/portal):

```bash
curl -fL --retry 5 --retry-delay 2 --retry-all-errors \
  -C - -o Claude-Desktop.dmg \
  "https://github.com/aresbit/claude-downloads-mirror/releases/download/desktop-v2.42304.0/Claude-Desktop-2.42304.0-macOS-universal.dmg"
```

Then verify `sha256sum` against the manifest. `-C -` is essential for the ~2 GB
offline DMGs; a single dropped connection otherwise restarts the download.

### Rate limiting

GitHub's release docs say there is **no limit on bandwidth usage** for releases,
and release downloads are served by the CDN, not `api.github.com`; no
`x-ratelimit-*` headers appear on asset responses [observed]. There is no
documented per-download rate limit for public release assets. Do not promise
throughput, but there is no policy cap to design around. Pages is different:
100 GB/month soft bandwidth ([Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)).

### Chinese users

- Prior art (Wangnov's mirror) states that the official update API and
  `downloads.claude.ai` are "frequently blocked or throttled" in mainland China,
  and it maintains Cloudflare R2 short links specifically for that audience
  ([README](https://github.com/Wangnov/claude-app-mirror#readme-cn)).
  That is a prior-art claim, not an official measurement; this mission
  deliberately does not include R2.
- GitHub web/Releases and Pages used different hosts/CDNs in observations:
  `github.com` (302), `release-assets.githubusercontent.com` (Azure Blob behind
  Fastly), and `*.github.io` (Fastly). A network that reaches `github.com` but
  not the asset host can still fail. State the host separation in the runbook;
  do not claim GitHub is blocked or unblocked in any specific region.
- Keep the portal useful on a bad link: show exact sizes and SHA-256, provide the
  `curl -C -` command, and link to the stable release URL (not a short link).
  Avoid recommending third-party download proxies; they add a supply-chain trust
  problem.

---

## 5. Prior art: `Wangnov/claude-app-mirror` and `agents-mirror-kit`

Inspected 2026-10-17: workflow, probe/download/metadata scripts, pitfalls doc,
download-router worker README, and live releases.

### Patterns worth copying

1. **Fingerprint, don't poll by version string alone.** `probe-release.sh` follows
   `/api/desktop/<platform>/<arch>/<format>/latest/redirect`, parses the version
   from the redirect path and the build hash from the filename, then HEADs the
   artifact for `Content-Length`, `ETag`, and `Last-Modified`
   ([probe-release.sh](https://github.com/Wangnov/claude-app-mirror/blob/main/scripts/probe-release.sh)).
   It compares a stable subset (`url` + `length` per platform) with the previous
   release's `release-manifest.json` and skips when unchanged
   ([#L137-L147](https://github.com/Wangnov/claude-app-mirror/blob/main/scripts/probe-release.sh#L137-L147),
   [#L198-L214](https://github.com/Wangnov/claude-app-mirror/blob/main/scripts/probe-release.sh#L198-L214)).
   Copy this for `probe`/`--dry-run` and for "nothing changed" detection.
2. **Downgrade guard.** It refuses to publish a probed version older than the
   latest release (`version_gt`, [#L208-L211](https://github.com/Wangnov/claude-app-mirror/blob/main/scripts/probe-release.sh#L208-L211)).
   Copy this; also make `--force` explicit.
3. **Predicted-tag existence check.** It skips when the predicted tag already
   exists ([#L216-L222](https://github.com/Wangnov/claude-app-mirror/blob/main/scripts/probe-release.sh#L216-L222)).
   Our version uses `gh release view` before create.
4. **Checksum manifest + machine-readable manifest as release assets.**
   `prepare-release-metadata.sh` computes SHA-256 for every artifact, writes
   `SHA256SUMS.txt`, augments `release-manifest.json` with `sha256` and
   `assetName`, and attaches both to the release
   ([#L53-L101](https://github.com/Wangnov/claude-app-mirror/blob/main/scripts/prepare-release-metadata.sh#L53-L101)).
   Copy this: it gives offline users a second, version-pinned verification path
   independent of the Pages manifest.
5. **Per-platform version display in release notes.** The bilingual notes list
   each platform's version separately
   ([#L119-L125](https://github.com/Wangnov/claude-app-mirror/blob/main/scripts/prepare-release-metadata.sh#L119-L125)).
   Copy the idea; it makes skew visible instead of hiding it behind one version.
6. **Concurrency guard.** The workflow uses a fixed `concurrency` group
   ([mirror.yml#L25-L27](https://github.com/Wangnov/claude-app-mirror/blob/main/.github/workflows/mirror.yml#L25-L27)).
   Our manual CLI should take a local `flock` so two terminals cannot publish at
   once.
7. **Fixed, sanitized asset names.** Live assets are
   `Claude-mac-universal.dmg`, `Claude-win-x64.msix`, etc., with no spaces
   ([release v2.42304.0](https://github.com/Wangnov/claude-app-mirror/releases/tag/claude-app-v2.42304.0)).
   Copy the convention; it avoids GitHub's renaming and keeps manifest URLs
   stable.
8. **Live release shape.** Each release carries installers plus
   `SHA256SUMS.txt` and `release-manifest.json`; the manifest is
   `application/json` and the API exposes digests
   (observed on the live release API).

### Pitfalls to avoid

1. **Scheduled auto-updates.** The workflow has a 6-hour `schedule`
   ([mirror.yml#L15-L16](https://github.com/Wangnov/claude-app-mirror/blob/main/.github/workflows/mirror.yml#L15-L16)),
   and the team's own pitfalls doc says GitHub `schedule` is often delayed or
   skipped, so they added a Cloudflare Cron dispatcher
   ([pitfalls.md#L33-L37](https://github.com/Wangnov/agents-mirror-kit/blob/main/docs/pitfalls.md#L33-L37)).
   Our mission is manual; adding cron recreates a known-unreliable dependency.
2. **R2/Cloudflare coupling.** Prior art mirrors a second copy to R2 and routes
   CN traffic through a Worker with SigV4 presigned URLs and analytics
   ([mirror.yml#L128-L189](https://github.com/Wangnov/claude-app-mirror/blob/main/.github/workflows/mirror.yml#L128-L189),
   [download-router README](https://github.com/Wangnov/agents-mirror-kit/blob/main/workers/download-router/README.md)).
   That needs Cloudflare account secrets, a custom domain, a Worker, and a second
   storage system. It also brought operational problems: R2 uploads hanging, a
   ~32-day analytics retention window, and a data endpoint swallowed by a
   static-site SPA fallback
   ([pitfalls.md#L7-L20](https://github.com/Wangnov/agents-mirror-kit/blob/main/docs/pitfalls.md#L7-L20),
   [#L39-L43](https://github.com/Wangnov/agents-mirror-kit/blob/main/docs/pitfalls.md#L39-L43)).
   Out of scope and a large increase in failure surface.
3. **Implicit tag selection when platform versions diverge.** The probe warns
   when platform versions differ but still tags by the macOS version
   ([#L166-L169](https://github.com/Wangnov/claude-app-mirror/blob/main/scripts/probe-release.sh#L166-L169));
   a live release with a manual suffix exists,
   [`claude-app-v2.9939.4-linux`](https://github.com/Wangnov/claude-app-mirror/releases/tag/claude-app-v2.9939.4-linux).
   The pitfalls doc records the underlying problem: one platform ships, the other
   has not, and the release stalls
   ([#L29-L31](https://github.com/Wangnov/agents-mirror-kit/blob/main/docs/pitfalls.md#L29-L31)).
   Decide explicitly: fail closed on skew, or use a release-train tag and record
   per-artifact versions. Never label artifacts with a version they do not have.
4. **Non-resumable downloads.** `download-artifacts.sh` uses `curl -fL -o` with
   retries but no `-C -`
   ([#L63-L74](https://github.com/Wangnov/claude-app-mirror/blob/main/scripts/download-artifacts.sh#L63-L74)).
   That is acceptable for a 388 MB universal DMG; it is fragile for the two ~2 GB
   offline DMGs. Add `-C -` and keep partial files between runs.
5. **Size-only validation.** It checks downloaded `Content-Length` but does not
   verify an upstream checksum
   ([#L51-L61](https://github.com/Wangnov/claude-app-mirror/blob/main/scripts/download-artifacts.sh#L51-L61)).
   Copy the size check, and add SHA-256 (always) plus `x-goog-hash` MD5/CRC32C
   when the source provides it.
6. **"Latest" links in release notes.** They embed R2 `latest/*` links with
   markers, then a separate step strips them from the previous release's notes
   ([mirror.yml#L110-L117](https://github.com/Wangnov/claude-app-mirror/blob/main/.github/workflows/mirror.yml#L110-L117)).
   If we avoid "latest" links in notes and let the portal be the only
   latest-pointer, we avoid this cleanup job and stale links.
7. **JSON embedded into a workflow heredoc.** The workflow interpolates the
   probe manifest into a shell heredoc
   ([#L69-L75](https://github.com/Wangnov/claude-app-mirror/blob/main/.github/workflows/mirror.yml#L69-L75)).
   Our manual Python CLI writes files directly; do not reintroduce string
   interpolation of machine data into shell/YAML.
8. **Only a subset of extensions in checksums.** Their checksum `find` covers
   `*.dmg`, `*.msix`, `*.deb` but not `*.exe` or `*.AppImage`
   ([#L96-L101](https://github.com/Wangnov/claude-app-mirror/blob/main/scripts/prepare-release-metadata.sh#L96-L101)).
   Our mirror includes `.exe`/`.msix` variants; checksum **all** published assets,
   not a hard-coded extension list.
9. **No offline 2 GB assets.** Prior art mirrors the universal DMG only, so it
   never tested the 2 GiB boundary. Our mirror is the first to carry the offline
   DMGs; do not infer safety from their success.

---

## 6. Failure modes and guardrails

| Failure | Symptom | Guardrail |
|---|---|---|
| Asset ≥ 2 GiB | Upload fails; possibly after transferring the whole body | Preflight `size < 2147483648`; warn within 128 MiB. Mark over-limit artifacts relay-only (`mirrored:false`, `download_url:null`, `relay_url`, true size, no `sha256`) and never upload. **Known:** `windows-x64-offline` (over by 69.8 MiB); `windows-arm64-offline` has only 4.80 MiB headroom. |
| Duplicate asset name | `422`; `gh` errors unless `--clobber` | Safe, unique names; skip existing assets; use `--clobber` only for a verified repair. |
| Network drop mid-upload | `gh` retries 3× from byte 0, then exits non-zero | Keep local files; rerun only missing assets; verify the remote set afterward. |
| `--clobber` repair fails | Old asset was already deleted; new one never appears | Do not clobber multi-GB assets routinely. If repair is unavoidable, verify the local file, upload under the same name, and re-verify digest; accept a short 404 window. |
| Partial release (crash/kill) | Some assets present, release draft | Draft-first workflow; resume uploads; verify count/names/sizes/digests; publish only when complete. |
| Manifest points at a missing asset | Portal 404 / Range check fails | Ordering: release → verify → manifest → verify Pages. Validate every `mirrored:true` `download_url` with `Range: 0-0` (expect 206) and compare the true size. Do not fetch `mirrored:false` entries. |
| Relay entry malformed | Broken redirect page, invented hash, or download URL | For `mirrored:false`: require `download_url == null`, no `sha256`, a real `size >= 2 GiB`, a source URL under `downloads.claude.ai`, and an existing `docs/relay/<id>.html` whose redirect target matches `source_url`. |
| HEAD omits `Content-Length` | Size parsed as 0 or missing | Use `x-goog-stored-content-length` or `Range: 0-0` + `Content-Range`; never treat missing as 0. |
| Desktop platform version skew | Tag says one version; artifact says another | Probe all 13 variants; assert equality by default; otherwise fail closed or use an explicit train tag + per-artifact `source_version`. |
| Science version changes independently | Desktop and science tags diverge | Separate `science-v*` namespace and release; update only the science product entry in the manifest; never rewrite the desktop entry. Detect via `Content-Disposition` on the **five** fixed aliases and verify against the official Science manifest. |
| Science alias flip mid-publish | Mixed 0.1.63 / 0.1.64 artifacts in one release | Probe and download from versioned `/claude-science/<version>/...` paths; re-check the official manifest version before hashing. |
| Science checksum mismatch | Downloaded bytes differ from official `sha256`/`dmg_sha256` | Fail the publish; do not upload, do not update the manifest. |
| Content-Disposition name collision | Four `Claude Setup.exe`/`Claude.msix` and two debs map to the same name | Use the brief's friendly mirror names; never derive the release asset name from the source header. |
| GitHub outage / 502 / TLS reset | API or asset host errors (observed during this research) | Retry with backoff; honor `Retry-After`; keep artifacts locally; do not push the manifest until every asset is verified. |
| Rate limit | `403`/`429` with `x-ratelimit-remaining: 0` or secondary-limit text | 5,000/h primary is ample; spread uploads; wait per headers. A full publish is 17 mirrored uploads ≈ 21 content-generating requests. |
| Source flakiness | `api.anthropic.com` 502/`SSL_ERROR_SYSCALL`; GCS timeouts (observed) | `curl --retry … --retry-all-errors`; resume with `-C -`; verify size and `x-goog-hash`/official SHA-256 before upload. |
| Source ETag misused as checksum | Composite GCS objects have opaque ETags (observed `-CJL+2vHqupcDEAE=`), not MD5 | Treat ETag as an opaque change fingerprint. Use `x-goog-hash` MD5/CRC32C when present; always compute SHA-256 after download. |
| Build filename hash misused as SHA | `Claude-e7f60….dmg` is a build identifier, identical across architectures | Never call it SHA-256 or publish it as a checksum; compute SHA-256 locally. |
| Pages stale after push | Old manifest for up to 10 min + build time | Poll until the new tag appears; show `generated_at`; do not rely on `?v=` to bypass the CDN. |
| Pages build missing `/docs` | Page build error | Keep `docs/index.html`, `docs/.nojekyll`, `docs/data/manifest.json`, and `docs/data/manifest.js` on `main`; never remove `/docs`. |
| Manifest files drift | `manifest.js` serves a different payload than `manifest.json` | Generate both from the same in-memory payload in one write step; verify equality (after stripping the JS wrapper) before commit. |
| Concurrent manual publishes | Race between two terminals | `flock -n` a lock file; require a clean git tree and expected branch before the manifest commit. |
| Repo "Latest" flaps | `/releases/latest` points at desktop, then science | Pass `--latest=false` on both product releases; the portal is the source of truth. |

### Additional publication invariants

1. **Never publish `manifest.json` first.** The release must exist, be published
   (not draft), and pass URL/size/digest checks before the manifest commit.
2. **Generate the manifest from remote observed state.** Read names, sizes, and
   digests from the release API after upload; merge with locally computed SHA-256.
   This absorbs GitHub's filename sanitization and catches missing assets.
3. **Keep artifacts immutable per tag.** If upstream bytes change under the same
   version, publish a new tag or an explicit force tag; do not silently clobber
   the historical release.
4. **Merge, don't regenerate, when publishing one product.** Load the existing
   manifest, update only the changed product, and verify the other product's
   entry is unchanged.
5. **Debounce/de-duplicate.** A re-run with identical fingerprints should print
   "no changes" and touch nothing remote.
6. **Keep a local publish log** (tag, asset names, sizes, SHA-256, timestamps,
   Pages verification result). Do not put it in the published site.
7. **Treat mirroring as a decision, not an assumption.** Every artifact carries
   `mirrored: true|false`. `true` requires an uploaded asset + verified digest;
   `false` requires a genuine over-limit size, no hash, and a relay page. Never
   upload a `mirrored:false` artifact and never invent a hash for it.
8. **Science hashes are upstream-authoritative.** Verify `dmg_sha256` for the two
   DMGs and `sha256` for the EXE/Linux binaries before upload. Desktop hashes are
   locally computed and recorded.
9. **`manifest.json` and `manifest.js` are one payload.** Write both in the same
   step; `manifest.js` is `window.MIRROR_MANIFEST = <same JSON>;`. Verify equality
   before commit.
10. **Push is explicit.** A publish run may commit locally with `--commit`, but
    must not push unless `--push` is passed. Treat the push/Pages update as a
    separate, visible action.
11. **`--dry-run` is truly read-only.** It may perform version GETs and HEAD/Range
    probes, but zero downloads, zero remote mutations, and unchanged manifest
    bytes. A second dry-run reports "no changes".

---

## Recommended publish sequence

```bash
#!/usr/bin/env bash
# Manual only: python3 scripts/mirror.py publish (or the equivalent CLI)
set -euo pipefail

REPO="aresbit/claude-downloads-mirror"
BRANCH="main"
DIST="dist"                    # mirrored files only; relay-only artifacts never enter here
TAG="desktop-v2.42304.0"      # repeat the sequence for each changed product tag
MAX=2147483648
PUSH="${PUSH:-0}"             # require an explicit --push / PUSH=1

# --- publish lock ---------------------------------------------------------
exec 9>"$HOME/.cache/claude-mirror-publish.lock"
flock -n 9 || { echo "another publish is running" >&2; exit 1; }

# --- preflight ------------------------------------------------------------
gh auth status >/dev/null
[[ $(gh api rate_limit --jq '.resources.core.remaining') -gt 50 ]]
[[ $(git rev-parse --abbrev-ref HEAD) == "$BRANCH" ]]
[[ -z $(git status --porcelain) ]] || { echo "dirty worktree" >&2; exit 1; }

# 1. probe, download, verify locally (per product)
#    Desktop: GET api.anthropic.com/api/desktop/<platform>/<arch>/<variant>/latest
#    Science: GET claude-science/latest/manifest.json, then download from the
#             versioned /claude-science/<version>/... path (never `latest`) and
#             verify dmg_sha256 / sha256 from the official manifest.
#    curl -fL --retry 5 --retry-delay 2 --retry-all-errors -C - -o <file> <url>
#    Resolve size via x-goog-stored-content-length or Range 0-0 + Content-Range;
#    verify x-goog-hash when present, then sha256sum.
#    Desktop artifacts >= 2 GiB are relay-only: do not download them.

# 2. preflight every file: size, safe unique name, sha256
#    (see section 1 guard)

# 3. for each product with changes: tag = desktop-v<version> | science-v<version>
#    create draft if absent, upload missing assets sequentially, verify REST
#    names/sizes/digests, then publish with --draft=false --latest=false
#    (see section 3 sequence). Relay-only artifacts are never uploaded.

# 4. verify every stable download URL (Range 0-0 => 206) and true size

# 5. regenerate/merge docs/data/manifest.json + docs/data/manifest.js from
#    verified remote state; both must come from the same in-memory payload

# 6. validate the manifest itself before committing
python3 - <<'PY'
import json, os, re, subprocess

m = json.load(open("docs/data/manifest.json"))
assert m["schema_version"] == 1
assert len(m["products"]) >= 1

for p in m["products"]:
    for a in p["artifacts"]:
        assert a["size"] > 0, (a["file"], a["size"])
        if a.get("mirrored"):
            assert a["size"] < 2147483648, (a["file"], a["size"])
            assert re.fullmatch(r"[0-9a-f]{64}", a["sha256"]), a["file"]
            url = a["download_url"]
            pat = r"^https://github\.com/[^/]+/[^/]+/releases/download/[^/]+/[^/]+$"
            assert re.match(pat, url), url

            hdr = "/tmp/range-headers.txt"
            code = subprocess.check_output([
                "curl", "-fsSL", "--retry", "3", "--retry-all-errors",
                "-r", "0-0", "-D", hdr, "-o", "/dev/null",
                "-w", "%{http_code}", url
            ], text=True)
            assert code == "206", (url, code)
            headers = open(hdr, encoding="utf-8").read()
            hm = re.search(r"(?im)^content-range:\s*bytes\s+0-0/(\d+)", headers)
            assert hm and int(hm.group(1)) == a["size"], (url, hm and hm.group(1))
        else:
            assert a["size"] >= 2147483648, (a["file"], a["size"])
            assert a.get("download_url") is None, a["file"]
            assert "sha256" not in a or a["sha256"] is None, a["file"]
            relay = os.path.join("docs", a["relay_url"])
            assert os.path.isfile(relay), relay
            assert a["source_url"].startswith("https://downloads.claude.ai/"), a["file"]
            assert a["source_url"] in open(relay, encoding="utf-8").read(), relay

# manifest.js must embed exactly the same payload
js = open("docs/data/manifest.js", encoding="utf-8").read().strip()
prefix = "window.MIRROR_MANIFEST = "
assert js.startswith(prefix) and js.endswith(";"), "manifest.js wrapper"
assert json.loads(js[len(prefix):-1]) == m, "manifest.js drift"
print("manifest OK")
PY

# 7. commit both manifest files; push only when explicitly requested
git add docs/data/manifest.json docs/data/manifest.js
if ! git diff --cached --quiet; then
  git commit -m "publish: <products and versions>"
  if [[ "$PUSH" == 1 ]]; then
    git push origin "$BRANCH"       # this triggers the Pages build
  else
    echo "committed locally; re-run with --push to update Pages"
    exit 0
  fi
fi

# 8. poll Pages until the new tag is actually served
for i in $(seq 1 30); do
  body=$(curl -fsS "https://aresbit.github.io/claude-downloads-mirror/data/manifest.json" || true)
  if jq -e --arg t "$TAG" 'any(.products[]; .tag == $t)' <<<"$body" >/dev/null 2>&1; then
    echo "Pages is serving the new manifest"
    exit 0
  fi
  sleep 30
done
echo "Pages did not update within 15 minutes" >&2
exit 1
```

For a re-run after a crash: steps 1–2 are cheap; step 3 skips existing assets and
resumes the draft; steps 5–8 are idempotent. If the release is already published
and complete, the whole run is a no-op except for the manifest merge.

---

## Do-not-do list

- **Do not put installers in the repo or `docs/`.** Git's 100 MiB file limit and
  Pages' 1 GB site / 100 GB/month limits are the wrong budget. Use Releases
  (2 GiB per file, no total/bandwidth cap).
- **Do not upload any file ≥ 2,147,483,648 bytes.** Preflight. `windows-x64-offline`
  (2,220,697,207 B) is **over** the cap and must be relay-only; the Intel macOS
  DMG has 66 MiB of headroom and `windows-arm64-offline` only **4.80 MiB**.
  `gh` 2.63.2 will not stop you client-side.
- **Do not split an over-limit artifact and do not fail the publish because of it.**
  The user decision is relay-only: `mirrored:false`, `download_url:null`, true
  size, `relay_url`, no `sha256`, generated relay page.
- **Do not invent a hash or download URL for a relay-only artifact.** There is no
  downloaded byte to hash; the manifest must say so honestly.
- **Do not derive asset names from `Content-Disposition`.** Four Windows variants
  and two debs share generic names; use the brief's friendly mirror names.
- **Do not treat a missing `Content-Length` as zero.** Use
  `x-goog-stored-content-length` or `Range: 0-0` + `Content-Range`.
- **Do not run `gh release upload --clobber` routinely.** It deletes the old asset
  before uploading; a failed upload leaves the release broken. Reserve it for a
  verified repair of a small asset, and never for a multi-GB asset without
  accepting a 404 window.
- **Do not publish `manifest.json` before the release is published and verified.**
  Release → verify URLs/sizes/digests → manifest → verify Pages.
- **Do not write signed `release-assets.githubusercontent.com` URLs into the
  manifest.** They expire in ~30–60 minutes. Use the stable
  `github.com/.../releases/download/...` URL.
- **Do not use spaces, unicode, `#`, or arbitrary punctuation in asset names.**
  GitHub rewrites them (spaces become dots); the manifest URL will not match.
- **Do not trust `gh release view --json assets` for digests in gh 2.63.2**
  (returns null); use `gh api .../releases/<id>/assets`.
- **Do not mark product releases as "Latest."** Two independent product lines
  fight over one repo-level Latest. Use `--latest=false`; the portal is the source
  of truth.
- **Do not add GitHub Actions cron or a Cloudflare Cron dispatcher.** Manual
  publish is the requirement; `schedule` is unreliable (prior-art evidence).
- **Do not add R2, Workers, custom domains, or R2 short links.** They require extra
  secrets and introduce a second storage path, CN-specific routing, upload
  timeouts, and stale-link cleanup.
- **Do not rely on query strings to bust the Pages CDN.** Observed: different
  query strings hit the same Fastly object; `max-age=600`. Poll after publishing.
- **Do not treat the build hash in the source filename as SHA-256.** It is a
  build identifier shared across architectures; compute SHA-256 after download.
- **Do not treat a composite GCS ETag as an MD5.** Use `x-goog-hash` when present;
  otherwise use the ETag only as an opaque change signal.
- **Do not resume a download and trust its size alone.** Compute SHA-256 and
  compare with the recorded/expected value; a resumed partial can have the right
  final size only if the byte ranges were correct.
- **Do not download Science from the `latest` aliases.** Probe with them, then
  download from `/claude-science/<version>/...` and verify `dmg_sha256`/`sha256`
  against the official Science manifest.
- **Do not let `manifest.js` drift from `manifest.json`.** Emit both from one
  payload in one atomic write; verify equality before commit.
- **Do not push implicitly during publish.** Commit locally if requested; update
  Pages only with an explicit `--push`.
- **Do not expect an HTTP redirect from a relay page.** GitHub Pages is static;
  use `<meta http-equiv="refresh">` / `location.replace()` plus a visible link to
  `source_url`.
- **Do not validate relay-only artifacts like mirrored ones.** They have no
  `download_url`/`sha256`; validate their size, source URL, and relay page
  instead, and exclude them from Range checks.
- **Do not silently publish a skewed version set.** Fail closed (default) or use
  an explicit release-train tag with per-artifact source versions.
- **Do not mirror the Windows online bootstrapper as if it were offline.** Label
  it as an online installer; the self-contained MSIX/offline variants are the
  useful offline downloads.
- **Do not let two publish processes run.** Use `flock` and a clean-tree check.
- **Do not assume a successful `git push` means the Pages site is live.** Poll the
  served manifest and check `generated_at`.
- **Do not use `.AppImage` on Pages expecting a precise MIME type.** It is unmapped
  in mime-db (octet-stream); Pages has no per-file override. Releases serve all
  installers as `application/octet-stream` anyway.

---

## Source index

- Releases limits: https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
  and https://github.com/github/docs/blob/main/data/variables/large_files.yml
- REST release assets: https://docs.github.com/en/rest/releases/assets
- Rate limits: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- Release download URLs: https://docs.github.com/en/repositories/releasing-projects-on-github/linking-to-releases
- Asset digests: https://github.blog/changelog/2025-06-03-releases-now-expose-digests-for-release-assets/
- Pages publishing: https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
- Pages site types / URL: https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages
- Pages `.nojekyll` and MIME: https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site
- Pages limits: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- MIME database: https://github.com/jshttp/mime-db
- gh 2.63.2 source: https://github.com/cli/cli/tree/v2.63.2/pkg/cmd/release
- gh manual: https://cli.github.com/manual/gh_release_create ,
  https://cli.github.com/manual/gh_release_upload ,
  https://cli.github.com/manual/gh_release_view ,
  https://cli.github.com/manual/gh_release_edit
- Prior art: https://github.com/Wangnov/claude-app-mirror ,
  https://github.com/Wangnov/agents-mirror-kit ,
  https://github.com/Wangnov/agents-mirror-kit/blob/main/docs/pitfalls.md
- Science official manifest:
  https://downloads.claude.ai/claude-science/latest/manifest.json
- Internal contract and inventory: `research/brief.md` (including amendment 1,
  2026-10-17) and `research/artifacts.md` (live 18-artifact inventory).
