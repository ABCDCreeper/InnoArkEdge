#!/bin/bash
# InnoArk Kiosk 启动脚本（通过 startx 调用）
export DISPLAY=:0

# 关闭屏保
xset s off 2>/dev/null || true
xset -dpms 2>/dev/null || true
xset s noblank 2>/dev/null || true

# 启动 unclutter 和 chromium
unclutter -idle 0 &
exec chromium --kiosk --no-first-run --disable-infobars --disable-session-crashed-bubble --touch-events=enabled --check-for-update-interval=604800 http://localhost