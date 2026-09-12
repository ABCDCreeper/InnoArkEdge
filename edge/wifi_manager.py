"""WiFi 管理 — 基于 nmcli 命令封装。"""

import asyncio
import re
from typing import Optional


class WiFiManager:
    async def scan(self) -> list[dict]:
        proc = await asyncio.create_subprocess_exec(
            "nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        networks = []
        for line in stdout.decode().strip().split("\n"):
            if not line:
                continue
            parts = line.split(":")
            if len(parts) >= 3:
                networks.append({
                    "ssid": parts[0],
                    "signal": int(parts[1]) if parts[1].isdigit() else 0,
                    "security": parts[2],
                })
        return networks

    async def connect(self, payload: dict) -> dict:
        ssid = payload.get("ssid", "")
        password = payload.get("password", "")
        mode = payload.get("mode", "dhcp")

        cmd = ["nmcli", "dev", "wifi", "connect", ssid]
        if password:
            cmd.extend(["password", password])
        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.wait()

        if mode == "static":
            ip = payload.get("ip", "")
            mask = payload.get("mask", "24")
            gateway = payload.get("gateway", "")
            con_name = ssid
            cmds = [
                ["nmcli", "con", "mod", con_name, "ipv4.method", "manual"],
                ["nmcli", "con", "mod", con_name, "ipv4.addresses", f"{ip}/{mask}"],
            ]
            if gateway:
                cmds.append(["nmcli", "con", "mod", con_name, "ipv4.gateway", gateway])
            for c in cmds:
                p = await asyncio.create_subprocess_exec(*c)
                await p.wait()

        status = await self.status()
        return {"success": status.get("connected", False), "ssid": ssid, **status}

    async def status(self) -> dict:
        proc = await asyncio.create_subprocess_exec(
            "nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "dev",
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        for line in stdout.decode().strip().split("\n"):
            parts = line.split(":")
            if len(parts) >= 4 and parts[1] == "wifi" and parts[2] == "connected":
                return {"connected": True, "ssid": parts[3], "ip": ""}
        return {"connected": False, "ssid": "", "ip": ""}

    async def disconnect(self) -> dict:
        status = await self.status()
        if status.get("ssid"):
            proc = await asyncio.create_subprocess_exec(
                "nmcli", "con", "down", status["ssid"]
            )
            await proc.wait()
        return {"success": True}