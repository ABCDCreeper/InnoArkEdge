#!/bin/bash
# InnoArkEdge 树莓派安装脚本
set -e

INSTALL_DIR=/opt/innoark-edge
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "[Install] Installing InnoArkEdge to $INSTALL_DIR..."

# 1. 系统依赖
sudo apt update
sudo apt install -y \
  xserver-xorg-core xinit xinput unclutter \
  chromium-browser nginx \
  network-manager bluez bluetooth python3-venv python3-pip

# 2. 复制代码并修复权限（nginx 需要读取 dist/）
sudo mkdir -p "$INSTALL_DIR"
sudo cp -r "$REPO_DIR/frontend/dist" "$INSTALL_DIR/frontend/dist"
sudo chmod -R 755 "$INSTALL_DIR/frontend/dist"
sudo chown -R www-data:www-data "$INSTALL_DIR/frontend/dist"
sudo cp -r "$REPO_DIR/backend" "$INSTALL_DIR/backend"
sudo cp -r "$REPO_DIR/edge" "$INSTALL_DIR/edge"
sudo cp "$REPO_DIR/main.py" "$INSTALL_DIR/main.py"
sudo cp "$REPO_DIR/requirements.txt" "$INSTALL_DIR/requirements.txt"
sudo cp -r "$REPO_DIR/nginx" "$INSTALL_DIR/nginx"
sudo cp -r "$REPO_DIR/scripts" "$INSTALL_DIR/scripts"

# 3. 创建虚拟环境
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# 4. nginx
sudo cp "$INSTALL_DIR/nginx/innoark.conf" /etc/nginx/sites-available/innoark
sudo ln -sf /etc/nginx/sites-available/innoark /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl restart nginx

# 5. systemd
sudo cp "$INSTALL_DIR/scripts/innoark-edge.service" /etc/systemd/system/
sudo cp "$INSTALL_DIR/scripts/innoark-kiosk.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable innoark-edge innoark-kiosk

# 6. 数据目录
sudo mkdir -p "$INSTALL_DIR/data"

echo "[Install] Done! Reboot to start: sudo reboot"