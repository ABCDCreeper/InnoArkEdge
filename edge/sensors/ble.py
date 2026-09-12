"""BLE 心率传感器 — 连接 Samsung Watch6，采集 HR/HRV。"""

import asyncio
import struct
import time
from dataclasses import dataclass
from typing import Optional

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice

from ..config import EdgeConfig

HR_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
HR_CHAR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

RR_WINDOW_SIZE = 10


@dataclass
class HeartRateData:
    hr: int
    hrv: float  # RMSSD
    rr_intervals: list[int]
    timestamp: float


class BLESensor:
    def __init__(self, config: EdgeConfig, queue: asyncio.Queue):
        self._config = config
        self._queue = queue
        self._client: Optional[BleakClient] = None
        self._lock = asyncio.Lock()
        self._rr_buffer: list[int] = []
        self._last_push = 0.0

    async def run(self):
        while True:
            try:
                device = await self._find_device()
                if not device:
                    await asyncio.sleep(self._config.ble_scan_interval)
                    continue

                async with BleakClient(device) as client:
                    self._client = client
                    await client.start_notify(HR_CHAR_UUID, self._on_hr_data)
                    await self._wait_disconnect(client)
            except Exception as exc:
                print(f"[BLE] Error: {exc}")
                await asyncio.sleep(5)

    async def _find_device(self) -> Optional[BLEDevice]:
        target = self._config.ble_target_device
        if target:
            return await BleakScanner.find_device_by_address(target)
        devices = await BleakScanner.discover(timeout=5)
        for d in devices:
            if "watch" in (d.name or "").lower() or "galaxy" in (d.name or "").lower():
                return d
        return None

    def _on_hr_data(self, _sender: int, data: bytearray):
        hr = data[1]
        rr_intervals = []
        offset = 2
        while offset + 2 <= len(data):
            rr = struct.unpack("<H", data[offset:offset + 2])[0]
            rr_intervals.append(rr)
            offset += 2

        async def push():
            async with self._lock:
                self._rr_buffer.extend(rr_intervals)
                if len(self._rr_buffer) > RR_WINDOW_SIZE:
                    self._rr_buffer = self._rr_buffer[-RR_WINDOW_SIZE:]

            now = time.time()
            if now - self._last_push >= self._config.ble_aggregate_window:
                hrv = self._calc_hrv()
                self._last_push = now
                await self._queue.put({
                    "type": "sensor",
                    "sensor": "ble",
                    "data": HeartRateData(hr=hr, hrv=hrv, rr_intervals=list(self._rr_buffer), timestamp=now)
                })

        asyncio.ensure_future(push())

    async def _wait_disconnect(self, client: BleakClient):
        while client.is_connected:
            await asyncio.sleep(1)

    def _calc_hrv(self) -> float:
        if len(self._rr_buffer) < 2:
            return 0.0
        diffs = [abs(self._rr_buffer[i] - self._rr_buffer[i - 1]) for i in range(1, len(self._rr_buffer))]
        rmsdd = (sum(d * d for d in diffs) / len(diffs)) ** 0.5
        return round(rmsdd, 2)

    async def stop(self):
        if self._client and self._client.is_connected:
            await self._client.disconnect()