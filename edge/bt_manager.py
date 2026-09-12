"""蓝牙管理 — 基于 bluetoothctl 封装蓝牙扫描/配对/连接。"""

import asyncio
import re
from typing import Optional


class BTManager:
    async def scan(self) -> list[dict]:
        proc = await asyncio.create_subprocess_exec(
            "bluetoothctl", "--", "scan", "on",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        except asyncio.TimeoutError:
            proc.kill()
            stdout, _ = await proc.communicate()

        devices = []
        for line in stdout.decode().strip().split("\n"):
            m = re.search(r"Device\s+([0-9A-Fa-f:]+)\s+(.*)", line)
            if m:
                devices.append({"address": m.group(1), "name": m.group(2).strip()})
        return devices

    async def pair(self, address: str) -> dict:
        proc = await asyncio.create_subprocess_exec(
            "bluetoothctl", "pair", address,
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        success = "Pairing successful" in stdout.decode()
        return {"success": success, "address": address}

    async def connect(self, address: str) -> dict:
        proc = await asyncio.create_subprocess_exec(
            "bluetoothctl", "connect", address,
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        success = "Connection successful" in stdout.decode()
        return {"success": success, "address": address}

    async def disconnect(self) -> dict:
        proc = await asyncio.create_subprocess_exec("bluetoothctl", "disconnect")
        await proc.wait()
        return {"success": True}

    async def status(self) -> dict:
        proc = await asyncio.create_subprocess_exec(
            "bluetoothctl", "show",
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode()
        return {
            "powered": "Powered: yes" in output,
            "discovering": "Discovering: yes" in output,
        }