"""BLE 心率传感器 — 连接小米手环 9 NFC，采集 HR/HRV。"""

import asyncio
import struct
import time
from dataclasses import dataclass
from typing import Optional

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from ..config import EdgeConfig

HR_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
HR_CHAR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

RR_WINDOW_SIZE = 10

# 已知的心率设备关键词（按优先级排序）
HR_KEYWORDS = ["xiaomi", "mi band", "mi smart", "polar", "hrm", "heart rate"]


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
        self._failed_addrs: set[str] = set()  # 连接失败的设备地址黑名单

    async def run(self):
        print("[BLE] Sensor started, scanning for devices...")

        # 如果配置了目标设备地址，先尝试通过 bluetoothctl 配对
        if self._config.ble_target_device:
            await self._pair_via_bluetoothctl(self._config.ble_target_device)

        while True:
            try:
                device = await self._find_device()
                if not device:
                    print("[BLE] No device found, retrying...")
                    await asyncio.sleep(self._config.ble_scan_interval)
                    continue
                print(f"[BLE] Connecting to {device.name} ({device.address})...")

                async with BleakClient(device) as client:
                    self._client = client
                    # 检查设备是否具备心率特征
                    if not await self._has_hr_characteristic(client):
                        print(f"[BLE] {device.address} has no HR characteristic, skipping")
                        self._failed_addrs.add(device.address)
                        await client.disconnect()
                        continue
                    await client.start_notify(HR_CHAR_UUID, self._on_hr_data)
                    print(f"[BLE] Connected to {device.name}, reading HR data...")
                    await self._wait_disconnect(client)
            except Exception as exc:
                print(f"[BLE] Error: {exc}")
                # 连接失败，尝试配对后再重试
                if self._config.ble_target_device and 'not paired' in str(exc).lower():
                    await self._pair_via_bluetoothctl(self._config.ble_target_device)
                await asyncio.sleep(5)

    async def _pair_via_bluetoothctl(self, address: str):
        """通过 bluetoothctl 配对待定设备。"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "bluetoothctl", "pair", address,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=15)
            # 配对后信任设备
            await asyncio.create_subprocess_exec(
                "bluetoothctl", "trust", address,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            print(f"[BLE] Paired with {address}")
        except Exception as e:
            print(f"[BLE] Pair attempt for {address}: {e}")

    async def _has_hr_characteristic(self, client: BleakClient) -> bool:
        """检查连接的设备是否暴露心率特征。"""
        try:
            # Bleak 3.x: services is a property, populated after connection
            for svc in client.services:
                if svc.uuid == HR_SERVICE_UUID:
                    for char in svc.characteristics:
                        if char.uuid == HR_CHAR_UUID:
                            return True
        except Exception:
            pass
        return False

    async def _find_device(self) -> Optional[BLEDevice]:
        target = self._config.ble_target_device
        if target:
            print(f"[BLE] Searching by target address: {target}")
            # 持续监听广播，不设超时，由外层循环控制重试
            device = await BleakScanner.find_device_by_filter(
                lambda d, a: d.address.upper() == target.upper(),
                timeout=300)
            if device:
                print(f"[BLE] Found target: {device.name} ({device.address})")
                return device
            print(f"[BLE] Target {target} not found in scan")
            return None

        # 1) 按心率服务 UUID 过滤（最准确）
        def hr_filter(device: BLEDevice, adv: AdvertisementData) -> bool:
            if device.address in self._failed_addrs:
                return False
            return HR_SERVICE_UUID in adv.service_uuids

        device = await BleakScanner.find_device_by_filter(hr_filter, timeout=8)
        if device:
            print(f"[BLE] Found by HR service: {device.name} ({device.address})")
            return device

        # 2) 按名称过滤（只匹配已知心率设备关键词，排除泛化词）
        print("[BLE] Scanning by name...")
        devices = await BleakScanner.discover(timeout=5)
        for d in devices:
            if d.address in self._failed_addrs:
                continue
            name = (d.name or "").lower()
            if any(kw in name for kw in HR_KEYWORDS):
                print(f"[BLE] Found by name: {d.name} ({d.address})")
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