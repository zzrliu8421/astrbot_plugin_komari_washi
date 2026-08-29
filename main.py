# -*- coding: utf-8 -*-
# Komari Washi — 和纸监控 (astrbot_plugin_komari_washi) v2.0.2
# Author: zzrliu8421 — https://github.com/zzrliu8421/astrbot_plugin_komari_washi
# License: AGPL-3.0 (see LICENSE)
#
# Derivative of: https://github.com/nulijiazaizhong/astrbot_plugin_komari_status (commit 646ec79)
# Original author: nulijiazaizhong — original repo has NO LICENSE (All Rights Reserved), used with attribution.
# Upstream Komari: https://github.com/komari-monitor/komari (AGPL-3.0)

import logging
import re
from datetime import datetime, timezone, timedelta
from astrbot.api.all import *
from astrbot.api.event import AstrMessageEvent
from astrbot.api.event import filter
from astrbot.api.message_components import Image
import aiohttp
import json
import os

from typing import Optional
from pydantic import BaseModel, Field

class KomariConfig(BaseModel):
    komari_url: Optional[str] = Field(None, description="Komari 服务器地址 (例如 https://status.example.com)")
    komari_token: Optional[str] = Field(None, description="API Key 或 Session Token (可选)")
    image_output: bool = Field(False, description="开启后，状态报告将调用文本转图像服务以图片形式发送。")
    dark_theme: bool = Field(True, description="开启后，生成的图片将使用深色主题背景。")
    viewport_width: int = Field(600, description="图片生成宽度 (像素)")
    verify_ssl: bool = Field(True, description="是否验证 TLS 证书（仅在自签名证书等特殊场景下关闭，有中间人风险）")
    
    # Custom Triggers (Regex)
    trigger_nodes: str = Field("查询\\s*Komari\\s*节点状态", description="[正则] 查询节点状态的触发指令，支持自定义。")
    trigger_realtime: str = Field("查询\\s*Komari\\s*实时状态", description="[正则] 查询实时状态的触发指令，支持自定义。")
    trigger_public: str = Field("查询\\s*Komari\\s*公开设置", description="[正则] 查询公开设置的触发指令，支持自定义。")
    trigger_version: str = Field("查询\\s*Komari\\s*版本信息", description="[正则] 查询版本信息的触发指令，支持自定义。")

