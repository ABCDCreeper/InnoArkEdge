"""蓝牙管理 — 基于 bluetoothctl 封装蓝牙扫描/配对/连接。"""

import asyncio
import re
from typing import Optional

# ANSI 转义码正则
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


class BTManager:
    async def scan(self) -> list[dict]:
        # 1. 打开蓝牙电源
        await self._run_cmd("power", "on")

        # 2. 开始后台扫描以发现新设备
        #    bluetoothctl scan on 在非交互模式下可能立即退出（仅触发 DBus 扫描），
        #    也可能持续运行，故需同时处理这两种情况
        scan_proc = await asyncio.create_subprocess_exec(
            "bluetoothctl", "scan", "on",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.sleep(10)
        try:
            scan_proc.kill()
            await scan_proc.wait()
        except ProcessLookupError:
            pass  # 进程已自行退出

        # 3. 从 bluetoothctl devices 读取已发现设备列表
        #    bluetoothctl scan on 在非交互式 shell 中不输出设备行，
        #    但 bluetoothd 会在后台缓存发现结果，用 devices 命令获取
        output = await self._run_cmd("devices")
        output = _ANSI_RE.sub("", output)  # 清除 ANSI 转义码
        devices = []
        for line in output.strip().split("\n"):
            m = re.search(r"Device\s+([0-9A-Fa-f:]+)\s+(.*)", line)
            if m:
                devices.append({"address": m.group(1), "name": m.group(2).strip()})
        return devices

    async def _run_cmd(self, *args: str) -> str:
        proc = await asyncio.create_subprocess_exec(
            "bluetoothctl", *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode()

    async def _bt_session(self, *commands: str, timeout: int = 60) -> str:
        """在单个 bluetoothctl 会话中依次执行多条命令，返回全部输出。"""
        proc = await asyncio.create_subprocess_exec(
            "bluetoothctl",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            stdin_data = "\n".join(commands) + "\n"
            stdout, _ = await asyncio.wait_for(
                proc.communicate(stdin_data.encode()),
                timeout=timeout,
            )
            return stdout.decode()
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return ""

    async def pair(self, address: str) -> dict:
        """配对设备：先设置 agent，再执行配对，最后 trust。"""
        output = await self._bt_session(
            "power on",
            "agent on",
            "default-agent",
            f"pair {address}",
            f"trust {address}",
            timeout=30,
        )
        output = _ANSI_RE.sub("", output)
        success = (
            "Pairing successful" in output
            or "Paired: yes" in output
            or "Pairing complete" in output
        )
        print(f"[BT] Pair result for {address}: success={success}")
        if not success:
            print(f"[BT] Pair output: {output[:500]}")
        return {"success": success, "address": address}

    async def connect(self, address: str) -> dict:
        """连接设备：先 trust 再 connect。"""
        output = await self._bt_session(
            "power on",
            "agent on",
            "default-agent",
            f"trust {address}",
            f"connect {address}",
            timeout=30,
        )
        output = _ANSI_RE.sub("", output)
        # bluetoothctl 连接成功后输出 "Connection successful"
        # 某些设备输出 "Connected: yes" 或类似信息
        success = (
            "Connection successful" in output
            or "Connected: yes" in output
        )
        print(f"[BT] Connect result for {address}: success={success}")
        if not success:
            print(f"[BT] Connect output: {output[:500]}")
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