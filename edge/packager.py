"""数据打包 — 将传感器数据封装为统一 JSON 格式。"""

import json
import time
import uuid
from typing import Any

from .config import EdgeConfig


def make_packet(sensor_type: str, payload: Any, config: EdgeConfig) -> str:
    packet = {
        "header": {
            "packet_id": str(uuid.uuid4())[:8],
            "device_id": config.device_id,
            "timestamp": time.time(),
            "sensor_type": sensor_type,
        },
        "payload": payload,
    }
    return json.dumps(packet)