@register("komari_washi", "zzrliu8421", "Komari Washi · 和纸监控 — 暖纸侘寂重制版", "2.0.2", "https://github.com/zzrliu8421/astrbot_plugin_komari_washi")
class KomariStatusPlugin(Star):
    def __init__(self, context: Context, config: KomariConfig = None):
        super().__init__(context)
        self.config = config or KomariConfig()
        self.logger = logging.getLogger("astrbot_plugin_komari_washi")
        
        # Load template
        self.template_str = ""
        try:
            template_path = os.path.join(os.path.dirname(__file__), "resources", "status.html")
            if os.path.exists(template_path):
                with open(template_path, "r", encoding="utf-8") as f:
                    self.template_str = f.read()
                self.logger.info(f"模板加载成功，长度: {len(self.template_str)}")
            else:
                self.logger.error(f"模板文件不存在: {template_path}")
        except Exception as e:
            self.logger.error(f"加载模板失败: {e}")

    @filter.command("komari_version", alias=["kv", "ver", "版本"])
    async def komari_version(self, event: AstrMessageEvent):
        '''查询 Komari 版本信息'''
        data, error = await self._fetch_api("/api/version")
        if error:
            yield event.plain_result(error)
            return
            
        ver_data = data.get("data", {})
        yield event.plain_result(f"Komari 版本: {ver_data.get('version')} ({ver_data.get('hash')})")

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        text = event.message_str
        if not text:
            return

        # 移除 ^ 和 $ 以支持更自然的语言（如 "帮我查询..."）
        # 使用 re.IGNORECASE 忽略大小写
        
        # 1. Nodes Status
        if re.search(self.config.trigger_nodes, text, re.IGNORECASE):
            async for result in self.komari_nodes(event):
                yield result
        
        # 2. Realtime Status
        elif re.search(self.config.trigger_realtime, text, re.IGNORECASE):
            async for result in self.komari_realtime(event):
                yield result
            
        # 3. Public Settings
        elif re.search(self.config.trigger_public, text, re.IGNORECASE):
            async for result in self.komari_public(event):
                yield result

        # 4. Version Info
        elif re.search(self.config.trigger_version, text, re.IGNORECASE):
            async for result in self.komari_version(event):
                yield result

    async def _fetch_api(self, endpoint: str):
        if not self.config.komari_url:
            return None, "请在插件设置中配置 Komari 服务器地址。"
        
        url = self.config.komari_url.rstrip("/") + endpoint
        headers = {}
        if self.config.komari_token:
            headers["Authorization"] = f"Bearer {self.config.komari_token}"
            # Also try Cookie if Bearer fails? Or just set both? 
            # Komari docs say Cookie: session_token=...
            headers["Cookie"] = f"session_token={self.config.komari_token}"

        try:
            # 默认校验 TLS 证书；仅当 verify_ssl=False 时禁用校验（兼容自签名，需用户显式开启）
            ssl = True if self.config.verify_ssl else False
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10, ssl=ssl) as resp:
                    if resp.status != 200:
                        return None, f"API 请求错误: {resp.status}"
                    data = await resp.json()
                    return data, None
        except Exception as e:
            return None, f"网络错误: {str(e)}"

    async def _get_online_uuids(self):
        if not self.config.komari_url:
            return None
            
        base_url = self.config.komari_url.rstrip("/")
        ws_url = base_url.replace("https://", "wss://").replace("http://", "ws://") + "/api/clients"
        
        headers = {}
        if self.config.komari_token:
            headers["Authorization"] = f"Bearer {self.config.komari_token}"
            headers["Cookie"] = f"session_token={self.config.komari_token}"

        try:
            # Short timeout for status check
            timeout = aiohttp.ClientTimeout(total=3.0)
            ssl = True if self.config.verify_ssl else False
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.ws_connect(ws_url, headers=headers, ssl=ssl) as ws:
                    await ws.send_str("get")
                    msg = await ws.receive()
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        resp = json.loads(msg.data)
                        if isinstance(resp, dict) and resp.get("status") == "success":
                            raw_data = resp.get("data", {})
                            # Structure check similar to komari_realtime
                            if isinstance(raw_data, dict) and "online" in raw_data:
                                return set(raw_data.get("online", []))
                            # Fallback: maybe raw_data is list of nodes? Not common for 'get' command but possible in variants
                            return None
        except Exception as e:
            self.logger.warning(f"WS在线检查失败 (将回退到时间判断): {e}")
            return None
        return None

    @filter.command("komari", alias=["k", "status", "节点"])
    async def komari_nodes(self, event: AstrMessageEvent):
        '''查询 Komari 节点状态'''
        data, error = await self._fetch_api("/api/nodes")
        if error:
            yield event.plain_result(error)
            return

        if not data.get("status") == "success":
            yield event.plain_result(f"API 调用失败: {data.get('message', '未知错误')}")
            return

        nodes = data.get("data", [])
        if not nodes:
            yield event.plain_result("未找到任何节点。")
            return

        # 获取 WS 在线列表 (可选，用于增强准确性)
        online_uuids = await self._get_online_uuids()
        
        # 处理节点状态
        now_utc = datetime.now(timezone.utc)
        tz_cn = timezone(timedelta(hours=8))
        
        for node in nodes:
            is_online = False
            is_ws_online = False
            is_time_online = False
            
            # 1. WS 验证
            if online_uuids is not None:
                if node.get("uuid") in online_uuids or node.get("id") in online_uuids:
                    is_ws_online = True
            
            # 2. 时间判断 (10分钟 = 600秒)
            updated_at_str = node.get("updated_at")
            if updated_at_str:
                try:
                    # 格式: 2026-01-23T12:04:33Z 或 2026-01-23T12:04:33.123Z
                    if updated_at_str.endswith("Z"):
                            updated_at_str = updated_at_str.replace("Z", "+00:00")
                    
                    updated_at = datetime.fromisoformat(updated_at_str)
                    if updated_at.tzinfo is None:
                        updated_at = updated_at.replace(tzinfo=timezone.utc)
                        
                    diff = now_utc - updated_at
                    # 600秒(10分钟)无心跳视为离线
                    if diff.total_seconds() < 600:
                        is_time_online = True
                except Exception:
                    pass
            
            # 只要满足 WS 在线 或 时间在范围内，即视为在线
            if is_ws_online or is_time_online:
                is_online = True
            
            node["is_online"] = is_online
            
            # 格式化更新时间为东八区
            if node.get("updated_at"):
                 try:
                     updated_at_str = node.get("updated_at").replace("Z", "+00:00")
                     dt = datetime.fromisoformat(updated_at_str)
                     if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                     dt_cn = dt.astimezone(tz_cn)
                     node["updated_at_cn"] = dt_cn.strftime("%Y-%m-%d %H:%M:%S")
                 except:
                     node["updated_at_cn"] = node.get("updated_at")

        if self.config.image_output:
            yield await self._handle_image_output(event, nodes)
        else:
            yield self._handle_text_output(event, nodes)

    @filter.command("komari_public", alias=["kp", "site", "站点信息"])
    async def komari_public(self, event: AstrMessageEvent):
        '''查询 Komari 公开设置'''
        data, error = await self._fetch_api("/api/public")
        if error:
            yield event.plain_result(error)
            return
        
        settings = data.get("data", {})
        
        # Format nice output
        info = []
        info.append(f"站点名称: {settings.get('sitename', '未知')}")
        info.append(f"描述: {settings.get('description', '')}")
        info.append(f"主题: {settings.get('theme', '默认')}")
        
        yield event.plain_result("\n".join(info))

    @filter.command("komari_realtime", alias=["kr", "realtime", "实时", "实时状态"])
    async def komari_realtime(self, event: AstrMessageEvent):
        '''查询 Komari 实时状态 (WebSocket)'''
        if not self.config.komari_url:
            yield event.plain_result("请在插件设置中配置 Komari 服务器地址。")
            return

        # 1. 获取节点静态信息
        static_nodes = {}
        try:
            data, _ = await self._fetch_api("/api/nodes")
            if data and data.get("data"):
                for n in data.get("data"):
                    if n.get("id"):
                        static_nodes[n.get("id")] = n
                    if n.get("uuid"):
                        static_nodes[n.get("uuid")] = n
        except Exception as e:
            self.logger.warning(f"静态节点信息获取失败: {e}")

        # 2. WebSocket 连接
        base_url = self.config.komari_url.rstrip("/")
        ws_url = base_url.replace("https://", "wss://").replace("http://", "ws://") + "/api/clients"
        
        headers = {}
        if self.config.komari_token:
            headers["Authorization"] = f"Bearer {self.config.komari_token}"
            headers["Cookie"] = f"session_token={self.config.komari_token}"

        realtime_data = []
        try:
            # WebSocket 默认校验 TLS；verify_ssl=False 时才禁用（需用户显式配置）
            ssl = True if self.config.verify_ssl else False
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(ws_url, headers=headers, ssl=ssl) as ws:
                    await ws.send_str("get")
                    
                    # 尝试读取响应
                    for _ in range(3):
                        msg = await ws.receive()
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                resp = json.loads(msg.data)
                                if isinstance(resp, dict) and resp.get("status") == "success":
                                    # Print API response as requested by user
                                    try:
                                        print(f"Komari WS Response: {json.dumps(resp, ensure_ascii=False, indent=2)}")
                                    except:
                                        pass
                                    
                                    # Handle {"data": {"online": [...], "data": {...}}} structure
                                    raw_data = resp.get("data", {})
                                    if isinstance(raw_data, dict) and "online" in raw_data and "data" in raw_data:
                                        online_uuids = raw_data.get("online", [])
                                        details_map = raw_data.get("data", {})
                                        
                                        realtime_list = []
                                        for uuid in online_uuids:
                                            if uuid in details_map:
                                                node_info = details_map[uuid]
                                                node_info["uuid"] = uuid
                                                realtime_list.append(node_info)
                                        realtime_data = realtime_list
                                    else:
                                        realtime_data = raw_data
                                    break
                            except Exception:
                                pass
                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break
        except Exception as e:
            yield event.plain_result(f"连接失败: {e}")
            return

        if not realtime_data:
            yield event.plain_result("未获取到数据，请检查服务状态。")
            return

        # 3. 数据处理
        processed_nodes = []
        
        # 增加数据类型调试日志
        if realtime_data:
            try:
                # 尝试获取第一个元素进行类型检查，兼容 list 和 dict
                first_elem = None
                if isinstance(realtime_data, list) and len(realtime_data) > 0:
                    first_elem = realtime_data[0]
                elif isinstance(realtime_data, dict):
                    # 如果是 dict，可能数据结构不同，打印 keys
                    first_elem = list(realtime_data.keys())
                
                self.logger.info(f"WebSocket数据类型: {type(realtime_data)}, 样本: {type(first_elem)}")
            except Exception:
                pass

        # 确保 realtime_data 是可迭代列表
        if isinstance(realtime_data, dict):
             self.logger.info(f"WebSocket 数据是 dict，keys: {list(realtime_data.keys())}")
             
             # 策略1: 检查是否包含常见列表字段
             found_list = False
             for key in ['servers', 'nodes', 'clients', 'list', 'data']:
                 if key in realtime_data and isinstance(realtime_data[key], list):
                     realtime_data = realtime_data[key]
                     found_list = True
                     break
            
             # 策略2: 如果没有常见列表字段，收集所有 dict 类型的 value (假设是 id -> node 映射)
             if not found_list:
                 potential_nodes = [v for v in realtime_data.values() if isinstance(v, dict)]
                 if potential_nodes:
                     self.logger.info(f"从 dict 中提取到 {len(potential_nodes)} 个节点对象")
                     realtime_data = potential_nodes
                 else:
                     self.logger.warning(f"无法从 dict 中提取节点列表: {realtime_data}")
                     yield event.plain_result(f"数据格式异常 (Dict解析失败, keys={list(realtime_data.keys())})")
                     return

        for node in realtime_data:
            # 兼容处理：如果 node 是字符串（JSON String），尝试解析
            if isinstance(node, str):
                try:
                    node = json.loads(node)
                except Exception:
                    self.logger.warning(f"无法解析节点数据(str): {node[:100]}...")
                    continue
            
            # 确保 node 是字典
            if not isinstance(node, dict):
                self.logger.warning(f"节点数据格式错误，跳过: {type(node)}")
                continue

            uuid = node.get("uuid")
            node_id = node.get("id")
            name = node.get("name")
            
            # 尝试通过 uuid 或 id 查找静态信息
            lookup_key = uuid or node_id
            
            # 补全信息 (从静态节点信息中合并缺失字段)
            if lookup_key and lookup_key in static_nodes:
                static_info = static_nodes[lookup_key]
                for k, v in static_info.items():
                    if k not in node or node[k] is None:
                        node[k] = v
                
                # 特殊处理 name
                if not name or name == "Unknown":
                    name = static_info.get("name", name)
            
            node["name"] = name or "未知节点"
            
            # 格式化实时数据
            # 1. CPU
            if "cpu" in node and isinstance(node["cpu"], dict):
                 cpu_usage = node["cpu"].get("usage", 0)
                 if cpu_usage is not None:
                     # User reported that API returns actual percentage value (e.g. 0.375 for 0.375%), so no need to multiply by 100
                     node["cpu_usage_percent"] = round(float(cpu_usage), 2)
            
            # 2. RAM
            if "ram" in node and isinstance(node["ram"], dict):
                ram_total = node["ram"].get("total", 0)
                ram_used = node["ram"].get("used", 0)
                if ram_total > 0:
                    node["ram_total_gb"] = round(ram_total / 1024**3, 2)
                    node["ram_used_gb"] = round(ram_used / 1024**3, 2)
                    node["ram_usage_percent"] = round((ram_used / ram_total) * 100, 1)
            elif "mem_total" in node:
                 # Fallback to static info if no realtime ram info
                 node["ram_total_gb"] = round(node.get("mem_total", 0) / 1024**3, 2)

            # 3. Disk
            if "disk" in node and isinstance(node["disk"], dict):
                disk_total = node["disk"].get("total", 0)
                disk_used = node["disk"].get("used", 0)
                if disk_total > 0:
                    node["disk_total_gb"] = round(disk_total / 1024**3, 2)
                    node["disk_used_gb"] = round(disk_used / 1024**3, 2)
                    node["disk_usage_percent"] = round((disk_used / disk_total) * 100, 1)
            elif "disk_total" in node:
                 node["disk_total_gb"] = round(node.get("disk_total", 0) / 1024**3, 2)
            
            # 4. Network
            if "network" in node and isinstance(node["network"], dict):
                # Convert bytes/s to MB/s or KB/s
                up = node["network"].get("up", 0)
                down = node["network"].get("down", 0)
                
                def fmt_speed(b):
                    if b > 1024*1024:
                        return f"{b/1024/1024:.1f} MB/s"
                    else:
                        return f"{b/1024:.1f} KB/s"
                
                node["net_up_str"] = fmt_speed(up)
                node["net_down_str"] = fmt_speed(down)
                
                total_up = node["network"].get("totalUp", 0)
                total_down = node["network"].get("totalDown", 0)
                
                def fmt_traffic(b):
                    if b > 1024**3:
                        return f"{b/1024**3:.2f} GB"
                    else:
                        return f"{b/1024**2:.2f} MB"
                        
                node["traffic_up_str"] = fmt_traffic(total_up)
                node["traffic_down_str"] = fmt_traffic(total_down)

            # 5. Uptime
            if "uptime" in node:
                uptime_sec = node.get("uptime", 0)
                days = uptime_sec // 86400
                hours = (uptime_sec % 86400) // 3600
                node["uptime_str"] = f"{days}天 {hours}小时"

            # 6. Load
            if "load" in node and isinstance(node["load"], dict):
                node["load_1"] = node["load"].get("load1")
                node["load_5"] = node["load"].get("load5")
                node["load_15"] = node["load"].get("load15")
                
            processed_nodes.append(node)

        # 4. 输出
        if self.config.image_output:
            # 这里必须使用 async for 来处理生成器
            async for r in self._handle_realtime_image_gen(event, processed_nodes):
                yield r
        else:
            msg = ["📊 **Komari 实时状态**"]
            for node in processed_nodes:
                region = node.get('region', '')
                name = node.get('name', '未知节点')
                cpu_pct = node.get('cpu_usage_percent')
                if cpu_pct is not None:
                    try:
                        cpu_f = float(cpu_pct)
                        if cpu_f >= 80:
                            status_label = "🔴 高负载"
                        elif cpu_f >= 50:
                            status_label = "🟡 中等"
                        else:
                            status_label = "🟢 正常"
                    except:
                        status_label = "🟢 在线"
                else:
                    status_label = "🟢 在线"
                msg.append(f"\n📌 {status_label} {region} {name}".strip())

                # 系统信息
                sys_parts = []
                if node.get('os'):
                    sys_parts.append(f"系统: {node.get('os')}")
                if node.get('virtualization'):
                    sys_parts.append(f"虚拟化: {node.get('virtualization')}")
                if node.get('group'):
                    sys_parts.append(f"分组: {node.get('group')}")
                if node.get('cpu_cores'):
                    sys_parts.append(f"核心: {node.get('cpu_cores')}C")
                if sys_parts:
                    msg.append(f"   {' | '.join(sys_parts)}")

                # CPU
                if cpu_pct is not None:
                    msg.append(f"   CPU: {cpu_pct}%")

                # 内存
                if node.get('ram_usage_percent') is not None:
                    total = node.get('ram_total_gb', '-')
                    used = node.get('ram_used_gb', '-')
                    pct = node.get('ram_usage_percent')
                    msg.append(f"   内存: {pct}% ({used}/{total} GB)")
                elif node.get('ram_total_gb') is not None:
                    # 兼容静态兜底
                    msg.append(f"   内存: {node.get('ram_total_gb')} GB (已用 {node.get('ram_used_gb', '?')} GB)")

                # 磁盘
                if node.get('disk_usage_percent') is not None:
                    total = node.get('disk_total_gb', '-')
                    used = node.get('disk_used_gb', '-')
                    pct = node.get('disk_usage_percent')
                    msg.append(f"   磁盘: {pct}% ({used}/{total} GB)")
                elif node.get('disk_total_gb') is not None:
                    msg.append(f"   磁盘: {node.get('disk_total_gb')} GB (已用 {node.get('disk_used_gb', '?')} GB)")

                # 网络
                if node.get('net_up_str') or node.get('net_down_str'):
                    up = node.get('net_up_str', '-')
                    down = node.get('net_down_str', '-')
                    msg.append(f"   网络: ↑ {up} ↓ {down}")
                if node.get('traffic_up_str') or node.get('traffic_down_str'):
                    tu = node.get('traffic_up_str', '-')
                    td = node.get('traffic_down_str', '-')
                    msg.append(f"   流量累计: ↑ {tu} ↓ {td}")

                # 负载
                if node.get('load_1') is not None:
                    msg.append(f"   负载: {node.get('load_1')} / {node.get('load_5')} / {node.get('load_15')} (1/5/15min)")

                # 运行时间与更新时间
                if node.get('uptime_str'):
                    upd = node.get('updated_at', '').replace('T', ' ').replace('Z', '') if node.get('updated_at') else "N/A"
                    msg.append(f"   运行: {node.get('uptime_str')} | 更新: {upd}")
                elif node.get('updated_at'):
                    upd = node.get('updated_at', '').replace('T', ' ').replace('Z', '')
                    msg.append(f"   更新: {upd}")
            yield event.plain_result("\n".join(msg))

    async def _handle_realtime_image_gen(self, event, nodes):
        # 尝试加载实时状态专用模板
        template_str = ""
        try:
            path = os.path.join(os.path.dirname(__file__), "resources", "realtime.html")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    template_str = f.read()
        except Exception:
            pass
            
        # 如果没有专用模板，回退到通用模板或报错
        if not template_str:
            self.logger.warning("realtime.html not found, falling back to default template")
            template_str = self.template_str

        if not template_str:
             yield event.plain_result("未找到 HTML 模板文件。")
             return

        try:
            # 数据预处理：将字节转换为 GB，保留两位小数
            # 注意：大部分数据处理已经在 komari_realtime 中完成了，这里主要是兜底或补充
            pass


            data = {"nodes": nodes, "title": "Komari 实时监控", "dark_theme": self.config.dark_theme}
            options = {
                "type": "jpeg",
                "quality": 92,
                "full_page": True,
                "omit_background": False
            }
            
            img_url = await self.html_render(template_str, data, options=options)
            
            if img_url:
                yield event.chain_result([Image.fromURL(img_url)])
            else:
                yield event.plain_result("图片生成失败。")
        except Exception as e:
            self.logger.error(f"实时状态图片生成失败: {e}")
            msg = ["📊 **Komari 实时状态 (文本模式)**"]
            for node in nodes:
                region = node.get('region', '')
                name = node.get('name', '未知节点')
                cpu_pct = node.get('cpu_usage_percent')
                status_label = "🟢 在线"
                if cpu_pct is not None:
                    try:
                        cpu_f = float(cpu_pct)
                        if cpu_f >= 80:
                            status_label = "🔴 高负载"
                        elif cpu_f >= 50:
                            status_label = "🟡 中等"
                        else:
                            status_label = "🟢 正常"
                    except:
                        pass
                msg.append(f"\n📌 {status_label} {region} {name}".strip())
                if node.get('os'):
                    msg.append(f"   系统: {node.get('os')}")
                if cpu_pct is not None:
                    msg.append(f"   CPU: {cpu_pct}%")
                if node.get('ram_usage_percent') is not None:
                    msg.append(f"   内存: {node.get('ram_usage_percent')}% ({node.get('ram_used_gb', '-')}/{node.get('ram_total_gb', '-')} GB)")
                elif node.get('ram_total_gb') is not None:
                    msg.append(f"   内存: {node.get('ram_total_gb')} GB")
                if node.get('disk_usage_percent') is not None:
                    msg.append(f"   磁盘: {node.get('disk_usage_percent')}% ({node.get('disk_used_gb', '-')}/{node.get('disk_total_gb', '-')} GB)")
                elif node.get('disk_total_gb') is not None:
                    msg.append(f"   磁盘: {node.get('disk_total_gb')} GB")
                if node.get('net_up_str') or node.get('net_down_str'):
                    msg.append(f"   网络: ↑ {node.get('net_up_str', '-')} ↓ {node.get('net_down_str', '-')}")
                if node.get('load_1') is not None:
                    msg.append(f"   负载: {node.get('load_1')} / {node.get('load_5')} / {node.get('load_15')}")
                if node.get('uptime_str'):
                    msg.append(f"   运行: {node.get('uptime_str')}")
            yield event.plain_result("\n".join(msg))

    def _handle_text_output(self, event, nodes):
        msg = ["🖥️ **Komari 服务器状态**"]
        for node in nodes:
            name = node.get("name", "未知")
            os_name = node.get("os", "未知")
            cpu_name = node.get("cpu_name", "未知")
            cpu_cores = node.get("cpu_cores", "?")
            region = node.get("region", "")
            
            mem = node.get("mem_total", 0)
            disk = node.get("disk_total", 0)
            
            # Format bytes to GB
            mem_gb = mem / 1024 / 1024 / 1024
            disk_gb = disk / 1024 / 1024 / 1024
            
            status_icon = "🟢" if node.get("is_online", False) else "🔴"
            
            msg.append(f"\n📌 {status_icon} {region} {name}")
            msg.append(f"   系统: {os_name}")
            msg.append(f"   CPU: {cpu_name} ({cpu_cores} C)")
            msg.append(f"   内存: {mem_gb:.2f} GB")
            msg.append(f"   磁盘: {disk_gb:.2f} GB")
            
            # Updated at
            updated = node.get("updated_at_cn", "")
            if not updated:
                 updated = node.get("updated_at", "").replace("T", " ").replace("Z", "")
            
            if updated:
                msg.append(f"   更新: {updated}")
        
        return event.plain_result("\n".join(msg))

    async def _handle_image_output(self, event, nodes):
        if not self.template_str:
             return event.plain_result("未找到 HTML 模板文件。")
             
        try:
            # Prepare data and options
            data = {"nodes": nodes, "dark_theme": self.config.dark_theme}
            # 完全对齐 tmp-bot 的参数配置
            options = {
                "type": "jpeg",
                "quality": 92,
                "full_page": True,
                "omit_background": False
            }
            
            self.logger.info(f"HTML Render: 模板长度={len(self.template_str)}, Nodes数量={len(nodes)}")
            
            # Use AstrBot's built-in html_render method
            #以此处为例，务必使用 keyword argument 传递 options，避免位置参数错位
            img_url = await self.html_render(self.template_str, data, options=options)
            
            if img_url:
                return event.chain_result([Image.fromURL(img_url)])
            else:
                return event.plain_result("图片生成失败: 未返回图片 URL")
                    
        except Exception as e:
            self.logger.error(f"图片生成失败: {e}，回退到文本模式")
            return self._handle_text_output(event, nodes)
