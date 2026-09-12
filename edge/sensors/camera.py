"""摄像头传感器 — OpenCV Haar Cascade 人脸检测 + 注意力评分。"""

import asyncio
import time
from dataclasses import dataclass
from typing import Optional

import cv2

from ..config import EdgeConfig


@dataclass
class AttentionData:
    face_count: int
    attention_score: float  # 0.0 - 1.0
    timestamp: float


class CameraSensor:
    def __init__(self, config: EdgeConfig, queue: asyncio.Queue):
        self._config = config
        self._queue = queue
        self._cap: Optional[cv2.VideoCapture] = None
        self._cascade: Optional[cv2.CascadeClassifier] = None

    async def run(self):
        self._cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self._cap = cv2.VideoCapture(self._config.camera_device)
        if not self._cap.isOpened():
            print("[Camera] Cannot open camera, retrying...")
            await asyncio.sleep(5)
            continue

        interval = 1.0 / self._config.camera_fps
        while True:
            ret, frame = self._cap.read()
            if not ret:
                await asyncio.sleep(interval)
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self._cascade.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))

            face_count = len(faces)
            attention = self._score_attention(faces, frame.shape)

            await self._queue.put({
                "type": "sensor",
                "sensor": "camera",
                "data": AttentionData(face_count=face_count, attention_score=attention, timestamp=time.time())
            })

            await asyncio.sleep(interval)

    def _score_attention(self, faces: list, frame_shape: tuple) -> float:
        if len(faces) == 0:
            return 0.0
        h, w = frame_shape[:2]
        cx, cy = w / 2, h / 2
        scores = []
        for (x, y, fw, fh) in faces:
            face_cx = x + fw / 2
            face_cy = y + fh / 2
            dx = abs(face_cx - cx) / cx
            dy = abs(face_cy - cy) / cy
            dist_score = max(0, 1.0 - (dx + dy) / 2)
            size_score = min(1.0, (fw * fh) / (w * h * 0.3))
            scores.append(dist_score * 0.6 + size_score * 0.4)
        return round(sum(scores) / len(scores), 2)

    async def stop(self):
        if self._cap and self._cap.isOpened():
            self._cap.release()