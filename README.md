# Claude Downloads Index

自动追踪 `downloads.claude.ai` 官方最新版本的静态索引页：**GitHub Pages 门户 + 官方源直链**。

- 门户：`docs/`（GitHub Pages）
- 索引：`docs/data/manifest.json`（机器可读）与 `docs/data/manifest.js`（页面直接加载）
- 更新：**GitHub Actions 每 6 小时自动同步**官方最新版本（`.github/workflows/sync.yml`）
- 下载：所有按钮直接指向 `downloads.claude.ai` 官方源，本站不托管安装包

> 非官方索引，与 Anthropic 无隶属关系。请优先从官方源下载。

## 当前内容

清单每次同步时从官方接口实时解析，覆盖：

| 产品 | 来源 | 条目 |
|---|---|---|
| Claude Desktop | `api.anthropic.com/api/desktop/...` | macOS ×3、Windows ×8、Linux ×2 |
| Claude Science | `downloads.claude.ai/claude-science/latest` | macOS ×2、Windows ×2、Linux ×1 |
| Claude Code | `downloads.claude.ai/claude-code-releases` | macOS ×2、Windows ×2、Linux ×4（含 musl） |

版本号随官方发布自动更新，无需人工修改页面。Claude Code 仍可使用官方安装脚本：

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

## 工作原理

定时任务执行：

```bash
python3 scripts/mirror.py sync --commit --push
```

`sync` 只做三件事：

1. 解析官方最新版本与各平台下载直链（含 Science/Code 的官方 SHA-256）。
2. 生成 `docs/data/manifest.json` / `manifest.js`，每条记录标记为 `mirrored: false`，`relay_url` 即官方直链。
3. 版本未变时不写文件、不提交；版本变化时才提交并推送，GitHub Pages 随后自动重建。

因此站点始终指向官方最新版本，也不会出现“按钮指向一个没上传的文件”的 404。

## 本地使用

依赖 Python 3.10+（仅标准库）。同步和校验都不需要 `gh`、`curl` 或登录：

```bash
python3 scripts/mirror.py sync --dry-run   # 只探测，打印将同步的内容
python3 scripts/mirror.py sync             # 更新 docs/data/manifest.*
python3 scripts/mirror.py verify           # 校验清单结构与直链
python3 -m unittest scripts.test_mirror    # 单元测试（无网络）
```

只同步某个产品：

```bash
python3 scripts/mirror.py sync --product code
```

`--commit` / `--push` 可将生成的清单提交并推送（CI 使用）。

## 首次部署

1. 在 GitHub 创建仓库，推送到 `main`。
2. 修改 `mirrorrc.json` 中的 `owner` / `repo`。
3. 开启 Pages：**Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: `main` / `docs`**。`docs/.nojekyll` 已就位。免费计划需要仓库为 **public**；站点地址为 `https://<owner>.github.io/<repo>/`。
4. 确认 **Settings → Actions → General → Workflow permissions** 为 **Read and write permissions**（定时任务要提交清单）。
5. 手动触发一次 **Actions → Sync official Claude releases → Run workflow**。

## 可选：镜像安装包到 GitHub Releases

仓库仍保留完整镜像能力（`publish`）。如果将来要把安装包托管到 GitHub Releases：

```bash
python3 scripts/mirror.py publish --dry-run
python3 scripts/mirror.py publish
```

它会下载新版本到 `.cache/downloads/`、校验大小与 SHA-256、创建 `desktop-v*` / `science-v*` / `code-v*` Release 并上传资产，同时生成镜像清单。注意：

- GitHub Release 单文件必须**严格小于 2 GiB**；超限条目会记为 `mirrored: false` 并生成 `docs/relay/<id>.html` 中转页。
- 需要 `gh` 已登录（`repo` 权限）与 `curl`。
- 镜像模式与自动同步模式共用同一个 manifest；再次运行 `sync` 会把清单切回官方直链模式。

## 目录结构

```text
mirrorrc.json              # owner/repo/branch + 官方接口 + 上传上限
.github/workflows/sync.yml # 每 6 小时自动同步官方最新版本
scripts/mirror.py          # sync / probe / publish / verify
scripts/test_mirror.py     # 标准库 unittest
docs/index.html            # 门户
docs/assets/               # 样式与前端逻辑
docs/data/manifest.*       # 自动生成的清单（json 为权威，js 供页面加载）
research/                  # 源站清单、约束与评估记录（不发布）
```

## 故障排查

| 现象 | 处理 |
|---|---|
| Actions 没有提交清单 | 检查 Workflow permissions 是否为 read/write；版本未变时本来就不会提交 |
| `claude.ai/api/...` 返回 403 “Just a moment...” | 不要用该域名；引擎使用 `api.anthropic.com/api/desktop/...` |
| Pages 404 | 确认 Settings → Pages 选择 `main` / `docs`，且 `docs/.nojekyll` 存在 |
| 页面显示“尚未找到清单” | `docs/data/manifest.js` 未生成或未提交；运行 `sync` 后重试 |
| 官方接口暂时不可用 | `sync` 会保留上一个可用产品的清单条目，并在日志里列出被跳过的条目 |

## 说明

- 本项目只索引官方下载地址，不修改、不重打包、不代理下载流量。
- 门户不加载任何外部字体、脚本或统计服务。
- 页面上的 SHA-256 来自官方清单（Claude Science / Claude Code）；Claude Desktop 官方未公开哈希，因此显示 `—`。
