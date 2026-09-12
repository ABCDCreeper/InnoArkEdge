"""InnoArkEdge — 边缘终端服务。"""

import asyncio

from .config import EdgeConfig
from .sensors import BLESensor, CameraSensor, RfidSensor
from .ws_server import WebSocketServer


async def create_edge_app(config: EdgeConfig) -> tuple[asyncio.Queue, WebSocketServer]:
    """创建传感器管道：BLE/Camera/RFID → Queue → WebSocket 广播。"""
    sensor_queue: asyncio.Queue = asyncio.Queue(maxsize=100)

    # 启动物理传感器协程
    sensors = [
        BLESensor(config, sensor_queue),
        CameraSensor(config, sensor_queue),
        RfidSensor(config, sensor_queue),
    ]
    for s in sensors:
        asyncio.create_task(s.run())

    # 启动 WebSocket 服务
    ws_server = WebSocketServer(config, sensor_queue)
    asyncio.create_task(ws_server.run())

    return sensor_queue, ws_server