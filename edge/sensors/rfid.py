"""RFID 传感器 — ProxMark3 Easy，串口自动检测。"""

import asyncio
import time
import serial.tools.list_ports
from dataclasses import dataclass
from typing import Optional

from ..config import EdgeConfig


@dataclass
class RfidData:
    card_id: str
    timestamp: float


class RfidSensor:
    def __init__(self, config: EdgeConfig, queue: asyncio.Queue):
        self._config = config
        self._queue = queue
        self._serial: Optional[serial.Serial] = None

    async def run(self):
        while True:
            try:
                port = self._find_port()
                if not port:
                    await asyncio.sleep(3)
                    continue

                self._serial = serial.Serial(port, 115200, timeout=1)
                self._serial.write(b"hw search\r")
                await self._read_loop()
            except Exception as exc:
                print(f"[RFID] Error: {exc}")
                await asyncio.sleep(3)

    def _find_port(self) -> Optional[str]:
        for p in serial.tools.list_ports.comports():
            if "proxmark" in (p.description or "").lower() or "pm3" in (p.product or "").lower():
                return p.device
        return None

    async def _read_loop(self):
        while self._serial and self._serial.is_open:
            if self._serial.in_waiting > 0:
                line = self._serial.readline().decode(errors="ignore").strip()
                if line and self._is_card_id(line):
                    await self._queue.put({
                        "type": "sensor",
                        "sensor": "rfid",
                        "data": RfidData(card_id=line, timestamp=time.time())
                    })
            await asyncio.sleep(self._config.rfid_poll_interval)

    async def stop(self):
        if self._serial and self._serial.is_open:
            self._serial.close()

    @staticmethod
    def _is_card_id(text: str) -> bool:
        return len(text) in (8, 14) and all(c in "0123456789abcdefABCDEF" for c in text)