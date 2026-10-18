# Claude Downloads Mirror

`downloads.claude.ai` 的手动维护镜像：**GitHub Pages 静态门户 + GitHub Releases 安装包托管**。

- 门户：`docs/`（GitHub Pages）
- 安装包：每个产品版本一个 GitHub Release（`desktop-v<版本>`、`science-v<版本>`、`code-v<版本>`）
- 索引：`docs/data/manifest.json`（机器可读）与 `docs/data/manifest.js`（页面直接加载）
- 更新：**手动执行发布脚本**，没有 cron、没有自动更新

> 非官方镜像，与 Anthropic 无隶属关系。请优先从官方源下载。

> **首次发布前**：仓库里的 `docs/data/manifest.json` 是带 `"sample": true` 的布局样例。运行一次 `publish` 后会被真实清单替换。

## 当前内容

| 产品 | 版本 | 安装包 |
|---|---|---|
| Claude Desktop | `2.42304.0` | macOS ×3、Windows ×8、Linux ×2 |
| Claude Science | `0.1.63` | macOS ×2、Windows ×2、Linux ×1 |
| Claude Code | `2.1.302` | macOS ×2、Windows ×2、Linux ×4（含 musl） |

合计 26 个条目：25 个镜像包 + 1 个官方源中转（`windows-x64-offline` 超过 GitHub 单文件 2 GiB 上限）。

Claude Code 条目是各平台的原生二进制（含 Linux musl 变体）；官方安装脚本仍可使用 `curl -fsSL https://claude.ai/install.sh | bash`。

## 依赖

