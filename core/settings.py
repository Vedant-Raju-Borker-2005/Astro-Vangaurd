import os
import json
from dataclasses import dataclass, field
from typing import List, Dict
import time
from core.constants import Difficulty, SAVE_PATH

@dataclass
class GameSettings:
    difficulty: Difficulty = Difficulty.NORMAL
    music_volume: float  = 0.5
    sfx_volume: float    = 0.8
    show_fps: bool       = False
    high_score: int      = 0
    high_score_table: List[Dict] = field(default_factory=list)
    aim_assist: bool     = False

    def save(self, filename="settings.json"):
        data = {
            "difficulty":        self.difficulty.value,
            "music_volume":      self.music_volume,
            "sfx_volume":        self.sfx_volume,
            "show_fps":          self.show_fps,
            "high_score":        self.high_score,
            "high_score_table":  self.high_score_table,
            "aim_assist":        self.aim_assist,
        }
        try:
            with open(os.path.join(SAVE_PATH, filename), 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Settings save error: {e}")

    @classmethod
    def load(cls, filename="settings.json") -> 'GameSettings':
        try:
            with open(os.path.join(SAVE_PATH, filename)) as f:
                d = json.load(f)
            return cls(
                difficulty=Difficulty(d.get("difficulty", "normal")),
                music_volume=d.get("music_volume", 0.5),
                sfx_volume=d.get("sfx_volume", 0.8),
                show_fps=d.get("show_fps", False),
                high_score=d.get("high_score", 0),
                high_score_table=d.get("high_score_table", []),
                aim_assist=d.get("aim_assist", False),
            )
        except Exception:
            return cls()

    def record_score(self, score: int, wave: int):
        self.high_score_table.append({
            "score": score, "wave": wave,
            "difficulty": self.difficulty.value,
            "date": time.strftime("%Y-%m-%d"),
        })
        self.high_score_table = sorted(
            self.high_score_table, key=lambda e: e["score"], reverse=True)[:5]
        if score > self.high_score:
            self.high_score = score
