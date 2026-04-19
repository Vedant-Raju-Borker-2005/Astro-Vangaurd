import arcade
from typing import Set, List, Tuple, Dict
from core.constants import AchievementID, SCREEN_WIDTH

ACHIEVEMENT_META: Dict[AchievementID, Dict] = {
    AchievementID.FIRST_BLOOD:   {"name": "First Blood",    "desc": "Kill your first enemy"},
    AchievementID.COMBO_10:      {"name": "On Fire!",       "desc": "Reach a x10 combo"},
    AchievementID.COMBO_25:      {"name": "Unstoppable",    "desc": "Reach a x25 combo"},
    AchievementID.BOSS_SLAYER:   {"name": "Boss Slayer",    "desc": "Defeat a boss"},
    AchievementID.SURVIVOR_5:    {"name": "Survivor",       "desc": "Reach wave 5"},
    AchievementID.PACIFIST_WAVE: {"name": "Untouchable",    "desc": "Clear a wave undamaged"},
    AchievementID.NUKE_LAUNCH:   {"name": "Big Bang",       "desc": "Use a NUKE power-up"},
    AchievementID.SHARPSHOOTER:  {"name": "Sharpshooter",   "desc": "Kill 3 Snipers in one wave"},
    AchievementID.FULL_UPGRADE:  {"name": "Fully Armed",    "desc": "Upgrade any weapon to Tier III"},
    AchievementID.DODGER:        {"name": "Ghost",          "desc": "Dash 50 times total"},
    AchievementID.IRON_SHIELD:   {"name": "Iron Shield",    "desc": "Absorb 500 damage with shield"},
    AchievementID.VETERAN:       {"name": "Veteran",        "desc": "Survive to wave 10"},
}

class AchievementSystem:
    def __init__(self):
        self.unlocked: Set[AchievementID] = set()
        self.toast_queue: List[Tuple[AchievementID, int]] = []  # (id, frames_left)
        # Session counters
        self.dash_count      = 0
        self.shield_absorbed = 0.0
        self.sniper_kills_this_wave = 0

    def unlock(self, aid: AchievementID):
        if aid not in self.unlocked:
            self.unlocked.add(aid)
            self.toast_queue.append((aid, 240))

    def check(self, aid: AchievementID, condition: bool):
        if condition:
            self.unlock(aid)

    def update(self):
        if self.toast_queue:
            aid, frames = self.toast_queue[0]
            self.toast_queue[0] = (aid, frames - 1)
            if frames <= 1:
                self.toast_queue.pop(0)

    def draw(self):
        if not self.toast_queue:
            return
        aid, frames = self.toast_queue[0]
        meta = ACHIEVEMENT_META[aid]
        alpha = min(255, frames * 4) if frames < 60 else 255
        w, h = 340, 64
        x = SCREEN_WIDTH - w - 16
        y = 90
        arcade.draw_rectangle_filled(x + w // 2, y + h // 2, w, h, (20, 20, 40, int(alpha * 0.9)))
        arcade.draw_rectangle_outline(x + w // 2, y + h // 2, w, h, (255, 200, 0, alpha), 2)
        arcade.draw_text("🏆 Achievement Unlocked!", x + 10, y + 40,
                         (255, 200, 0, alpha), 13, bold=True)
        arcade.draw_text(f"{meta['name']} — {meta['desc']}", x + 10, y + 14,
                         (220, 220, 220, alpha), 12)
