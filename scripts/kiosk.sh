#!/bin/bash
# InnoArk Kiosk 启动脚本（通过 startx 调用）
export DISPLAY=:0

# 关闭屏保
xset s off 2>/dev/null || true
xset -dpms 2>/dev/null || true
xset s noblank 2>/dev/null || true

# 启动 unclutter 和 chromium（全屏）
unclutter -idle 0 &
exec chromium --kiosk \
  --no-first-run \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --touch-events=enabled \
  --check-for-update-interval=604800 \
  --start-maximized \
  --window-size=1920,1080 \
  --no-sandbox \
  --disable-features=TranslateUI \
  --lang=zh-CN \
  --remote-debugging-port=9222 \
  --enable-logging=stderr \
  --v=1 \
  http://localhost 2>/tmp/chromium.log