- Python **3.10+**（脚本只用标准库）
- `git`、`curl`
- [`gh`](https://cli.github.com/) 并已登录（`gh auth login`，需要 `repo` 权限）

## 首次部署

1. 在 GitHub 创建仓库（例如 `claude-downloads-mirror`），推送到 `main`。
2. 修改 `mirrorrc.json`：

   ```json
   {
     "owner": "你的GitHub用户名",
     "repo": "claude-downloads-mirror",
     "branch": "main",
     "site_dir": "docs"
   }
   ```

3. 开启 Pages：仓库 **Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: `main` / `docs`**。`docs/.nojekyll` 已就位。免费计划的 GitHub Pages 需要仓库为 **public**；站点地址为 `https://<owner>.github.io/<repo>/`。
4. 先探测、再演练，最后发布：

   ```bash
   python3 scripts/mirror.py probe --table
   python3 scripts/mirror.py publish --dry-run
   python3 scripts/mirror.py publish
   ```

   `publish` 会下载新版本安装包到 `.cache/downloads/`、校验大小与 SHA-256、创建/复用 GitHub Release、上传资产与 `SHA256SUMS.txt`，并重新生成 manifest。首次发布会下载约 **11 GB**，请预留磁盘与时间。

5. 提交并推送生成的清单：

   ```bash
   git add docs/data docs/relay
   git commit -m "Publish Claude Desktop 2.42304.0 / Claude Science 0.1.63 / Claude Code 2.1.302"
   git push
   ```

6. 打开 `https://<owner>.github.io/<repo>/`。

## 日常更新（手动）

官方发布新版本后：

```bash
python3 scripts/mirror.py probe --table          # 看看当前版本
python3 scripts/mirror.py publish --dry-run      # 打印将执行的操作，不下载、不上传
python3 scripts/mirror.py publish                # 下载 → 校验 → 发布 → 生成清单
git add docs/data docs/relay && git commit -m "Update Claude installers" && git push
```

`publish` 是幂等的：版本未变时不会重复创建 Release 或重复上传；已有 Release 缺资产时只补传缺失项。

发布顺序是“先 Release、后清单”：只有资产上传并校验完成后才会写 `docs/data/manifest.json`，避免页面指向不存在的文件。两个产品线都不会被标记为仓库级 “Latest”（`gh release create --latest=false`）。

发布后 GitHub Pages 通常需要 **10–15 分钟**生效：`manifest.json` 在 Pages CDN 缓存约 600 秒，查询参数不能绕过缓存。可轮询确认：

```bash
curl -fsS https://<owner>.github.io/<repo>/data/manifest.json \
  | jq -r '.products[] | "\(.id) \(.version) \(.tag)"'
```

GitHub Release 的稳定下载 URL 支持 HTTP Range/断点续传；重定向后的签名 CDN 地址会过期，因此 manifest 永远只写 `github.com/.../releases/download/...`。

常用参数：

```bash
--product desktop|science|code   # 只处理某个产品
--exclude id,id            # 跳过指定 artifact
--force                    # 版本未变也重新上传（仅此时使用 --clobber）
--commit                   # 发布后本地提交 manifest 与 relay 页
--push                     # 提交并推送（隐含 --commit）
--dry-run                  # 只读探测 + 打印计划，不下载、不上传、不写文件
```

## 2 GiB 规则与中转

GitHub Release 单文件要求 **严格小于 2 GiB（2,147,483,648 B）**。

- 超限文件**不会上传、不会分卷**，而是记录为 `mirrored: false`，并生成
  `docs/relay/<artifact-id>.html` 中转页，自动跳转到官方源，同时保留可见的兜底链接。
- 当前唯一超限项：`windows-x64-offline`（2,220,697,207 B）。
- `windows-arm64-offline`（2,142,449,767 B）仍在限制内，但余量只有约 5 MB；未来若超限会自动转为中转。
- `python3 scripts/mirror.py verify` 会拒绝任何“标记为已镜像却 ≥ 2 GiB”的条目。

## 校验

```bash
python3 scripts/mirror.py verify
python3 scripts/mirror.py verify --allow-sample   # 首次发布前检查示例清单结构
```

`verify` 默认拒绝带 `"sample": true` 的示例清单，防止把假哈希部署上线；`--allow-sample` 只做结构检查，不可用于发布验收。

每个 Release 附带 `SHA256SUMS.txt`。门户上每个已镜像文件也显示 SHA-256 与一键复制。下载后本地校验：

```bash
sha256sum <文件名>            # Linux
shasum -a 256 <文件名>        # macOS
Get-FileHash .\<文件名> -Algorithm SHA256   # Windows PowerShell
```

Claude Science 的哈希来自官方 `claude-science/latest/manifest.json`（DMG 用 `dmg_sha256`，EXE/Linux 用 `sha256`）。Claude Code 的哈希来自官方 `claude-code-releases/<版本>/manifest.json`。Claude Desktop 没有公开哈希，引擎在下载后计算并记录 SHA-256。

## 目录结构

```text
mirrorrc.json              # owner/repo/branch + 源站接口 + 上传上限
scripts/mirror.py          # probe / publish / verify
scripts/test_mirror.py     # 标准库 unittest
docs/index.html            # 门户
docs/assets/               # 样式与前端逻辑
docs/data/manifest.*       # 生成的清单（json 为权威，js 供页面加载）
docs/relay/                # 超限资产的官方源中转页
research/                  # 源站清单、约束与评估记录（不发布）
```

## 故障排查

| 现象 | 处理 |
|---|---|
| `claude.ai/api/...` 返回 403 “Just a moment...” | 不要用该域名；引擎使用 `api.anthropic.com/api/desktop/...` |
| 下载出现 `CONNECT tunnel failed, response 502` | 代理瞬断；重新执行，下载会断点续传（`curl -C -`） |
| `HEAD` 没有 `Content-Length` | 引擎回退到 `x-goog-stored-content-length` 或 `Range: bytes=0-0` |
| `gh release upload` 很慢或中断 | 重新执行 `publish`；已存在资产会跳过，必要时加 `--force`（`--clobber`） |
| Pages 404 | 确认 Settings → Pages 选择 `main` / `docs`，且 `docs/.nojekyll` 存在 |
| 页面显示“尚未找到清单” | 尚未运行 `publish`，或 `docs/data/manifest.js` 未提交/推送 |
| 2 GiB 报错 | 该资产应自动转为 relay；若 `verify` 报错，检查 manifest 的 `mirrored` 字段 |

## 说明

- 本项目只索引与镜像安装包，不修改、不重打包、不代理下载流量。
- 门户不加载任何外部字体、脚本或统计服务。
- 更新完全由维护者手动触发；版本可能略晚于官方。
