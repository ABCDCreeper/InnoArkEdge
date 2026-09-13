# InnoArkEdge

树莓派边缘终端，采集传感器数据并通过 WebSocket 推送到 InnoArk 前端。

## 架构

```
传感器层 (edge/sensors/)
  ├── ble.py      — BLE 心率传感器（小米手环 9）
  ├── camera.py   — 摄像头人脸检测 + 注意力评分
  └── rfid.py     — PN532 I2C RFID 读卡器

通信层
  ├── bt_manager.py  — bluetoothctl 会话管理（配对/连接）
  └── ws_server.py   — WebSocket 服务（推送传感器数据、响应命令）

后端 API (backend/)
  └── app/ — Flask REST API（认证、学习课程）

前端 (frontend/)
  └── Vue 3 + Pinia 单页应用（WebSocket 接收传感器数据）
```

## 传感器

| 传感器 | 硬件 | 数据 |
|--------|------|------|
| BLE 心率 | 小米手环 9 NFC | HR (bpm)、HRV (ms)、RR 间隔 |
| 摄像头 | USB 摄像头 | 人脸数、注意力评分 |
| RFID | PN532 (I2C) | 卡片 UID → 学习主题映射 |

## 部署

```bash
# 安装依赖
pip install -r requirements.txt

# 配置（可选）
echo 'BLE_TARGET=C1:43:DD:D8:69:CB' | sudo tee -a /etc/default/innoark-edge

# 运行
python main.py

# 或作为 systemd 服务
sudo cp scripts/innoark-edge.service /etc/systemd/system/
sudo systemctl enable --now innoark-edge
```

## Kiosk 模式

树莓派接显示器后启动全屏 Chrome：

```bash
sudo cp scripts/innoark-kiosk.service /etc/systemd/system/
sudo systemctl enable --now innoark-kiosk
```

## 前端构建

```bash
cd frontend
yarn install
yarn build       # 输出到 frontend/dist/
```

## 协议

传感器数据通过 WebSocket (`ws://host/ws`) 推送，格式：

```json
{"event": "sensor_data", "payload": {"hr": 72, "hrv": 38.5, "attention": 0.65, "faceCount": 1, "rfidCard": null}}
{"event": "sensor_status", "payload": {"ble": "connected", "camera": "demo", "rfid": "demo"}}
```