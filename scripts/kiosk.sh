#!/bin/bash
# InnoArk Kiosk 启动脚本
xset s off
xset -dpms
xset s noblank
unclutter -idle 0 &

chromium-browser --kiosk \
  --no-first-run \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --touch-events=enabled \
  --check-for-update-interval=604800 \
  http://localhost