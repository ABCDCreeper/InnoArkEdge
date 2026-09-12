#!/usr/bin/env python3
"""InnoArkEdge 统一入口 — 同时运行 Flask + 传感器管道 + WebSocket。"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aiohttp import web
from aiohttp_wsgi import WSGIHandler

from edge.config import EdgeConfig
from edge import create_edge_app
from backend.app import create_app as create_flask_app


async def main():
    config = EdgeConfig.load()

    # 创建 Flask WSGI 应用
    flask_app = create_flask_app()
    wsgi_handler = WSGIHandler(flask_app)

    # 创建传感器管道 + WebSocket
    await create_edge_app(config)

    # 使用单个 aiohttp server 承载 Flask
    app = web.Application()
    app.router.add_route("*", "/api{tail:.*}", wsgi_handler)
    app.router.add_route("*", "/api/", wsgi_handler)
    # WebSocket 由 edge/ws_server.py 自行启动独立端口 :8765
    # nginx 将 /ws 代理到该端口

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.flask_host, config.flask_port)
    await site.start()
    print(f"[Main] Flask API on {config.flask_host}:{config.flask_port}")

    # 保持运行
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())