"""MQTT 发送器 — 带 SQLite 离线缓冲。"""

import asyncio
import json
import sqlite3
import os
import time

from .config import EdgeConfig


class Sender:
    """MQTT 发送器 — 带 SQLite 离线缓冲。

    注意：当前尚未接入主流水线（edge/__init__.py 的 create_edge_app），
    传感器数据目前仅通过 WebSocket 广播。后续如需启用 MQTT 上传，
    需要在 create_edge_app 中创建 Sender 实例并从传感器队列消费。
    """

    def __init__(self, config: EdgeConfig, input_queue: asyncio.Queue):
        self._config = config
        self._input_queue = input_queue
        self._mqtt = None
        self._sensor_type = "sensor"
        self._db_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data", "buffer.db"
        )

    async def run(self):
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._init_db()

        while True:
            packet = await self._input_queue.get()
            sent = await self._send_mqtt(packet)
            if sent:
                self._flush_buffer()
            else:
                self._buffer_packet(packet)
                await asyncio.sleep(5)

    def _init_db(self):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS buffer (id INTEGER PRIMARY KEY, packet TEXT, ts REAL)"
            )

    def _buffer_packet(self, packet: str):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("INSERT INTO buffer (packet, ts) VALUES (?, ?)", (packet, time.time()))

    def _flush_buffer(self):
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute("SELECT id, packet FROM buffer ORDER BY id").fetchall()
            for row_id, pkt in rows:
                if not self._mqtt or not self._mqtt.is_connected():
                    break
                self._mqtt.publish(self._topic(), pkt)
                conn.execute("DELETE FROM buffer WHERE id = ?", (row_id,))

    def _topic(self) -> str:
        return f"{self._config.mqtt_topic_prefix}/{self._config.device_id}/{self._sensor_type}"

    async def _send_mqtt(self, packet: str) -> bool:
        try:
            import asyncio_mqtt as mqtt
            if not self._mqtt:
                self._mqtt = mqtt.Client(
                    self._config.mqtt_broker,
                    port=self._config.mqtt_port,
                )
                await self._mqtt.connect()
            await self._mqtt.publish(self._topic(), packet)
            return True
        except Exception:
            return False