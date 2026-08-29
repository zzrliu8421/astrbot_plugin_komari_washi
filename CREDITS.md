# CREDITS

## 原始项目

- **astrbot_plugin_komari_status** — https://github.com/nulijiazaizhong/astrbot_plugin_komari_status
  - Author: `nulijiazaizhong`
  - Contribution: 插件框架、Komari API 对接（`/api/nodes`、`/api/realtime`、`/api/public`、`/api/version`）、文本/图片双模式输出、配置项与正则触发器设计

## 本衍生项目

- **astrbot_plugin_komari_washi** — https://github.com/zzrliu8421/astrbot_plugin_komari_washi
  - Author: `zzrliu8421` (2026)
  - Contribution:
    - **v2.0.0 Washi**：暖纸侘寂（Washi）视觉重设计 — `resources/status.html` 与 `resources/realtime.html` 的完整重写（暖纸色板 `#f6f5f1 / #0a0a0b`、衬线标题 `Cormorant Garamond`、等宽数据 `JetBrains Mono`、hairline 边框与柔和阴影体系）、中文化标签、计费/流量边界修复与字段补全、AGPL-3.0 合规化、marketplace 抛光（`logo.png 256×256`、`short_desc/tags/astrbot_version`）
    - **v2.0.1**：安全加固 — 移除 `ssl=False` 硬编码 MITM 风险，新增 `verify_ssl` 默认校验（`_conf_schema.json` 默认 `true`，三处 `aiohttp` 统一尊重开关）
    - **v2.0.2**：修复 `kr` 文字模式 `mem_total_gb` 键名错误导致 `内存: 0 GB` 及信息缺失，文字模式现与图片模板对齐输出全量指标
    - **v2.0.3**：`kr` 离线可见性 — 合并 `GET /api/nodes` 全量与 `WSS /api/clients` 在线，离线节点以 `is_online=False` 虚线卡追加（`ram_total_gb/disk_total_gb` 兜底，`bars-empty` 占位），验证于 `https://komari.sylv.top`

## 上游依赖

- **Komari** — https://github.com/komari-monitor/komari (AGPL-3.0) — 监控数据来源
- **AstrBot** — https://github.com/Soulter/AstrBot — 机器人框架与 `html_render` 能力

## 字体与资源

- Google Fonts: `Cormorant Garamond`, `JetBrains Mono`, `Noto Serif SC` (OFL)
- 设计灵感：日本和纸（Washi）纹理与侘寂（Wabi-Sabi）留白美学

## 致谢

感谢 `nulijiazaizhong` 的原始开源工作，使本重制成为可能。所有原始版权归其所有，本项目仅在保留署名的前提下进行视觉、安全与功能层面的二次创作（截至 2.0.3）。
