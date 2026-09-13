"""RFID 传感器 — PN532，I2C 模式。"""

import asyncio
import time
from dataclasses import dataclass
from typing import Optional

import smbus2

from ..config import EdgeConfig
from ..card_mapper import CardMapper


@dataclass
class RfidData:
    card_id: str
    timestamp: float
    name: str = ""
    emoji: str = ""
    action: str = ""
    content: str = ""


# ── PN532 I2C 驱动 ──────────────────────────────

_HOST_TFI = 0xD4
_RESP_TFI = 0xD5


class PN532I2C:
    """基于 smbus2 的 PN532 I2C 驱动。"""

    def __init__(self, bus: int = 1, address: int = 0x24):
        self._bus = smbus2.SMBus(bus)
        self._addr = address
        self._initialized = False

    # ── I2C 原语 ──────────────────────────────

    def _write(self, data):
        self._bus.i2c_rdwr(smbus2.i2c_msg.write(self._addr, data))

    def _read(self, n):
        msg = smbus2.i2c_msg.read(self._addr, n)
        self._bus.i2c_rdwr(msg)
        return list(msg)

    def _wait_status(self, timeout=1.0):
        """等 PN532 输出 0x01 状态字节（已就绪）。"""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                if self._read(1)[0] == 0x01:
                    return True
            except (OSError, IndexError):
                pass
            time.sleep(0.001)
        return False

    # ── 帧收发 ────────────────────────────────

    def _build_cmd_frame(self, cmd, params):
        data = [_HOST_TFI, cmd] + list(params)
        l = len(data)
        return [0x00, 0x00, 0xFF, l, (0x100 - l) & 0xFF] + data + \
               [(0x100 - sum(data)) & 0xFF, 0x00]

    def _read_ack(self):
        if not self._wait_status():
            raise TimeoutError("ACK not ready")
        raw = self._read(6)
        if raw[1:6] != [0x00, 0x00, 0xFF, 0x00, 0xFF]:
            raise RuntimeError(f"Bad ACK: {bytes(raw[1:6]).hex()}")
        return True

    def _read_once(self, timeout=1.0):
        """等就绪后一次性读取全部响应数据并解析。"""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self._wait_status(timeout=0.15):
                continue
            try:
                raw = self._read(32)
                if raw[0] != 0x01 or raw[1:4] != [0x00, 0x00, 0xFF]:
                    continue
                data_len = raw[4]
                if raw[5] != (0x100 - data_len) & 0xFF:
                    continue
                # 校验通过
                d = raw[6:6 + data_len]
                if raw[6 + data_len] != (0x100 - sum(d)) & 0xFF:
                    continue
                if raw[7 + data_len] != 0x00:
                    continue
                if d[0] != _RESP_TFI:
                    continue
                return list(d[1:])
            except:
                continue
        raise TimeoutError("Response timeout")

    def send_command(self, command, params=None):
        self._write(self._build_cmd_frame(command, params or []))
        self._read_ack()
        return self._read_once()

    # ── 高层 ──────────────────────────────────

    def sam_configuration(self):
        """SAM 配置：正常模式，超时 1 s。"""
        resp = self.send_command(0x14, [0x01, 0x14, 0x00])
        if resp[0] != 0x15:
            raise RuntimeError(f"SAM config failed: cmd=0x{resp[0]:02x}")
        self._initialized = True

    def read_passive_target(self, timeout=0.5):
        """尝试读卡一次，返回 UID bytes 或 None。"""
        if not self._initialized:
            self.sam_configuration()

        self._write(self._build_cmd_frame(0x4A, [0x01, 0x00]))
        self._read_ack()

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                resp = self._read_once(timeout=0.3)
                if resp[0] != 0x4B or resp[1] == 0:
                    return None
                # resp: [0x4B, nbTg, Tg, ATQA0, ATQA1, SAK, uid_len, uid...]
                uid_len = resp[6]
                return bytes(resp[7:7 + uid_len])
            except (TimeoutError, RuntimeError, OSError):
                continue
        return None

    def close(self):
        try:
            self._bus.close()
        except Exception:
            pass


# ── RfidSensor ──────────────────────────────────


class RfidSensor:
    """PN532 RFID 传感器，异步轮询检测卡片。"""

    def __init__(self, config: EdgeConfig, queue: asyncio.Queue):
        self._config = config
        self._queue = queue
        self._pn532: Optional[PN532I2C] = None
        self._last_card_id: Optional[str] = None
        self._last_card_time: float = 0
        self._card_map = CardMapper()

    async def run(self):
        print("[RFID] PN532 I2C sensor started")
        await asyncio.sleep(1)  # 等 I2C 总线稳定
        retry_delay = 1
        while True:
            try:
                self._pn532 = PN532I2C()
                self._pn532.sam_configuration()
                retry_delay = 1
                print("[RFID] PN532 initialized, waiting for cards...")
                await self._poll_loop()
            except OSError as exc:
                print(f"[RFID] I2C error (retry {retry_delay}s): {exc}")
            except Exception as exc:
                print(f"[RFID] Error (retry {retry_delay}s): {exc}")
                import traceback
                traceback.print_exc()
            finally:
                if self._pn532:
                    self._pn532.close()
                    self._pn532 = None
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 30)

    async def _poll_loop(self):
        """持续轮询卡片。"""
        while self._pn532:
            try:
                uid = await asyncio.get_event_loop().run_in_executor(
                    None, self._pn532.read_passive_target, 0.5
                )
                if uid:
                    card_id = uid.hex().upper()
                    now = time.time()
                    if card_id != self._last_card_id or now - self._last_card_time > 3:
                        self._last_card_id = card_id
                        self._last_card_time = now

                        # 查卡片映射
                        info = self._card_map.lookup(card_id)
                        if info:
                            print(f"[RFID] {info['name']} (card {card_id})")
                        else:
                            print(f"[RFID] New card: {card_id}")

                        await self._queue.put({
                            "type": "sensor",
                            "sensor": "rfid",
                            "data": RfidData(
                                card_id=card_id,
                                timestamp=now,
                                name=info.get("name", "") if info else "",
                                emoji=info.get("emoji", "") if info else "",
                                action=info.get("action", "") if info else "",
                                content=info.get("content", "") if info else "",
                            )
                        })
                else:
                    await asyncio.sleep(0.1)
            except Exception as exc:
                print(f"[RFID] Poll error: {exc}")
                await asyncio.sleep(1)

    async def stop(self):
        if self._pn532:
            self._pn532.close()
            self._pn532 = None