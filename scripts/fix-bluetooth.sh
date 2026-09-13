#!/bin/bash
# 蓝牙开启脚本 - 解决 rfkill 阻塞问题
set -e

echo "[Fix] Unblocking Bluetooth..."

# 解除 rfkill 阻塞
sudo rfkill unblock bluetooth || true

# 开启蓝牙电源
bluetoothctl power on || true

# 设置默认可信任（可选）
bluetoothctl discoverable on || true
bluetoothctl pairable on || true

echo "[Fix] Bluetooth enabled successfully"
bluetoothctl show | grep -E "(Powered|Discoverable|Pairable)"
