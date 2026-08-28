# Komari Washi · 和纸监控

> 暖纸侘寂 · 优雅重制 — 基于 `nulijiazaizhong/astrbot_plugin_komari_status` 的 AstrBot Komari 监控插件。

<p align="center">
  <img src="https://img.shields.io/badge/license-AGPL--3.0-blue?style=flat-square" alt="AGPL-3.0">
  <img src="https://img.shields.io/badge/version-2.0.0-efebe3?style=flat-square" alt="2.0.0">
  <img src="https://img.shields.io/badge/style-washi%20%E5%92%8C%E7%BA%B8-f6f5f1?style=flat-square" alt="washi">
  <img src="https://img.shields.io/badge/AstrBot-%E2%89%A50.6-58a6ff?style=flat-square" alt="astrbot">
</p>

---

## 概览

Washi（和纸）是本项目的视觉主题：以 **暖纸 `#f6f5f1` / 暖黑 `#0a0a0b`** 为底，搭配 **CORMORANT 衬线标题 + JetBrains Mono 等宽数据**，以 hairline 边框与柔和阴影呈现侘寂留白。功能上完整保留原始插件的全部数据字段与触发逻辑，仅重绘渲染层并补全边界展示。

| 旧版字段 | Washi 版 |
|---|---|
| `status.html` 14 字段 | **15 字段（原 14 全保留 + `updated_at` 兜底）** |
| `realtime.html` 19 字段 | **24 字段（原 19 全保留 + `disk_used_gb/ram_used_gb/os/traffic_*`）** |
| 中文/英文混排、强渐变 | 统一中文标签、双主题暖纸体系 |

## 功能特性

- **节点状态**：`name / region / os / cpu_name / cpu_cores / mem_total / disk_total / traffic_limit(+type) / price(+billing_cycle) / updated_at_cn / is_online`
- **实时监控**：`cpu/ram/disk%` 进度条（50/80 三档阈值）、`net_up/down`、`traffic`、`load_1/5/15`、`uptime`、`virtualization/group`
- **双模式**：文本回退 + `html_render` 精美图片
- **双主题**：`dark_theme` 开关，`viewport_width` 可调（300–2000px）
- **自定义触发**：4 条正则可配，支持短指令

## 安装与配置

### 1. 安装

- AstrBot 插件市场搜索 `komari_washi`（或 `komari_status` 迁移用户直接替换本仓库）
- 或手动：`git clone https://github.com/zzrliu8421/astrbot_plugin_komari_washi.git` 至 `data/plugins/`

### 2. 配置（WebUI 插件配置页）

| 配置项 | 说明 | 默认值 |
| :--- | :--- | :--- |
| **Komari 服务器地址** | 您的 Komari 面板 URL（如 `https://status.example.com`） | — |
| **API Token** | API Key 或 Session Token（非公开站点必填） | — |
| **以图片形式发送** | 开启后调用 `html_render` 以图片发送 | `false` |
| **是否启用深色背景** | 深色暖黑 / 浅色暖纸 | `true` |
| **图片宽度** | 生成图片宽度（px） | `600` |

## 指令列表

默认正则（可在配置中自定义）：

- **查询节点状态**：`查询\s*Komari\s*节点状态`
- **查询实时状态**：`查询\s*Komari\s*实时状态`
- **查询公开设置**：`查询\s*Komari\s*公开设置`
- **查询版本信息**：`查询\s*Komari\s*版本信息`

### 自定义短命令示例

| 需求 | 配置项 | 填入值 | 效果 |
|---|---|---|---|
| 短命令 `k状态` | `trigger_realtime` | `(k\|komari)\\s*(实时\|状态)` | `k实时` / `komari状态` 触发 |
| 口语兼容 | `trigger_realtime` | `(查询\|看下)\\s*(k\|服务器)\\s*状态` | `看下服务器状态` 触发 |
| 严格匹配 | `trigger_nodes` | `^node$` | 仅 `node` 触发 |

> 正则小贴士：`\s*` 允许任意空格，`\|` 表示“或”，`^/$` 锚定首尾。

## 渲染预览

- 状态页：暖纸卡片 + 顶部 `KOMARI · STATUS / N NODES` 眉题 + 在线汇总胶囊 + 3 指标（内存/磁盘/流量）+ 操作系统/处理器/费用/更新时间
- 实时页：`LIVE` 脉冲眉题 + `高负载/中等/正常` 三档胶囊 + 流光进度条 + 6 详情卡（CPU 核心/内存总量/磁盘总量/网络流量/运行时间/系统负载）

> 预览文件位于 `/opt/data/*_preview.html`（如从本机安装），或直接在 AstrBot 中开启“以图片形式发送”查看。

## 致谢

本项目为衍生重制，致谢如下（详见 [NOTICE](./NOTICE.md) / [CREDITS](./CREDITS.md)）：

- **原始项目**：[`nulijiazaizhong/astrbot_plugin_komari_status`](https://github.com/nulijiazaizhong/astrbot_plugin_komari_status)（`646ec79`）— 插件框架与 Komari API 对接，版权归 `nulijiazaizhong` 所有
- **上游**：[`komari-monitor/komari`](https://github.com/komari-monitor/komari)（AGPL-3.0）、[`Soulter/AstrBot`](https://github.com/Soulter/AstrBot)
- **字体**：`Cormorant Garamond / JetBrains Mono / Noto Serif SC`（OFL）
- **本衍生视觉重设计**：`zzrliu8421`（2026）

## 许可证

- 本衍生项目以 **GNU Affero General Public License v3.0（AGPL-3.0）** 发布，详见 [`LICENSE`](./LICENSE)。
- 原始仓库无 `LICENSE`（All Rights Reserved），本 Fork 已通过 `NOTICE`/`CREDITS`/`LICENSE` 头注保留完整署名与溯源。
- 依据 AGPL-3.0 §13，通过网络提供服务时须向用户提供完整对应源码。

## 更新日志

### v2.0.0 (Washi)

- 视觉重生：暖纸侘寂双主题重写 `status.html` / `realtime.html`
- 字段补全：`status` 新增 `updated_at` 兜底；`realtime` 新增 `disk_used_gb/ram_used_gb/os/traffic_*` 与 `CPU 核心` 卡
- 交互修复：流量 `round(2)` 精度、`无限制` 文案、`N/A` 兜底、`price==0` 时隐藏费用、中文化标签、负载 `a / b / c` 统一
- 合规：新增 `LICENSE(AGPL-3.0)` / `NOTICE.md` / `CREDITS.md`，`metadata`/`@register` 更新为 `zzrliu8421/komari_washi`

### 原始日志（`nulijiazaizhong`）

- **v1.0.6** 修复 节点异常离线
- **v1.0.5** 修复 计费周期/流量不显示
- **v1.0.4** 修复 离线仍显示在线
- **v1.0.3** 更新图片模板
- **v1.0.2** 修复 CPU 占用率异常
- **v1.0.1** 修改插件名称
- **v1.0.0** 初始可用版本
