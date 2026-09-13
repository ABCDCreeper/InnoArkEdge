"""WebSocket 服务 — 推送传感器数据 + 响应 WiFi/BT 命令。"""

import asyncio
import json
import time
from typing import Any

from aiohttp import web, web_ws

from .config import EdgeConfig
from .wifi_manager import WiFiManager
from .bt_manager import BTManager
from .card_mapper import CardMapper


SENSOR_TIMEOUT = 15  # 超过此秒数无数据视为断开


class WebSocketServer:
    def __init__(self, config: EdgeConfig, sensor_queue: asyncio.Queue):
        self._config = config
        self._sensor_queue = sensor_queue
        self._clients: set[web.WebSocketResponse] = set()
        self._sensor_last_seen: dict[str, float] = {}
        self._wifi = WiFiManager()
        self._bt = BTManager()
        self._card = CardMapper()
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

        # 连接后立即推送当前传感器状态
        try:
            await ws.send_json({
                "event": "sensor_status",
                "payload": self._get_sensor_status(),
            })
        except Exception:
            pass

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
            "card_list": lambda: self._card.all_cards(),
            "card_register": lambda: self._register_card(payload),
            "card_delete": lambda: self._delete_card(payload),
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
            "card_list": "card_list",
            "card_register": "card_result",
            "card_delete": "card_result",
        }

        handler = handlers.get(action)
        if handler:
            try:
                result = await handler()
                await ws.send_json({"event": event_map.get(action, action), "payload": result})
            except Exception as exc:
                print(f"[WS] Command error {action}: {exc}")
                await ws.send_json({"event": "error", "payload": f"{action} failed: {exc}"})
        else:
            await ws.send_json({"event": "error", "payload": f"Unknown cmd: {action}"})

    def _get_sensor_status(self) -> dict[str, str]:
        now = time.time()
        return {
            sensor: "connected" if self._sensor_last_seen.get(sensor, 0) > now - SENSOR_TIMEOUT else "disconnected"
            for sensor in ("ble", "camera", "rfid")
        }

    async def _broadcast_loop(self):
        while True:
            data = await self._sensor_queue.get()
            if not self._clients:
                continue

            # 记录传感器最近活跃时间
            self._sensor_last_seen[data["sensor"]] = time.time()

            payload = data["data"]
            if hasattr(payload, "__dataclass_fields__"):
                payload = {k: getattr(payload, k) for k in payload.__dataclass_fields__}

            message = json.dumps({
                "event": "sensor_data",
                "payload": payload,
                "sensor": data["sensor"],
                "timestamp": time.time(),
            })
            status_msg = json.dumps({
                "event": "sensor_status",
                "payload": self._get_sensor_status(),
            })

            disconnected = set()
            for ws in self._clients:
                try:
                    await ws.send_str(message)
                    await ws.send_str(status_msg)
                except Exception:
                    disconnected.add(ws)
            self._clients -= disconnected

    def _register_card(self, payload: dict) -> dict:
        uid = payload.get("uid", "")
        info = {k: v for k, v in payload.items() if k in ("name", "emoji", "action", "content")}
        if not uid or not info:
            return {"ok": False, "error": "missing uid or card info"}
        self._card.register(uid, info)
        print(f"[Card] Registered: {uid} → {info.get('name', '?')}")
        return {"ok": True}

    def _delete_card(self, payload: dict) -> dict:
        uid = payload.get("uid", "")
        if not uid:
            return {"ok": False, "error": "missing uid"}
        self._card.delete(uid)
        print(f"[Card] Deleted: {uid}")
        return {"ok": True}