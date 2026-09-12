"""WebSocket 服务 — 推送传感器数据 + 响应 WiFi/BT 命令。"""

import asyncio
import json
import time
from typing import Any

from aiohttp import web, web_ws

from .config import EdgeConfig
from .wifi_manager import WiFiManager
from .bt_manager import BTManager


class WebSocketServer:
    def __init__(self, config: EdgeConfig, sensor_queue: asyncio.Queue):
        self._config = config
        self._sensor_queue = sensor_queue
        self._clients: set[web.WebSocketResponse] = set()
        self._wifi = WiFiManager()
        self._bt = BTManager()
        self._app = web.Application()
        self._app.router.add_get("/ws", self._handle_ws)

    async def run(self):
        runner = web.AppRunner(self._app)
        await runner.setup()
        site = web.TCPSite(runner, self._config.ws_host, self._config.ws_port)
        await site.start()
        print(f"[WS] Server started on {self._config.ws_host}:{self._config.ws_port}")

        await self._broadcast_loop()

    async def _handle_ws(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(heartbeat=30.0)
        await ws.prepare(request)
        self._clients.add(ws)
        print(f"[WS] Client connected ({len(self._clients)} total)")

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    await self._handle_command(ws, json.loads(msg.data))
                elif msg.type == web.WSMsgType.ERROR:
                    print(f"[WS] Error: {ws.exception()}")
        finally:
            self._clients.discard(ws)
            print(f"[WS] Client disconnected ({len(self._clients)} total)")

        return ws

    async def _handle_command(self, ws: web.WebSocketResponse, cmd: dict):
        action = cmd.get("cmd", "")
        payload = cmd.get("payload", {})

        handlers = {
            "wifi_scan": self._wifi.scan,
            "wifi_connect": lambda: self._wifi.connect(payload),
            "wifi_status": self._wifi.status,
            "wifi_disconnect": self._wifi.disconnect,
            "bt_scan": self._bt.scan,
            "bt_pair": lambda: self._bt.pair(payload.get("address", "")),
            "bt_connect": lambda: self._bt.connect(payload.get("address", "")),
            "bt_disconnect": self._bt.disconnect,
            "bt_status": self._bt.status,
        }

        # 事件名映射（匹配前端 store 的 handleMessage 期望）
        event_map = {
            "wifi_scan": "wifi_networks",
            "wifi_connect": "wifi_result",
            "wifi_disconnect": "wifi_result",
            "bt_scan": "bt_devices",
            "bt_pair": "bt_result",
            "bt_connect": "bt_result",
            "bt_disconnect": "bt_result",
        }

        handler = handlers.get(action)
        if handler:
            result = await handler()
            await ws.send_json({"event": event_map.get(action, action), "payload": result})
        else:
            await ws.send_json({"event": "error", "payload": f"Unknown cmd: {action}"})

    async def _broadcast_loop(self):
        while True:
            data = await self._sensor_queue.get()
            if not self._clients:
                continue

            payload = data["data"]
            if hasattr(payload, "__dataclass_fields__"):
                payload = {k: getattr(payload, k) for k in payload.__dataclass_fields__}

            message = json.dumps({
                "event": "sensor_data",
                "payload": payload,
                "sensor": data["sensor"],
                "timestamp": time.time(),
            })

            disconnected = set()
            for ws in self._clients:
                try:
                    await ws.send_str(message)
                except Exception:
                    disconnected.add(ws)
            self._clients -= disconnected