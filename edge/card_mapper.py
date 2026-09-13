"""卡片-主题映射 — 将 RFID 卡片 UID 映射为学习主题/互动内容。"""

import json
import os
from typing import Optional

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_DEFAULT_MAP = {
    "0AACA09B": {
        "name": "数学探险",
        "emoji": "🔢",
        "action": "quiz",
        "content": "二次函数与抛物线"
    },
    "DEADBEEF": {
        "name": "英语乐园",
        "emoji": "📖",
        "action": "quiz",
        "content": "英语词汇闯关"
    },
    "CAFEBABE": {
        "name": "科学实验室",
        "emoji": "🔬",
        "action": "experiment",
        "content": "物理小实验"
    },
    "12345678": {
        "name": "历史探索",
        "emoji": "🏛️",
        "action": "story",
        "content": "历史故事时间"
    },
    "87654321": {
        "name": "编程挑战",
        "emoji": "💻",
        "action": "challenge",
        "content": "Scratch 编程小挑战"
    }
}


def _load_card_map() -> dict:
    path = os.path.join(_DATA_DIR, "cards.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_card_map(data: dict):
    os.makedirs(_DATA_DIR, exist_ok=True)
    path = os.path.join(_DATA_DIR, "cards.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class CardMapper:
    """管理卡片 UID → 学习主题的映射。"""

    def __init__(self):
        self._user_map = _load_card_map()
        # 合并内置默认映射（用户映射优先级高）
        self._map = {**_DEFAULT_MAP, **self._user_map}

    def lookup(self, uid: str) -> Optional[dict]:
        """根据 UID 查询卡片信息。"""
        return self._map.get(uid)

    def is_known(self, uid: str) -> bool:
        return uid in self._map

    def register(self, uid: str, info: dict):
        self._map[uid] = info
        self._user_map[uid] = info
        _save_card_map(self._user_map)

    def all_cards(self) -> dict:
        return dict(self._map)

    def delete(self, uid: str):
        if uid in self._user_map:
            del self._user_map[uid]
            _save_card_map(self._user_map)
        self._map.pop(uid, None)