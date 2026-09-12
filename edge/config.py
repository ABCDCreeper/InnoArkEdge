"""边缘终端配置。"""

import os
import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EdgeConfig:
    # 设备标识
    device_id: str = os.environ.get("INNOARK_DEVICE_ID", "pi4b-001")

    # BLE
    ble_scan_interval: int = 10          # 扫描间隔（秒）
    ble_aggregate_window: int = 5        # HR/HRV 聚合窗口（秒）
    ble_target_device: Optional[str] = os.environ.get("BLE_TARGET")

    # Camera
    camera_fps: int = 10
    camera_device: int = 0

    # RFID
    rfid_poll_interval: float = 0.5

    # MQTT
    mqtt_broker: str = os.environ.get("MQTT_BROKER", "")
    mqtt_port: int = int(os.environ.get("MQTT_PORT", "1883"))
    mqtt_topic_prefix: str = "innoark/edge"
    mqtt_reconnect_delay: int = 5

    # WebSocket
    ws_host: str = "127.0.0.1"
    ws_port: int = 8765

    # Flask
    flask_host: str = "127.0.0.1"
    flask_port: int = 5000

    # Database
    db_path: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "innoark.db"
    )

    @classmethod
    def load(cls, path: Optional[str] = None) -> "EdgeConfig":
        if path and os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            valid_keys = cls.__dataclass_fields__.keys()
            return cls(**{k: v for k, v in data.items() if k in valid_keys})
        return cls()