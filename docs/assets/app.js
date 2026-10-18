(function () {
  'use strict';

  var SVG_NS = 'http://www.w3.org/2000/svg';

  var I18N = {
    zh: {
      pageTitle: 'Claude 下载镜像 · Claude Desktop 与 Claude Science',
      skipLink: '跳到主要内容',
      brand: 'Claude 下载镜像',
      brandTag: '手动维护',
      navLabel: '页面导航',
      navOverview: '概览',
      navDesktop: 'Claude Desktop',
      navScience: 'Claude Science',
      navVerify: '校验与说明',
      langLabel: '切换语言',
      themeToDark: '切换到深色模式',
      themeToLight: '切换到浅色模式',
      heroEyebrow: '社区镜像 · 手动维护',
      heroTitle: 'Claude 桌面端下载镜像',
      heroLead: 'downloads.claude.ai 的手动维护镜像。安装包托管在 GitHub Releases，本页只提供索引、文件大小与 SHA-256 校验值，不代理下载流量。',
      lastUpdated: '清单更新时间',
      officialSource: '官方下载源',
      previewTitle: '本地预览 · 示例数据',
      previewBody: '当前清单仅用于布局验证，下载链接与校验值并非线上文件。',
      previewTitlePlaceholder: '示例数据 / 尚未发布',
      previewBodyPlaceholder: '清单中的 SHA-256 仍是占位值。维护者完成首次发布后，这里会显示真实的校验值。',
      previewBodySample: '当前清单标记为示例数据，尚未发布。下载与校验信息仅用于布局预览；维护者完成首次真实发布后，此提示会消失。',
      overviewTitle: '概览',
      statDesktop: 'Claude Desktop 最新版本',
      statScience: 'Claude Science 最新版本',
      statSize: '镜像总大小',
      statArtifacts: '镜像包总数',
      statDesktopMeta: '{n} 个镜像包',
      statScienceMeta: '{n} 个镜像包',
      statSizeMeta: '全部已镜像安装包',
      statArtifactsMeta: '{n} 个产品',
      statSizeBreakdown: '{n} 个镜像包 · {r} 个官方源中转',
      statSizeSimple: '{n} 个镜像包',
      statCountBreakdown: '另有 {n} 个官方源中转 · {p} 个产品',
      relayCountShort: '{n} 个官方源中转',
      notInManifest: '当前清单未包含',
      desktopKicker: '桌面客户端',
      desktopDesc: '官方桌面客户端，覆盖 macOS、Windows 与 Linux，含在线安装器、完整安装包与离线安装包。',
      scienceKicker: '科学桌面应用',
      scienceDesc: 'Claude Science 桌面应用，覆盖 macOS、Windows 与 Linux。',
      viewRelease: '查看 GitHub Release',
      releasedAt: '发布于 {date}',
      download: '下载',
      downloadAria: '下载 {file}',
      missingLink: '链接缺失',
      source: '源站',
      sourceAria: '打开 {file} 的官方源站链接',
      fileHeader: '文件',
      sizeHeader: '大小',
      hashHeader: 'SHA-256',
      downloadHeader: '下载',
      copy: '复制',
      copyAria: '复制 {file} 的 SHA-256',
      copyToast: 'SHA-256 已复制',
      copied: '已复制',
      copyFailed: '复制失败，请手动选择哈希',
      manifestMissingTitle: '尚未找到清单',
      manifestMissingBody: '页面未加载 data/manifest.js，也没有可用的 data/manifest.json。维护者运行 python3 scripts/mirror.py publish 生成清单后，刷新此页即可。',
      manifestInvalidTitle: '清单无法读取',
      manifestInvalidBody: '已加载的清单不是有效的 schema v1 数据。请重新运行发布脚本生成清单。',
      productMissingTitle: '清单未包含此产品',
      productMissingBody: '当前清单中没有该产品的条目，因此不显示下载链接。',
      noArtifacts: '此产品暂时没有可用安装包。',
      noArtifactsBody: '请等待维护者发布该产品的安装包后再试。',
      filesCount: '{n} 个文件',
      unknownOS: '其他平台',
      unknownArtifact: '未命名文件',
      variantInstaller: '安装包',
      variantOffline: '离线安装包',
      variantSetup: '在线安装器',
      variantExe: 'EXE 安装包',
      variantMsix: 'MSIX 安装包',
      variantDeb: 'DEB 安装包',
      variantOnline: '在线安装器',
      offlineFlag: '离线安装包 · ~{size}',
      relayBadge: '未镜像 · 超过 2 GiB',
      relayDownload: '中转下载（官方源）',
      relayAria: '通过官方源中转下载 {file}',
      relayMissing: '中转链接缺失',
      relayNoHash: '未镜像 · 无镜像校验值',
      linuxBinaryLabel: 'Linux x64 · 命令行/二进制',
      verifyTitle: '校验下载',
      verifyLead: '每个镜像文件都提供 SHA-256。下载完成后先核对哈希，确认文件完整再安装；官方源中转条目由源站提供校验信息。',
      verifyQuick: '快速校验',
      verifyWin: 'Windows PowerShell',
      verifyMacCmd: 'shasum -a 256 <文件名>',
      verifyLinuxCmd: 'sha256sum <文件名>',
      verifyWinCmd: 'Get-FileHash .\\<文件名> -Algorithm SHA256',
      aboutTitle: '关于这个镜像',
      about1: '清单由维护者手动运行发布脚本生成，不设自动更新，版本可能略晚于官方。',
      about2: '下载链接指向 GitHub Releases 中的固定版本资产，不经过第三方代理。',
      about3: 'GitHub 单文件上限为 2 GiB。超过上限的安装包不镜像，改为链接官方源中转；接近上限的文件会在发布前按大小与 SHA-256 严格校验。',
      footerLinks: '相关链接',
      footerDisclaimer: '非官方镜像，与 Anthropic 无隶属关系。请优先从官方源下载。',
      footerRepo: 'GitHub 仓库',
      footerSource: '官方下载源'
    },
    en: {
      pageTitle: 'Claude Downloads Mirror · Claude Desktop & Claude Science',
      skipLink: 'Skip to main content',
      brand: 'Claude Downloads Mirror',
      brandTag: 'Manual mirror',
      navLabel: 'Page navigation',
      navOverview: 'Overview',
      navDesktop: 'Claude Desktop',
      navScience: 'Claude Science',
      navVerify: 'Verify & notes',
      langLabel: 'Language',
      themeToDark: 'Switch to dark mode',
      themeToLight: 'Switch to light mode',
      heroEyebrow: 'COMMUNITY MIRROR · MANUALLY MAINTAINED',
      heroTitle: 'Claude desktop downloads mirror',
      heroLead: 'A manually maintained mirror of downloads.claude.ai. Installers live in GitHub Releases; this page only provides the index, file sizes and SHA-256 checksums, and does not proxy download traffic.',
      lastUpdated: 'Manifest updated',
      officialSource: 'Official source',
      previewTitle: 'Local preview · sample data',
      previewBody: 'This manifest is a layout fixture. Download links and checksums do not refer to published files.',
      previewTitlePlaceholder: 'Sample data / not yet published',
      previewBodyPlaceholder: 'The manifest still contains placeholder SHA-256 values. Real checksums appear after the maintainer completes the first publish.',
      previewBodySample: 'This manifest is marked as a sample and has not been published. Downloads and checksums are for layout preview only; this notice disappears after the first real publish.',
      overviewTitle: 'Overview',
      statDesktop: 'Latest Claude Desktop',
      statScience: 'Latest Claude Science',
      statSize: 'Total mirrored size',
      statArtifacts: 'Mirrored packages',
      statDesktopMeta: '{n} mirrored packages',
      statScienceMeta: '{n} mirrored packages',
      statSizeMeta: 'All mirrored installers',
      statArtifactsMeta: '{n} products',
      statSizeBreakdown: '{n} mirrored packages · {r} relay-only',
      statSizeSimple: '{n} mirrored packages',
      statCountBreakdown: 'Plus {n} relay-only · {p} products',
      relayCountShort: '{n} relay-only',
      notInManifest: 'Not in current manifest',
      desktopKicker: 'Desktop client',
      desktopDesc: 'The official desktop client for macOS, Windows and Linux, including online installers, full packages and offline installers.',
      scienceKicker: 'Science desktop app',
      scienceDesc: 'Claude Science desktop app for macOS, Windows and Linux.',
      viewRelease: 'View GitHub Release',
      releasedAt: 'Released {date}',
      download: 'Download',
      downloadAria: 'Download {file}',
      missingLink: 'Link missing',
      source: 'Source',
      sourceAria: 'Open the official source link for {file}',
      fileHeader: 'File',
      sizeHeader: 'Size',
      hashHeader: 'SHA-256',
      downloadHeader: 'Download',
      copy: 'Copy',
      copyAria: 'Copy SHA-256 for {file}',
      copyToast: 'SHA-256 copied',
      copied: 'Copied',
      copyFailed: 'Copy failed. Select the hash manually.',
      manifestMissingTitle: 'Manifest not found',
      manifestMissingBody: 'The page could not load data/manifest.js or data/manifest.json. Run python3 scripts/mirror.py publish, then refresh.',
      manifestInvalidTitle: 'Manifest unreadable',
      manifestInvalidBody: 'The loaded manifest is not valid schema v1 data. Regenerate it with the publish script.',
      productMissingTitle: 'Product missing from manifest',
      productMissingBody: 'This manifest has no entry for the product, so no download links are shown.',
      noArtifacts: 'No installers are available for this product yet.',
      noArtifactsBody: 'Wait for the maintainer to publish installers for this product.',
      filesCount: '{n} files',
      unknownOS: 'Other platform',
      unknownArtifact: 'Unnamed file',
      variantInstaller: 'Installer',
      variantOffline: 'Offline installer',
      variantSetup: 'Online installer',
      variantExe: 'EXE installer',
      variantMsix: 'MSIX package',
      variantDeb: 'DEB package',
      variantOnline: 'Online installer',
      offlineFlag: 'Offline installer · ~{size}',
      relayBadge: 'Not mirrored · over 2 GiB',
      relayDownload: 'Relay download (official source)',
      relayAria: 'Download {file} via the official source relay',
      relayMissing: 'Relay link missing',
      relayNoHash: 'Not mirrored · no mirror checksum',
      linuxBinaryLabel: 'Linux x64 · CLI/binary',
      verifyTitle: 'Verify downloads',
      verifyLead: 'Every mirrored file includes a SHA-256. Check the hash after downloading and before installing; relay-only entries rely on the official source for verification.',
      verifyQuick: 'Quick check',
      verifyWin: 'Windows PowerShell',
      verifyMacCmd: 'shasum -a 256 <file>',
      verifyLinuxCmd: 'sha256sum <file>',
      verifyWinCmd: 'Get-FileHash .\\<file> -Algorithm SHA256',
      aboutTitle: 'About this mirror',
      about1: 'The manifest is produced manually by the maintainer; there is no automatic update, so versions may lag behind the official source.',
      about2: 'Download links point to fixed-version assets in GitHub Releases and are not proxied by a third party.',
      about3: 'GitHub limits each asset to under 2 GiB. Oversized installers are not mirrored; they link to the official source via a relay, while near-limit files are validated before publishing.',
      footerLinks: 'Related links',
      footerDisclaimer: 'Unofficial mirror, not affiliated with Anthropic. Prefer downloading from the official source.',
      footerRepo: 'GitHub repository',
      footerSource: 'Official source'
    }
  };

  var state = {
    lang: 'zh',
    manifest: null,
    renderedOnce: false
  };

  var toastTimer = null;

  function $(selector) {
    return document.querySelector(selector);
  }

  function $all(selector) {
    return Array.prototype.slice.call(document.querySelectorAll(selector));
  }

  function t(key, vars) {
    var dict = I18N[state.lang] || I18N.zh;
    var value = dict[key];
    if (value === undefined) value = I18N.zh[key];
    if (value === undefined) value = key;
    if (!vars) return value;
    return value.replace(/\{(\w+)\}/g, function (match, name) {
      return vars[name] === undefined ? match : String(vars[name]);
    });
  }

  function readText(value) {
    return typeof value === 'string' ? value.trim() : '';
  }

  function isObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
  }

  function locale() {
    return state.lang === 'zh' ? 'zh-CN' : 'en-US';
  }

  function el(tag, className) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    return node;
  }

  function icon(id, extraClass) {
    var svg = document.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('class', 'icon' + (extraClass ? ' ' + extraClass : ''));
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    var use = document.createElementNS(SVG_NS, 'use');
    use.setAttribute('href', '#' + id);
    svg.appendChild(use);
    return svg;
  }

  function safeHttpsUrl(value) {
    if (typeof value !== 'string') return null;
    try {
      var url = new URL(value, document.baseURI);
      return url.protocol === 'https:' ? url.href : null;
    } catch (error) {
      return null;
    }
  }

  function isMirroredArtifact(artifact) {
    return !(isObject(artifact) && artifact.mirrored === false);
  }

  function isStandaloneBinary(artifact) {
    var file = readText(artifact.file);
    if (!file || /\.[A-Za-z0-9]+$/.test(file)) return false;
    return readText(artifact.os).toLowerCase() === 'linux' &&
      readText(artifact.arch).toLowerCase() === 'x64';
  }

  function safeRelayUrl(value) {
    var raw = readText(value);
    if (!raw) return null;
    if (/^[a-z][a-z0-9+.-]*:/i.test(raw) || raw.slice(0, 2) === '//') return null;
    try {
      var url = new URL(raw, document.baseURI);
      if (url.protocol === 'https:' || url.protocol === 'http:' || url.protocol === 'file:') {
        return raw;
      }
    } catch (error) {
      return null;
    }
    return null;
  }

  function formatBytes(bytes) {
    var value = Number(bytes);
    if (!isFinite(value) || value < 0) return '';
    if (value < 1000) return String(Math.round(value)) + ' B';
    var units = ['KB', 'MB', 'GB', 'TB'];
    var index = -1;
    do {
      value = value / 1000;
      index += 1;
    } while (value >= 1000 && index < units.length - 1);
    var digits = value >= 100 ? 0 : 1;
    return value.toFixed(digits) + ' ' + units[index];
  }

  function exactBytes(bytes) {
    var value = Number(bytes);
    if (!isFinite(value) || value < 0) return '';
    return new Intl.NumberFormat(locale()).format(value) + ' B';
  }

  function formatDate(iso) {
    if (!iso) return '';
    var date = new Date(iso);
    if (isNaN(date.getTime())) return '';
    try {
      return new Intl.DateTimeFormat(locale(), {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short'
      }).format(date);
    } catch (error) {
      return date.toISOString();
    }
  }

  function setTime(node, iso) {
    var text = formatDate(iso);
    if (!text) {
      node.textContent = '—';
      node.removeAttribute('datetime');
      node.removeAttribute('title');
      return false;
    }
    node.textContent = text;
    node.dateTime = iso;
    node.title = iso;
    return true;
  }

  function localizeVariant(value) {
    var raw = readText(value);
    if (!raw) return '';
    var normalized = raw.toLowerCase();
    if (normalized.indexOf('offline') !== -1) return t('variantOffline');
    if (normalized.indexOf('online') !== -1) return t('variantOnline');
    if (normalized.indexOf('setup') !== -1) return t('variantSetup');
    if (normalized.indexOf('msix') !== -1) return t('variantMsix');
    if (normalized.indexOf('deb') !== -1) return t('variantDeb');
    if (normalized.indexOf('exe') !== -1) return t('variantExe');
    if (normalized.indexOf('install') !== -1) return t('variantInstaller');
    return raw;
  }

  function isOffline(artifact) {
    var probe = readText(artifact.variant) + ' ' + readText(artifact.id) + ' ' + readText(artifact.file);
    return /offline/i.test(probe);
  }

  function osIconId(osName) {
    var name = osName.toLowerCase();
    if (name.indexOf('mac') !== -1) return 'icon-laptop';
    if (name.indexOf('win') !== -1) return 'icon-windows';
    if (name.indexOf('linux') !== -1) return 'icon-terminal';
    return 'icon-folder';
  }

  function osRank(osName) {
    var name = osName.toLowerCase();
    if (name.indexOf('mac') !== -1) return 0;
    if (name.indexOf('win') !== -1) return 1;
    if (name.indexOf('linux') !== -1) return 2;
    return 3;
  }

  function updateLanguageButtons() {
    $all('[data-lang-btn]').forEach(function (button) {
      button.setAttribute('aria-pressed', String(button.dataset.langBtn === state.lang));
    });
  }

  function updateThemeUI() {
    var isDark = document.documentElement.classList.contains('dark');
    var toggle = $('#theme-toggle');
    if (toggle) {
      toggle.setAttribute('aria-pressed', String(isDark));
      toggle.setAttribute('aria-label', t(isDark ? 'themeToLight' : 'themeToDark'));
    }
    var meta = $('#theme-color');
    if (meta) meta.setAttribute('content', isDark ? '#0f0f0e' : '#f5f5f3');
  }

  function applyStaticLanguage() {
    document.documentElement.lang = state.lang === 'zh' ? 'zh-CN' : 'en';
    document.documentElement.dataset.lang = state.lang;
    document.title = t('pageTitle');
    $all('[data-i18n]').forEach(function (node) {
      node.textContent = t(node.dataset.i18n);
    });
    $all('[data-i18n-aria]').forEach(function (node) {
      node.setAttribute('aria-label', t(node.dataset.i18nAria));
    });
    updateLanguageButtons();
    updateThemeUI();
    if (state.manifest) renderManifest(state.manifest);
  }

  function showToast(message) {
    var toast = $('#toast');
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('is-visible');
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(function () {
      toast.classList.remove('is-visible');
    }, 2200);
  }

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text).then(function () {
        return true;
      }).catch(function () {
        return legacyCopy(text);
      });
    }
    return Promise.resolve(legacyCopy(text));
  }

  function legacyCopy(text) {
    try {
      var area = document.createElement('textarea');
      area.value = text;
      area.setAttribute('readonly', '');
      area.style.position = 'fixed';
      area.style.top = '-1000px';
      area.style.opacity = '0';
      document.body.appendChild(area);
      area.select();
      var ok = document.execCommand('copy');
      document.body.removeChild(area);
      return ok;
    } catch (error) {
      return false;
    }
  }

  function handleCopy(button, hash, file) {
    copyText(hash).then(function (ok) {
      var label = button.querySelector('span');
      window.clearTimeout(button._resetTimer);
      if (!ok) {
        showToast(t('copyFailed'));
        return;
      }
      button.dataset.copied = 'true';
      if (label) label.textContent = t('copied');
      showToast(t('copyToast'));
      button._resetTimer = window.setTimeout(function () {
        delete button.dataset.copied;
        if (label) label.textContent = t('copy');
        button.setAttribute('aria-label', t('copyAria', { file: file }));
      }, 2200);
    });
  }

  function createBadge(text, className) {
    var badge = el('span', 'badge' + (className ? ' ' + className : ''));
    badge.textContent = text;
    return badge;
  }

  function createArtifactRow(artifact, index, animate) {
    var row = el('li', 'artifact-row');
    if (animate) {
      row.classList.add('is-entering');
      row.style.setProperty('--i', String(Math.min(index, 9)));
    }

    var file = readText(artifact.file) || readText(artifact.id) || t('unknownArtifact');
    var arch = readText(artifact.arch);
    var variant = readText(artifact.variant);
    var offline = isOffline(artifact);
    var mirrored = isMirroredArtifact(artifact);
    var binary = isStandaloneBinary(artifact);
    if (!mirrored) row.classList.add('artifact-row-relay');
    var size = Number(artifact.size);
    var hasSize = isFinite(size) && size >= 0;

    var idCell = el('div', 'artifact-id');
    var fileName = el('span', 'artifact-file t-code');
    fileName.textContent = file;
    fileName.lang = 'en';
    idCell.appendChild(fileName);

    var badges = el('div', 'badges');
    if (!mirrored) {
      if (arch) badges.appendChild(createBadge(arch));
      badges.appendChild(createBadge(t('relayBadge'), 'badge-warn'));
    } else if (binary) {
      badges.appendChild(createBadge(t('linuxBinaryLabel'), 'badge-accent'));
    } else {
      if (arch) badges.appendChild(createBadge(arch));
      if (offline) {
        var flag = hasSize ? t('offlineFlag', { size: formatBytes(size) }) : t('variantOffline');
        badges.appendChild(createBadge(flag, 'badge-warn'));
      } else if (variant) {
        badges.appendChild(createBadge(localizeVariant(variant)));
      }
    }
    if (badges.childElementCount) idCell.appendChild(badges);

    var sizeCell = el('div', 'artifact-size');
    sizeCell.setAttribute('role', 'group');
    sizeCell.setAttribute('aria-label', t('sizeHeader'));
    if (hasSize) {
      var sizeValue = el('span', 'size-value');
      sizeValue.textContent = formatBytes(size);
      var sizeExact = el('span', 'size-bytes');
      sizeExact.textContent = exactBytes(size);
      sizeCell.appendChild(sizeValue);
      sizeCell.appendChild(sizeExact);
    } else {
      var unknownSize = el('span', 'size-value');
      unknownSize.textContent = '—';
      sizeCell.appendChild(unknownSize);
    }

    var source = safeHttpsUrl(artifact.source_url);
    if (source) {
      var sourceLink = el('a', 'source-link');
      sourceLink.href = source;
      sourceLink.target = '_blank';
      sourceLink.rel = 'noopener noreferrer';
      sourceLink.setAttribute('aria-label', t('sourceAria', { file: file }));
      sourceLink.appendChild(icon('icon-external'));
      var sourceText = el('span');
      sourceText.textContent = t('source');
      sourceLink.appendChild(sourceText);
      sizeCell.appendChild(sourceLink);
    }

    var hashCell = el('div', 'artifact-hash');
    hashCell.setAttribute('role', 'group');
    if (mirrored) {
      hashCell.setAttribute('aria-label', t('hashHeader'));
      var hash = readText(artifact.sha256);
      var hashCode = el('code', 'hash t-code');
      hashCode.textContent = hash || '—';
      if (hash) hashCode.title = hash;
      hashCell.appendChild(hashCode);

      var copyButton = el('button', 'copy-btn');
      copyButton.type = 'button';
      copyButton.setAttribute('aria-label', t('copyAria', { file: file }));
      copyButton.appendChild(icon('icon-copy'));
      copyButton.appendChild(icon('icon-check'));
      var copyLabel = el('span');
      copyLabel.textContent = t('copy');
      copyButton.appendChild(copyLabel);
      if (hash) {
        copyButton.addEventListener('click', function () {
          handleCopy(copyButton, hash, file);
        });
      } else {
        copyButton.disabled = true;
      }
      hashCell.appendChild(copyButton);
    } else {
      hashCell.setAttribute('aria-label', t('relayNoHash'));
      var relayNote = el('span', 'relay-note');
      relayNote.textContent = t('relayNoHash');
      hashCell.appendChild(relayNote);
    }

    var actionCell = el('div', 'artifact-action');
    if (!mirrored) {
      var relay = safeRelayUrl(artifact.relay_url);
      if (relay) {
        var relayLink = el('a', 'btn btn-relay relay-btn');
        relayLink.href = relay;
        relayLink.target = '_blank';
        relayLink.rel = 'noopener noreferrer';
        relayLink.setAttribute('aria-label', t('relayAria', { file: file }));
        relayLink.appendChild(icon('icon-external'));
        var relayLabel = el('span');
        relayLabel.textContent = t('relayDownload');
        relayLink.appendChild(relayLabel);
        actionCell.appendChild(relayLink);
      } else {
        var relayMissing = el('span', 'btn btn-relay relay-btn is-disabled');
        relayMissing.setAttribute('aria-disabled', 'true');
        relayMissing.textContent = t('relayMissing');
        actionCell.appendChild(relayMissing);
      }
    } else {
      var download = safeHttpsUrl(artifact.download_url);
      if (download) {
        var downloadLink = el('a', 'btn btn-primary download-btn');
        downloadLink.href = download;
        downloadLink.target = '_blank';
        downloadLink.rel = 'noopener noreferrer';
        downloadLink.setAttribute('aria-label', t('downloadAria', { file: file }));
        downloadLink.appendChild(icon('icon-download'));
        var downloadLabel = el('span');
        downloadLabel.textContent = t('download');
        downloadLink.appendChild(downloadLabel);
        actionCell.appendChild(downloadLink);
      } else {
        var missing = el('span', 'btn btn-primary download-btn is-disabled');
        missing.setAttribute('aria-disabled', 'true');
        missing.textContent = t('missingLink');
        actionCell.appendChild(missing);
      }
    }

    row.appendChild(idCell);
    row.appendChild(sizeCell);
    row.appendChild(hashCell);
    row.appendChild(actionCell);
    return row;
  }

  function createEmptyState(title, body, compact) {
    var box = el('div', 'empty-state' + (compact ? ' compact' : ''));
    var iconWrap = el('span', 'empty-icon');
    iconWrap.setAttribute('aria-hidden', 'true');
    iconWrap.appendChild(icon('icon-folder'));
    var heading = el('h3');
    heading.textContent = title;
    var paragraph = el('p');
    paragraph.textContent = body;
    box.appendChild(iconWrap);
    box.appendChild(heading);
    box.appendChild(paragraph);
    return box;
  }

  function renderGroups(container, artifacts, animate) {
    container.replaceChildren();

    var valid = artifacts.filter(function (artifact) {
      return isObject(artifact);
    });

    if (!valid.length) {
      container.appendChild(createEmptyState(t('noArtifacts'), t('noArtifactsBody'), true));
      return;
    }

    var groups = new Map();
    valid.forEach(function (artifact) {
      var osName = readText(artifact.os) || t('unknownOS');
      if (!groups.has(osName)) groups.set(osName, []);
      groups.get(osName).push(artifact);
    });

    var entries = Array.from(groups.entries()).sort(function (a, b) {
      var rank = osRank(a[0]) - osRank(b[0]);
      return rank !== 0 ? rank : a[0].localeCompare(b[0]);
    });

    var rowIndex = 0;
    entries.forEach(function (entry) {
      var osName = entry[0];
      var items = entry[1];

      var section = el('div', 'os-group');
      var header = el('div', 'os-heading');
      header.appendChild(icon(osIconId(osName)));
      var heading = el('h3');
      heading.textContent = osName;
      heading.lang = 'en';
      header.appendChild(heading);
      var count = el('span', 'count-pill');
      count.textContent = t('filesCount', { n: items.length });
      header.appendChild(count);
      section.appendChild(header);

      var table = el('div', 'artifact-table');
      var head = el('div', 'artifact-list-head');
      head.setAttribute('aria-hidden', 'true');
      [t('fileHeader'), t('sizeHeader'), t('hashHeader'), t('downloadHeader')].forEach(function (label) {
        var cell = el('span');
        cell.textContent = label;
        head.appendChild(cell);
      });
      table.appendChild(head);

      var list = el('ul', 'artifact-list');
      items.forEach(function (artifact) {
        list.appendChild(createArtifactRow(artifact, rowIndex, animate));
        rowIndex += 1;
      });
      table.appendChild(list);
      section.appendChild(table);
      container.appendChild(section);
    });
  }

  function productVersion(product) {
    var version = product ? readText(product.version) : '';
    if (!version) return '—';
    return version.charAt(0).toLowerCase() === 'v' ? version : 'v' + version;
  }

  function productArtifacts(product) {
    return product && Array.isArray(product.artifacts) ? product.artifacts.filter(isObject) : [];
  }

  function renderProduct(product, refs) {
    var productName = product ? readText(product.name) : '';
    if (productName) refs.name.textContent = productName;
    refs.version.textContent = productVersion(product);

    var released = product ? readText(product.released_at) : '';
    if (released && setTime(refs.released, released)) {
      refs.released.hidden = false;
      refs.released.textContent = t('releasedAt', { date: formatDate(released) });
    } else {
      refs.released.hidden = true;
      refs.released.textContent = '';
      refs.released.removeAttribute('datetime');
    }

    var releaseUrl = product ? safeHttpsUrl(product.release_url) : null;
    if (releaseUrl) {
      refs.release.href = releaseUrl;
      refs.release.hidden = false;
    } else {
      refs.release.removeAttribute('href');
      refs.release.hidden = true;
    }

    if (!product) {
      refs.groups.replaceChildren();
      refs.groups.appendChild(createEmptyState(t('productMissingTitle'), t('productMissingBody')));
      return;
    }

    renderGroups(refs.groups, productArtifacts(product), !state.renderedOnce);
  }

  function findProduct(products, id, nameHint) {
    var byId = products.find(function (product) {
      return readText(product.id) === id;
    });
    if (byId) return byId;
    return products.find(function (product) {
      return readText(product.name).toLowerCase().indexOf(nameHint) !== -1;
    }) || null;
  }

  function setupMirrorLinks(manifest) {
    var mirror = isObject(manifest.mirror) ? manifest.mirror : {};
    var sourceUrl = safeHttpsUrl(mirror.source);
    var sourceLink = $('#official-source');
    var footerSource = $('#footer-source');
    if (sourceUrl) {
      [sourceLink, footerSource].forEach(function (link) {
        if (!link) return;
        link.href = sourceUrl;
        link.hidden = false;
      });
    } else {
      [sourceLink, footerSource].forEach(function (link) {
        if (!link) return;
        link.removeAttribute('href');
        link.hidden = true;
      });
    }

    var owner = readText(mirror.owner);
    var repo = readText(mirror.repo);
    var repoLink = $('#footer-repo');
    var validPart = /^[A-Za-z0-9_.-]+$/;
    if (repoLink && validPart.test(owner) && validPart.test(repo)) {
      repoLink.href = 'https://github.com/' + encodeURIComponent(owner) + '/' + encodeURIComponent(repo);
      repoLink.hidden = false;
    } else if (repoLink) {
      repoLink.removeAttribute('href');
      repoLink.hidden = true;
    }
  }

  function countArtifacts(product) {
    var counts = { mirrored: 0, relay: 0, mirroredSize: 0, relaySize: 0, hasMirroredSize: false };
    productArtifacts(product).forEach(function (artifact) {
      var size = Number(artifact.size);
      var hasSize = isFinite(size) && size >= 0;
      if (isMirroredArtifact(artifact)) {
        counts.mirrored += 1;
        if (hasSize) {
          counts.mirroredSize += size;
          counts.hasMirroredSize = true;
        }
      } else {
        counts.relay += 1;
        if (hasSize) counts.relaySize += size;
      }
    });
    return counts;
  }

  function productMetaText(counts, key) {
    var text = t(key, { n: counts.mirrored });
    if (counts.relay) text += ' · ' + t('relayCountShort', { n: counts.relay });
    return text;
  }

  function renderStats(products, desktop, science) {
    var desktopCounts = countArtifacts(desktop);
    var scienceCounts = countArtifacts(science);

    $('#stat-desktop').textContent = desktop ? productVersion(desktop) : '—';
    $('#stat-desktop-meta').textContent = desktop
      ? productMetaText(desktopCounts, 'statDesktopMeta')
      : t('notInManifest');

    $('#stat-science').textContent = science ? productVersion(science) : '—';
    $('#stat-science-meta').textContent = science
      ? productMetaText(scienceCounts, 'statScienceMeta')
      : t('notInManifest');

    var totalMirrored = 0;
    var totalRelay = 0;
    var totalSize = 0;
    var hasSize = false;
    products.forEach(function (product) {
      var counts = countArtifacts(product);
      totalMirrored += counts.mirrored;
      totalRelay += counts.relay;
      totalSize += counts.mirroredSize;
      if (counts.hasMirroredSize) hasSize = true;
    });

    var sizeNode = $('#stat-size');
    sizeNode.textContent = hasSize ? formatBytes(totalSize) : '—';
    sizeNode.title = hasSize ? exactBytes(totalSize) + ' (mirrored)' : '';
    $('#stat-size-meta').textContent = hasSize
      ? (totalRelay
        ? t('statSizeBreakdown', { n: totalMirrored, r: totalRelay })
        : t('statSizeSimple', { n: totalMirrored }))
      : t('statSizeMeta');
    $('#stat-count').textContent = String(totalMirrored);
    $('#stat-count-meta').textContent = totalRelay
      ? t('statCountBreakdown', { n: totalRelay, p: products.length })
      : t('statArtifactsMeta', { n: products.length });
  }

  function setManifestVisibility(ready) {
    $('#overview').hidden = !ready;
    $('#desktop').hidden = !ready;
    $('#science').hidden = !ready;
    $('#manifest-empty').hidden = ready;
    $('#anchor-nav').hidden = !ready;
    if (!ready) {
      var preview = $('#preview-note');
      if (preview) preview.hidden = true;
    }
  }

  function showManifestProblem(kind) {
    state.manifest = null;
    state.renderedOnce = false;
    setManifestVisibility(false);

    var titleKey = kind === 'invalid' ? 'manifestInvalidTitle' : 'manifestMissingTitle';
    var bodyKey = kind === 'invalid' ? 'manifestInvalidBody' : 'manifestMissingBody';
    var title = $('#empty-title');
    var body = $('#empty-body');
    title.dataset.i18n = titleKey;
    title.textContent = t(titleKey);
    body.dataset.i18n = bodyKey;
    body.textContent = t(bodyKey);

    var updated = $('#last-updated');
    updated.textContent = '—';
    updated.removeAttribute('datetime');
    updated.removeAttribute('title');

    var official = $('#official-source');
    official.removeAttribute('href');
    official.hidden = true;
    ['#footer-repo', '#footer-source'].forEach(function (selector) {
      var link = $(selector);
      link.removeAttribute('href');
      link.hidden = true;
    });
    finishBoot();
  }

  function isLocalPreview() {
    var host = location.hostname;
    return location.protocol === 'file:' ||
      host === 'localhost' ||
      host === '127.0.0.1' ||
      host === '::1' ||
      host === '[::1]';
  }

  function hasPlaceholderHashes(manifest) {
    if (!isObject(manifest) || !Array.isArray(manifest.products)) return false;
    return manifest.products.some(function (product) {
      if (!isObject(product) || !Array.isArray(product.artifacts)) return false;
      return product.artifacts.some(function (artifact) {
        return isObject(artifact) && /^deadbeef/i.test(readText(artifact.sha256));
      });
    });
  }

  function renderPreviewNotice(manifest) {
    var banner = $('#preview-note');
    if (!banner) return;
    var sampleFlag = isObject(manifest) && manifest.sample === true;
    var placeholder = hasPlaceholderHashes(manifest);
    var sample = sampleFlag || placeholder;
    var local = isLocalPreview();
    document.documentElement.dataset.sample = sample ? 'true' : 'false';
    banner.hidden = !sample && !local;
    var titleKey = sample ? 'previewTitlePlaceholder' : 'previewTitle';
    var bodyKey = sampleFlag ? 'previewBodySample' : (placeholder ? 'previewBodyPlaceholder' : 'previewBody');
    var title = $('#preview-title');
    var body = $('#preview-body');
    if (title) {
      title.dataset.i18n = titleKey;
      title.textContent = t(titleKey);
    }
    if (body) {
      body.dataset.i18n = bodyKey;
      body.textContent = t(bodyKey);
    }
  }

  function renderManifest(manifest) {
    if (!isObject(manifest) || !Array.isArray(manifest.products)) {
      showManifestProblem('invalid');
      return;
    }

    state.manifest = manifest;
    setManifestVisibility(true);

    var updated = $('#last-updated');
    if (!setTime(updated, manifest.generated_at)) {
      updated.textContent = '—';
    }

    renderPreviewNotice(manifest);
    setupMirrorLinks(manifest);

    var products = manifest.products.filter(isObject);
    var desktop = findProduct(products, 'claude-desktop', 'desktop');
    var science = findProduct(products, 'claude-science', 'science');

    renderStats(products, desktop, science);

    renderProduct(desktop, {
      name: $('#desktop-name'),
      version: $('#desktop-version'),
      released: $('#desktop-released'),
      release: $('#desktop-release'),
      groups: $('#desktop-groups')
    });

    renderProduct(science, {
      name: $('#science-name'),
      version: $('#science-version'),
      released: $('#science-released'),
      release: $('#science-release'),
      groups: $('#science-groups')
    });

    state.renderedOnce = true;
    finishBoot();
  }

  function resolveManifest() {
    var globalManifest = window.MIRROR_MANIFEST;

    if (typeof globalManifest === 'string') {
      try {
        globalManifest = JSON.parse(globalManifest);
      } catch (error) {
        return Promise.resolve({ kind: 'invalid' });
      }
    }

    if (globalManifest !== undefined) {
      return Promise.resolve(isObject(globalManifest) && Array.isArray(globalManifest.products)
        ? { kind: 'ok', manifest: globalManifest }
        : { kind: 'invalid' });
    }

    if (location.protocol === 'http:' || location.protocol === 'https:') {
      return fetch('data/manifest.json', { cache: 'no-store' }).then(function (response) {
        if (!response.ok) {
          return { kind: response.status === 404 ? 'missing' : 'invalid' };
        }
        return response.json().then(function (data) {
          return isObject(data) && Array.isArray(data.products)
            ? { kind: 'ok', manifest: data }
            : { kind: 'invalid' };
        }, function () {
          return { kind: 'invalid' };
        });
      }).catch(function () {
        return { kind: 'missing' };
      });
    }

    return Promise.resolve({ kind: 'missing' });
  }

  function bindEvents() {
    $all('[data-lang-btn]').forEach(function (button) {
      button.addEventListener('click', function () {
        var next = button.dataset.langBtn;
        if (next !== 'zh' && next !== 'en') return;
        if (next === state.lang) return;
        state.lang = next;
        try {
          localStorage.setItem('cdm-lang', next);
        } catch (error) {
          /* storage unavailable */
        }
        applyStaticLanguage();
      });
    });

    var themeToggle = $('#theme-toggle');
    if (themeToggle) {
      themeToggle.addEventListener('click', function () {
        var dark = !document.documentElement.classList.contains('dark');
        document.documentElement.classList.toggle('dark', dark);
        document.documentElement.dataset.theme = dark ? 'dark' : 'light';
        try {
          localStorage.setItem('cdm-theme', dark ? 'dark' : 'light');
        } catch (error) {
          /* storage unavailable */
        }
        updateThemeUI();
      });
    }

    try {
      var media = window.matchMedia('(prefers-color-scheme: dark)');
      media.addEventListener('change', function (event) {
        var stored = null;
        try {
          stored = localStorage.getItem('cdm-theme');
        } catch (error) {
          stored = null;
        }
        if (stored) return;
        document.documentElement.classList.toggle('dark', event.matches);
        document.documentElement.dataset.theme = event.matches ? 'dark' : 'light';
        updateThemeUI();
      });
    } catch (error) {
      /* matchMedia unavailable */
    }
  }

  function finishBoot() {
    document.documentElement.classList.remove('is-booting');
    var main = $('#main');
    if (main) main.setAttribute('aria-busy', 'false');
  }

  function initLanguage() {
    var stored = null;
    try {
      stored = localStorage.getItem('cdm-lang');
    } catch (error) {
      stored = null;
    }
    state.lang = stored === 'en' ? 'en' : 'zh';
  }

  function init() {
    initLanguage();
    bindEvents();
    applyStaticLanguage();
    updateThemeUI();

    resolveManifest().then(function (result) {
      try {
        if (result.kind === 'ok') {
          renderManifest(result.manifest);
        } else {
          showManifestProblem(result.kind === 'invalid' ? 'invalid' : 'missing');
        }
      } catch (error) {
        showManifestProblem('invalid');
      }
    }, function () {
      showManifestProblem('invalid');
    });
  }

  init();
})();
