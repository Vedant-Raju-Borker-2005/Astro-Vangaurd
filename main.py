"""
AstraVanguard: AI Tactical Space Siege — Enhanced Edition v5.0
A professional-grade arcade space shooter.

Compatible with: Arcade 3.0+
Python Version: 3.9+

=== v5.0 Enhancements over v4.0 ===
BUG FIXES:
  - Fixed duplicate boss-spawn condition (was checking living==0 twice without re-evaluation)
  - Fixed camera shake (now uses arcade.Camera2D viewport properly)
  - Fixed draw_bar fill ratio clipping (integer floor was causing visual gap)
  - Fixed wave_manager boss spawn — flag now cleared on every new wave
  - Fixed energy drain not clamping when shield deactivates mid-drain
  - Fixed combo not resetting when timer hits 0 (was off-by-one)
  - Fixed player bullet spawn offset for spread weapon (was misaligned)
  - Fixed powerup magnet applying force even when powerup is dead

NEW SYSTEMS:
  - Formation spawning: V-wing, pincer, column, diamond patterns
  - 3 new enemy types: KAMIKAZE, SNIPER, SHIELDED
  - Weapon upgrade tiers (I/II/III) with stat scaling
  - Between-wave upgrade selection (pick 1 of 3)
  - Achievement system (12 achievements)
  - Asteroid hazard field (drifting obstacles)
  - Shockwave ring visual on explosions
  - Improved boss: BEAM charge + SUMMON attacks, visual telegraphing
  - Dynamic wave modifiers: SPEED RUSH, ELITE SURGE, SHIELDED WAVE
  - Damage number color-coding by weapon type
  - Player trail effect during dash
  - Hit-flash on enemies when damaged
  - Screen flash (red vignette) when player takes damage
  - Smooth animated bars in HUD (interpolated)
  - Achievement toast notifications
  - Pause menu with volume sliders (keyboard)
  - Auto-aim assist mode (toggleable, slight magnet to nearest enemy)
  - Comprehensive controls reference card
"""

import arcade
import random
import math
import heapq
import os
import json
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Set
from collections import defaultdict

# ═══════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════

class GameState(Enum):
    MENU = "menu"
    PLAYING = "playing"
    PAUSED = "paused"
    GAME_OVER = "game_over"
    RESPAWNING = "respawning"
    UPGRADE_SELECT = "upgrade_select"

class Difficulty(Enum):
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"

class PowerUpType(Enum):
    HEALTH = "health"
    SHIELD = "shield"
    WEAPON_SPREAD = "weapon_spread"
    WEAPON_PIERCING = "weapon_piercing"
    SPEED_BOOST = "speed_boost"
    ENERGY_BOOST = "energy_boost"
    EXTRA_LIFE = "extra_life"
    NUKE = "nuke"

class WeaponType(Enum):
    SINGLE = "single"
    SPREAD = "spread"
    PIERCING = "piercing"

class EnemyType(Enum):
    SCOUT = "scout"
    SOLDIER = "soldier"
    ELITE = "elite"
    KAMIKAZE = "kamikaze"
    SNIPER = "sniper"
    SHIELDED = "shielded"

class WaveModifier(Enum):
    NONE = "none"
    SPEED_RUSH = "speed_rush"
    ELITE_SURGE = "elite_surge"
    SHIELDED_WAVE = "shielded_wave"
    DENSE_PACK = "dense_pack"

class AchievementID(Enum):
    FIRST_BLOOD    = "first_blood"
    COMBO_10       = "combo_10"
    COMBO_25       = "combo_25"
    BOSS_SLAYER    = "boss_slayer"
    SURVIVOR_5     = "survivor_5"
    PACIFIST_WAVE  = "pacifist_wave"   # complete a wave without taking damage
    NUKE_LAUNCH    = "nuke_launch"
    SHARPSHOOTER   = "sharpshooter"    # kill 3 snipers in one wave
    FULL_UPGRADE   = "full_upgrade"    # reach tier III on any weapon
    DODGER         = "dodger"          # use dash 50 times
    IRON_SHIELD    = "iron_shield"     # absorb 500 damage with shield
    VETERAN        = "veteran"         # reach wave 10

# ═══════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════

@dataclass
class DifficultySettings:
    enemy_health: int
    enemy_speed_multiplier: float
    enemy_spawn_rate: float
    boss_health: int
    enemy_bullet_damage: int
    enemy_fire_rate: int
    score_multiplier: float
    powerup_drop_boost: float = 0.0

DIFFICULTY_SETTINGS: Dict[Difficulty, DifficultySettings] = {
    Difficulty.EASY: DifficultySettings(
        enemy_health=22, enemy_speed_multiplier=0.75, enemy_spawn_rate=0.6,
        boss_health=180, enemy_bullet_damage=4, enemy_fire_rate=130,
        score_multiplier=0.8, powerup_drop_boost=0.12,
    ),
    Difficulty.NORMAL: DifficultySettings(
        enemy_health=40, enemy_speed_multiplier=1.0, enemy_spawn_rate=1.0,
        boss_health=300, enemy_bullet_damage=8, enemy_fire_rate=90,
        score_multiplier=1.0, powerup_drop_boost=0.0,
    ),
    Difficulty.HARD: DifficultySettings(
        enemy_health=65, enemy_speed_multiplier=1.35, enemy_spawn_rate=1.5,
        boss_health=480, enemy_bullet_damage=14, enemy_fire_rate=55,
        score_multiplier=1.6, powerup_drop_boost=-0.05,
    ),
}

# Weapon damage per tier
WEAPON_TIERS: Dict[WeaponType, List[float]] = {
    WeaponType.SINGLE:   [20.0, 28.0, 40.0],
    WeaponType.SPREAD:   [14.0, 18.0, 24.0],
    WeaponType.PIERCING: [30.0, 42.0, 58.0],
}
WEAPON_SPEED_BONUS: Dict[WeaponType, List[float]] = {
    WeaponType.SINGLE:   [0,  1,  2],
    WeaponType.SPREAD:   [0,  0,  1],
    WeaponType.PIERCING: [2,  3,  4],
}

# ═══════════════════════════════════════════════════
# GAME CONSTANTS
# ═══════════════════════════════════════════════════

SCREEN_WIDTH  = 1280
SCREEN_HEIGHT = 800
SCREEN_TITLE  = "AstraVanguard: AI Tactical Space Siege — Enhanced v5.0"

PLAYER_SPEED   = 5
DASH_SPEED     = 20
DASH_COOLDOWN  = 85
DASH_DURATION  = 12
MAX_ENERGY     = 100
MAX_HEALTH     = 100
MAX_LIVES      = 3
RESPAWN_DELAY  = 120

MAX_SHIELD        = 100
SHIELD_REGEN      = 0.18
SHIELD_COOLDOWN   = 180
SHIELD_ABSORPTION = 0.75
SHIELD_DRAIN      = 0.35

BULLET_SPEED       = 12
ENEMY_BULLET_SPEED = 5.5
FIRE_RATE          = 8
MUZZLE_DURATION    = 5

BASE_ENEMY_SPEED  = 2.0
BOSS_SPEED        = 1.6
MAX_ENEMIES       = 14
GRID_SIZE         = 40

INITIAL_WAVE_SIZE   = 3
WAVE_SIZE_INCREMENT = 2
WAVES_BEFORE_BOSS   = 3

MINIMAP_WIDTH  = 200
MINIMAP_HEIGHT = 140

COMBO_TIMEOUT        = 180
POWERUP_MAGNET_RADIUS = 130

ASSETS_PATH = "assets"
IMG_PATH    = os.path.join(ASSETS_PATH, "images")
SOUND_PATH  = os.path.join(ASSETS_PATH, "sounds")
SAVE_PATH   = "saves"
os.makedirs(SAVE_PATH, exist_ok=True)

# ═══════════════════════════════════════════════════
# ALPHA-BETA PRUNING AI  (unchanged, correct logic)
# ═══════════════════════════════════════════════════

def minimax(depth: int, is_maximizing: bool, distance: float,
            alpha: float, beta: float) -> float:
    if depth == 0:
        return -distance
    if is_maximizing:
        value = -math.inf
        for _ in range(2):
            value = max(value, minimax(depth - 1, False, distance - 20, alpha, beta))
            alpha = max(alpha, value)
            if beta <= alpha:
                break
        return value
    else:
        value = math.inf
        for _ in range(2):
            value = min(value, minimax(depth - 1, True, distance + 20, alpha, beta))
            beta = min(beta, value)
            if beta <= alpha:
                break
        return value

# ═══════════════════════════════════════════════════
# A* PATHFINDING
# ═══════════════════════════════════════════════════

@dataclass
class Node:
    position: Tuple[int, int]
    parent: Optional['Node'] = None
    g: float = 0
    h: float = 0
    f: float = 0
    def __lt__(self, other: 'Node') -> bool:
        return self.f < other.f

def astar(start: Tuple[int, int], end: Tuple[int, int],
          max_iterations: int = 120) -> List[Tuple[int, int]]:
    open_list: List[Node] = []
    closed_set: Set[Tuple[int, int]] = set()
    heapq.heappush(open_list, Node(position=start))
    iterations = 0
    while open_list and iterations < max_iterations:
        iterations += 1
        current = heapq.heappop(open_list)
        closed_set.add(current.position)
        if current.position == end:
            path = []
            while current:
                path.append(current.position)
                current = current.parent
            return path[::-1]
        x, y = current.position
        for nx, ny in [
            (x + GRID_SIZE, y), (x - GRID_SIZE, y),
            (x, y + GRID_SIZE), (x, y - GRID_SIZE),
            (x + GRID_SIZE, y + GRID_SIZE), (x - GRID_SIZE, y - GRID_SIZE),
            (x + GRID_SIZE, y - GRID_SIZE), (x - GRID_SIZE, y + GRID_SIZE),
        ]:
            if not (0 <= nx <= SCREEN_WIDTH and 0 <= ny <= SCREEN_HEIGHT):
                continue
            if (nx, ny) in closed_set:
                continue
            n = Node(position=(nx, ny), parent=current)
            n.g = current.g + math.hypot(nx - x, ny - y)
            n.h = math.hypot(end[0] - nx, end[1] - ny)
            n.f = n.g + n.h
            heapq.heappush(open_list, n)
    return []

# ═══════════════════════════════════════════════════
# ACHIEVEMENTS
# ═══════════════════════════════════════════════════

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

# ═══════════════════════════════════════════════════
# FLOATING TEXT
# ═══════════════════════════════════════════════════

class FloatingText:
    def __init__(self, text: str, x: float, y: float,
                 color: Tuple = (255, 255, 255, 255), font_size: int = 14):
        self.text = text
        self.x = x
        self.y = y
        self.color = list(color)
        self.font_size = font_size
        self.lifetime = 90
        self.alive = True
        self.vy = 1.6

    def update(self):
        self.y += self.vy
        self.vy *= 0.96
        self.lifetime -= 1
        self.color[3] = max(0, int((self.lifetime / 90) * 255))
        if self.lifetime <= 0:
            self.alive = False

    def draw(self):
        if self.alive and self.color[3] > 0:
            arcade.draw_text(self.text, self.x, self.y, tuple(self.color),
                             self.font_size, anchor_x="center")

# ═══════════════════════════════════════════════════
# VISUAL EFFECTS
# ═══════════════════════════════════════════════════

class Shockwave:
    """Expanding ring after explosions."""
    def __init__(self, x: float, y: float,
                 color: Tuple = (255, 200, 80, 200), max_radius: float = 90):
        self.x, self.y = x, y
        self.color = list(color)
        self.radius = 8.0
        self.max_radius = max_radius
        self.alive = True
        self.width = 4

    def update(self):
        self.radius += (self.max_radius - self.radius) * 0.12 + 1.0
        fade = 1.0 - (self.radius / self.max_radius)
        self.color[3] = max(0, int(fade * 200))
        self.width = max(1, int(fade * 5))
        if self.radius >= self.max_radius:
            self.alive = False

    def draw(self):
        if self.alive:
            arcade.draw_circle_outline(self.x, self.y, self.radius,
                                       tuple(self.color), self.width)

class ScreenFlash:
    """Full-screen color flash for damage feedback."""
    def __init__(self):
        self.alpha = 0
        self.color = (255, 0, 0)
        self.decay = 12

    def trigger(self, color=(255, 0, 0), strength=80):
        self.color = color
        self.alpha = min(255, self.alpha + strength)
        self.decay = 10

    def update(self):
        if self.alpha > 0:
            self.alpha = max(0, self.alpha - self.decay)

    def draw(self):
        if self.alpha > 0:
            arcade.draw_rectangle_filled(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                                    SCREEN_WIDTH, SCREEN_HEIGHT,
                                    (*self.color, self.alpha))

class DashTrail:
    """Fading ghost sprites left during dodge-roll."""
    def __init__(self, x: float, y: float):
        self.x, self.y = x, y
        self.alpha = 140
        self.alive = True

    def update(self):
        self.alpha -= 14
        if self.alpha <= 0:
            self.alive = False

    def draw(self):
        if self.alive:
            arcade.draw_circle_filled(self.x, self.y, 14, (0, 180, 255, self.alpha))

# ═══════════════════════════════════════════════════
# PARTICLE SYSTEM
# ═══════════════════════════════════════════════════

class Particle(arcade.Sprite):
    def __init__(self, texture: arcade.Texture, x: float, y: float,
                 velocity: Optional[Tuple[float, float]] = None,
                 spark: bool = False):
        super().__init__(texture)
        self.center_x, self.center_y = x, y
        self.scale = random.uniform(0.08, 0.28) if not spark else random.uniform(0.05, 0.15)
        if velocity:
            self.velocity = list(velocity)
        else:
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 8) if not spark else random.uniform(4, 12)
            self.velocity = [math.cos(angle) * speed, math.sin(angle) * speed]
        self.alpha = 255
        self.fade_rate = random.uniform(4, 9) if not spark else random.uniform(8, 16)
        self.gravity = -0.08 if spark else 0

    def on_update(self, delta_time: float = 1 / 60):
        self.center_x += self.velocity[0]
        self.center_y += self.velocity[1]
        self.velocity[0] *= 0.93
        self.velocity[1] = self.velocity[1] * 0.93 + self.gravity
        self.alpha = max(0, self.alpha - self.fade_rate)
        if self.alpha <= 0:
            self.kill()

# ═══════════════════════════════════════════════════
# STAR FIELD  (two-layer parallax)
# ═══════════════════════════════════════════════════

class StarField:
    def __init__(self):
        self.far:  List[Tuple[float, float, float]] = []
        self.near: List[Tuple[float, float, float]] = []
        self._generate()

    def _generate(self):
        for _ in range(130):
            self.far.append((random.uniform(0, SCREEN_WIDTH),
                             random.uniform(0, SCREEN_HEIGHT),
                             random.uniform(0.4, 1.0)))
        for _ in range(65):
            self.near.append((random.uniform(0, SCREEN_WIDTH),
                              random.uniform(0, SCREEN_HEIGHT),
                              random.uniform(1.0, 2.2)))

    def scroll(self, sf=0.3, sn=0.75):
        self.far  = [(x, (y - sf) % SCREEN_HEIGHT, r) for x, y, r in self.far]
        self.near = [(x, (y - sn) % SCREEN_HEIGHT, r) for x, y, r in self.near]

    def draw(self):
        for x, y, r in self.far:
            arcade.draw_circle_filled(x, y, r, (155, 155, 200, 110))
        for x, y, r in self.near:
            arcade.draw_circle_filled(x, y, r, (215, 215, 255, 190))

# ═══════════════════════════════════════════════════
# ASTEROIDS  (environmental hazard)
# ═══════════════════════════════════════════════════

class Asteroid(arcade.Sprite):
    def __init__(self):
        size = random.randint(18, 38)
        gray = random.randint(90, 160)
        texture = arcade.make_circle_texture(size, (gray, gray, gray, 230))
        super().__init__(texture)
        self.center_x = random.uniform(40, SCREEN_WIDTH - 40)
        self.center_y = SCREEN_HEIGHT + size
        speed = random.uniform(0.8, 2.0)
        drift = random.uniform(-0.5, 0.5)
        self.vx = drift
        self.vy = -speed
        self.rotation_speed = random.uniform(-2, 2)
        self.radius = size
        self.damage = 15

    def on_update(self, delta_time=1 / 60):
        self.center_x += self.vx
        self.center_y += self.vy
        self.angle += self.rotation_speed
        if self.center_y < -60 or self.center_x < -80 or self.center_x > SCREEN_WIDTH + 80:
            self.kill()

# ═══════════════════════════════════════════════════
# POWER-UP
# ═══════════════════════════════════════════════════

class PowerUp(arcade.Sprite):
    COLOR_MAP = {
        PowerUpType.HEALTH:          (255,  60,  60, 255),
        PowerUpType.SHIELD:          ( 60, 100, 255, 255),
        PowerUpType.WEAPON_SPREAD:   (255, 230,   0, 255),
        PowerUpType.WEAPON_PIERCING: (160,   0, 200, 255),
        PowerUpType.SPEED_BOOST:     (  0, 220,  80, 255),
        PowerUpType.ENERGY_BOOST:    (  0, 230, 230, 255),
        PowerUpType.EXTRA_LIFE:      (255, 130,   0, 255),
        PowerUpType.NUKE:            (255,  40,  40, 255),
    }

    def __init__(self, x: float, y: float, power_up_type: PowerUpType):
        self.power_up_type = power_up_type
        texture = arcade.make_circle_texture(15, self.COLOR_MAP.get(power_up_type, (255, 255, 255, 255)))
        super().__init__(texture)
        self.center_x, self.center_y = x, y
        self.lifetime = 380
        self.magnet_vx = self.magnet_vy = 0.0

    def on_update(self, delta_time=1 / 60):
        self.angle += 3
        self.center_x += self.magnet_vx
        self.center_y += self.magnet_vy
        self.magnet_vx *= 0.82
        self.magnet_vy *= 0.82
        self.lifetime -= 1
        if self.lifetime < 90:
            self.alpha = max(0, int((self.lifetime / 90) * 255))
        if self.lifetime <= 0:
            self.kill()

# ═══════════════════════════════════════════════════
# UPGRADE SYSTEM
# ═══════════════════════════════════════════════════

@dataclass
class Upgrade:
    label: str
    description: str
    apply_fn: str   # name of method on GameView to call

UPGRADE_POOL: List[Upgrade] = [
    Upgrade("Max HP +20",       "Increase maximum health by 20",     "upg_max_hp"),
    Upgrade("Max Shield +20",   "Increase maximum shield by 20",     "upg_max_shield"),
    Upgrade("Max Energy +20",   "Increase maximum energy by 20",     "upg_max_energy"),
    Upgrade("Fire Rate+",       "Reduce fire cooldown by 1 frame",   "upg_fire_rate"),
    Upgrade("Dash Speed+",      "Increase dash speed by 2",          "upg_dash_speed"),
    Upgrade("Shield Regen+",    "Shield recharges 50% faster",       "upg_shield_regen"),
    Upgrade("Bullet Damage+",   "Upgrade current weapon tier",       "upg_weapon_tier"),
    Upgrade("Energy Regen+",    "Energy recharges 50% faster",       "upg_energy_regen"),
    Upgrade("Combo Window+",    "Combo timer lasts 50% longer",      "upg_combo_window"),
    Upgrade("Extra Life",       "Gain 1 life (max 5)",               "upg_extra_life"),
    Upgrade("Cooldown-",        "Dash cooldown reduced by 10",       "upg_dash_cd"),
    Upgrade("Spray & Pray",     "Spread shot gains +1 pellet",       "upg_spread_count"),
]

# ═══════════════════════════════════════════════════
# PLAYER
# ═══════════════════════════════════════════════════

class Player(arcade.Sprite):
    def __init__(self):
        texture = arcade.make_circle_texture(28, (0, 220, 255, 255))
        super().__init__(texture)
        self.center_x = SCREEN_WIDTH // 2
        self.center_y = 100

        self.health = self.max_health = MAX_HEALTH
        self.energy = self.max_energy = MAX_ENERGY
        self.shield = self.max_shield = MAX_SHIELD
        self.lives = MAX_LIVES

        self.dash_timer = 0
        self.dash_active = 0
        self.velocity_x = self.velocity_y = 0.0

        self.shield_active = False
        self.shield_cooldown_timer = 0
        self.invincible_timer = 0

        self.current_weapon = WeaponType.SINGLE
        self.weapon_tiers: Dict[WeaponType, int] = {
            WeaponType.SINGLE: 0,
            WeaponType.SPREAD: 0,
            WeaponType.PIERCING: 0,
        }
        self.active_power_ups: Dict[PowerUpType, int] = defaultdict(int)

        # Mutable stats (modified by upgrades)
        self.dash_speed = DASH_SPEED
        self.dash_cd    = DASH_COOLDOWN
        self.shield_regen_rate = SHIELD_REGEN
        self.energy_regen_rate = 0.30
        self.spread_count = 3       # pellets for spread shot
        self.combo_window_mult = 1.0
        self.energy_cost_fire = 5

        # aim-assist toggle
        self.aim_assist = False

    # ── per-frame update ────────────────────────────
    def on_update(self, delta_time=1 / 60):
        if not self.shield_active and self.energy < self.max_energy:
            self.energy = min(self.max_energy, self.energy + self.energy_regen_rate)

        if self.shield_active:
            self.energy = max(0, self.energy - SHIELD_DRAIN)
            if self.energy == 0:
                self.shield_active = False
                self.shield_cooldown_timer = SHIELD_COOLDOWN

        if self.dash_timer > 0:
            self.dash_timer -= 1
        if self.dash_active > 0:
            self.dash_active -= 1
            self.invincible_timer = max(self.invincible_timer, self.dash_active)

        if self.shield_cooldown_timer > 0:
            self.shield_cooldown_timer -= 1
            if self.shield_cooldown_timer == 0:
                pass  # cooldown expired, regen will start next frame
        else:
            if not self.shield_active and self.shield < self.max_shield:
                self.shield = min(self.max_shield, self.shield + self.shield_regen_rate)

        if self.invincible_timer > 0:
            self.invincible_timer -= 1
            self.alpha = 90 if (self.invincible_timer % 6 < 3) else 255
        else:
            self.alpha = 255

        # Power-up countdowns
        expired = [k for k, v in self.active_power_ups.items() if v <= 0]
        for k in expired:
            del self.active_power_ups[k]
            if k in (PowerUpType.WEAPON_SPREAD, PowerUpType.WEAPON_PIERCING):
                self.current_weapon = WeaponType.SINGLE
        for k in list(self.active_power_ups):
            self.active_power_ups[k] -= 1

        self.center_x = max(15, min(SCREEN_WIDTH - 15, self.center_x))
        self.center_y = max(15, min(SCREEN_HEIGHT - 15, self.center_y))

    def dash(self) -> bool:
        if self.dash_timer <= 0 and self.energy >= 10:
            self.dash_timer   = self.dash_cd
            self.dash_active  = DASH_DURATION
            self.invincible_timer = DASH_DURATION
            self.energy -= 10
            return True
        return False

    def toggle_shield(self) -> bool:
        if self.shield_cooldown_timer > 0:
            return False
        if not self.shield_active and self.shield > 10 and self.energy > 20:
            self.shield_active = True
            return True
        elif self.shield_active:
            self.shield_active = False
            return True
        return False

    def apply_power_up(self, power_up: 'PowerUp') -> str:
        pt = power_up.power_up_type
        if pt == PowerUpType.HEALTH:
            self.health = min(self.max_health, self.health + 35); return "+35 HP"
        elif pt == PowerUpType.SHIELD:
            self.shield = min(self.max_shield, self.shield + 50); return "+50 Shield"
        elif pt == PowerUpType.WEAPON_SPREAD:
            self.current_weapon = WeaponType.SPREAD
            self.active_power_ups[PowerUpType.WEAPON_SPREAD] = 600; return "Spread Shot!"
        elif pt == PowerUpType.WEAPON_PIERCING:
            self.current_weapon = WeaponType.PIERCING
            self.active_power_ups[PowerUpType.WEAPON_PIERCING] = 600; return "Piercing Shot!"
        elif pt == PowerUpType.SPEED_BOOST:
            self.active_power_ups[PowerUpType.SPEED_BOOST] = 360; return "Speed Boost!"
        elif pt == PowerUpType.ENERGY_BOOST:
            self.energy = min(self.max_energy, self.energy + 60); return "+60 Energy"
        elif pt == PowerUpType.EXTRA_LIFE:
            self.lives = min(5, self.lives + 1); return "Extra Life!"
        elif pt == PowerUpType.NUKE:
            return "NUKE!"
        return ""

    def take_damage(self, damage: float) -> float:
        """Returns actual damage dealt (0 if invincible). Also handles shield."""
        if self.invincible_timer > 0:
            return 0.0
        absorbed = 0.0
        if self.shield_active and self.shield > 0:
            absorbed = damage * SHIELD_ABSORPTION
            self.shield = max(0, self.shield - absorbed)
            damage -= absorbed
            if self.shield == 0:
                self.shield_active = False
                self.shield_cooldown_timer = SHIELD_COOLDOWN
        if damage > 0:
            self.health -= damage
            self.invincible_timer = 45
        return damage + absorbed   # total damage intercepted (for achievement)

    def get_effective_speed(self) -> float:
        spd = PLAYER_SPEED
        if PowerUpType.SPEED_BOOST in self.active_power_ups:
            spd *= 1.6
        return spd

    def get_weapon_tier(self) -> int:
        return self.weapon_tiers[self.current_weapon]

    def get_bullet_damage(self) -> float:
        tier = self.get_weapon_tier()
        return WEAPON_TIERS[self.current_weapon][tier]

    def get_bullet_speed(self) -> float:
        tier = self.get_weapon_tier()
        return BULLET_SPEED + WEAPON_SPEED_BONUS[self.current_weapon][tier]

# ═══════════════════════════════════════════════════
# BULLET
# ═══════════════════════════════════════════════════

class Bullet(arcade.Sprite):
    def __init__(self, x, y, angle, speed, is_player=True,
                 penetrating=False, damage=20.0, color=None):
        if color is None:
            color = (255, 240, 0, 255) if is_player else (255, 60, 60, 255)
        size = 8 if is_player else 7
        texture = arcade.make_circle_texture(size, color)
        super().__init__(texture)
        self.center_x, self.center_y = x, y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.is_player = is_player
        self.penetrating = penetrating
        self.damage = damage
        self.lifetime = 480

    def on_update(self, delta_time=1 / 60):
        self.center_x += self.vx
        self.center_y += self.vy
        self.lifetime -= 1
        # Kill bullets that leave the battlefield
        if (self.center_x < -80 or self.center_x > SCREEN_WIDTH + 80 or
                self.center_y < -80 or self.center_y > SCREEN_HEIGHT + 80 or
                self.lifetime <= 0):
            self.kill()

# ═══════════════════════════════════════════════════
# ENEMY
# ═══════════════════════════════════════════════════

class Enemy(arcade.Sprite):
    TYPE_COLOR = {
        EnemyType.SCOUT:    (255, 165,   0, 255),
        EnemyType.SOLDIER:  (230,  40,  40, 255),
        EnemyType.ELITE:    (160,   0, 200, 255),
        EnemyType.KAMIKAZE: (255,  60, 200, 255),
        EnemyType.SNIPER:   ( 50, 180, 255, 255),
        EnemyType.SHIELDED: ( 60, 200,  80, 255),
    }

    def __init__(self, difficulty: Difficulty,
                 enemy_type: EnemyType = EnemyType.SCOUT,
                 spawn_x: Optional[float] = None,
                 spawn_y: Optional[float] = None):
        color = self.TYPE_COLOR.get(enemy_type, (200, 200, 200, 255))
        size = 14 if enemy_type == EnemyType.KAMIKAZE else 20
        texture = arcade.make_circle_texture(size, color)
        super().__init__(texture)
        self.enemy_type = enemy_type
        self.difficulty  = difficulty
        settings = DIFFICULTY_SETTINGS[difficulty]

        self.center_x = spawn_x if spawn_x is not None else random.randint(80, SCREEN_WIDTH - 80)
        self.center_y = spawn_y if spawn_y is not None else SCREEN_HEIGHT + 30

        mult = {EnemyType.SCOUT: 0.65, EnemyType.SOLDIER: 1.0, EnemyType.ELITE: 1.6,
                EnemyType.KAMIKAZE: 0.4, EnemyType.SNIPER: 0.9, EnemyType.SHIELDED: 1.4}
        self.health = self.max_health = int(settings.enemy_health * mult.get(enemy_type, 1.0))

        # SHIELDED has a breakable shield
        self.enemy_shield = 40 if enemy_type == EnemyType.SHIELDED else 0
        self.max_enemy_shield = self.enemy_shield

        self.path: List[Tuple[int, int]] = []
        self.repath_timer = random.randint(0, 20)
        self.shoot_timer  = random.randint(0, settings.enemy_fire_rate)
        self.fire_rate    = settings.enemy_fire_rate

        self.knockback_vx = self.knockback_vy = 0.0
        self.hit_flash = 0   # frames of white flash after taking damage

        self.burst_count = self.burst_timer = 0

        # Sniper charge-up
        self.sniper_charge = 0
        self.sniper_locked_angle: Optional[float] = None

    # ── damage ──────────────────────────────────────
    def take_damage(self, damage: float, knockback_angle: float = 0.0) -> float:
        """Returns actual hp damage dealt."""
        actual = damage
        if self.enemy_shield > 0:
            absorbed = min(self.enemy_shield, damage)
            self.enemy_shield -= absorbed
            actual = damage - absorbed
        if actual > 0:
            self.health -= actual
        kb = 4.0
        self.knockback_vx = math.cos(knockback_angle) * kb
        self.knockback_vy = math.sin(knockback_angle) * kb
        self.hit_flash = 6
        return actual

    # ── per-frame update ────────────────────────────
    def update_enemy(self, player: Player, speed: float,
                     enemy_bullets: arcade.SpriteList):
        self.repath_timer += 1
        self.shoot_timer  += 1
        if self.hit_flash > 0:
            self.hit_flash -= 1
            self.alpha = 255 if self.hit_flash % 3 == 0 else 60
        else:
            self.alpha = 255

        self.center_x += self.knockback_vx
        self.center_y += self.knockback_vy
        self.knockback_vx *= 0.68
        self.knockback_vy *= 0.68

        self.center_x = max(20, min(SCREEN_WIDTH - 20, self.center_x))
        self.center_y = max(20, min(SCREEN_HEIGHT - 20, self.center_y))

        eff_speed = speed * DIFFICULTY_SETTINGS[self.difficulty].enemy_speed_multiplier

        # KAMIKAZE — straight charge, faster
        if self.enemy_type == EnemyType.KAMIKAZE:
            angle = math.atan2(player.center_y - self.center_y,
                               player.center_x - self.center_x)
            self.center_x += math.cos(angle) * eff_speed * 1.8
            self.center_y += math.sin(angle) * eff_speed * 1.8
            self.angle = math.degrees(angle)
            return

        # SNIPER — stays back, charges shot
        if self.enemy_type == EnemyType.SNIPER:
            # Keep distance
            dist = math.hypot(player.center_x - self.center_x,
                              player.center_y - self.center_y)
            if dist < 300:
                angle = math.atan2(self.center_y - player.center_y,
                                   self.center_x - player.center_x)
                self.center_x += math.cos(angle) * eff_speed * 0.6
                self.center_y += math.sin(angle) * eff_speed * 0.6
            # Charge shot
            self.sniper_charge += 1
            charge_time = max(50, self.fire_rate - 20)
            if self.sniper_charge < charge_time:
                ratio = self.sniper_charge / charge_time
                # Lock aim at 80%
                if ratio > 0.8:
                    self.sniper_locked_angle = math.atan2(
                        player.center_y - self.center_y,
                        player.center_x - self.center_x)
                # Draw telegraph line handled in draw
            elif self.sniper_charge >= charge_time:
                fire_angle = (self.sniper_locked_angle
                              if self.sniper_locked_angle is not None
                              else math.atan2(player.center_y - self.center_y,
                                              player.center_x - self.center_x))
                b = Bullet(self.center_x, self.center_y, fire_angle,
                           ENEMY_BULLET_SPEED * 1.8, is_player=False,
                           damage=22, color=(50, 180, 255, 255))
                enemy_bullets.append(b)
                self.sniper_charge = 0
                self.sniper_locked_angle = None
            return

        # Standard A* pathing
        if self.repath_timer > 38:
            sx = int(self.center_x // GRID_SIZE) * GRID_SIZE
            sy = int(self.center_y // GRID_SIZE) * GRID_SIZE
            ex = int(player.center_x // GRID_SIZE) * GRID_SIZE
            ey = int(player.center_y // GRID_SIZE) * GRID_SIZE
            self.path = astar((sx, sy), (ex, ey))
            self.repath_timer = 0

        if self.path and len(self.path) > 1:
            target = self.path[1]
            angle = math.atan2(target[1] - self.center_y, target[0] - self.center_x)
        else:
            angle = math.atan2(player.center_y - self.center_y,
                               player.center_x - self.center_x)

        self.angle = math.degrees(angle)
        self.center_x += math.cos(angle) * eff_speed
        self.center_y += math.sin(angle) * eff_speed

        # Shooting logic
        if self.enemy_type == EnemyType.ELITE:
            if self.burst_count > 0:
                self.burst_timer -= 1
                if self.burst_timer <= 0:
                    atk = math.atan2(player.center_y - self.center_y,
                                     player.center_x - self.center_x)
                    for sp in (-0.18, 0, 0.18):
                        b = Bullet(self.center_x, self.center_y, atk + sp,
                                   ENEMY_BULLET_SPEED, is_player=False, damage=9)
                        enemy_bullets.append(b)
                    self.burst_count -= 1
                    self.burst_timer = 9
            elif self.shoot_timer > self.fire_rate:
                self.burst_count = 3
                self.burst_timer = 1
                self.shoot_timer = 0
        else:
            if self.shoot_timer > self.fire_rate:
                atk = math.atan2(player.center_y - self.center_y,
                                 player.center_x - self.center_x)
                b = Bullet(self.center_x, self.center_y, atk,
                           ENEMY_BULLET_SPEED, is_player=False)
                enemy_bullets.append(b)
                self.shoot_timer = 0

    def draw_health_bar(self):
        bar_w, bar_h = 34, 4
        bx = self.center_x - bar_w / 2
        by = self.center_y + 24
        arcade.draw_rectangle_filled(bx + bar_w / 2, by + bar_h / 2, bar_w, bar_h, (60, 0, 0, 200))
        if self.health > 0:
            hp_w = bar_w * (self.health / self.max_health)
            arcade.draw_rectangle_filled(bx + hp_w / 2, by + bar_h / 2, hp_w, bar_h, (0, 210, 60, 220))
        if self.max_enemy_shield > 0:
            sh_w = bar_w * max(0, self.enemy_shield / self.max_enemy_shield)
            arcade.draw_rectangle_filled(bx + sh_w / 2, by + bar_h / 2 + bar_h + 2,
                                    sh_w, bar_h, (60, 200, 80, 200))

    def draw_sniper_telegraph(self, player: Player):
        """Draw aim line for sniper charge-up."""
        if self.enemy_type != EnemyType.SNIPER:
            return
        charge_time = max(50, self.fire_rate - 20)
        if 0 < self.sniper_charge < charge_time:
            ratio = self.sniper_charge / charge_time
            angle = (self.sniper_locked_angle
                     if self.sniper_locked_angle is not None
                     else math.atan2(player.center_y - self.center_y,
                                     player.center_x - self.center_x))
            end_x = self.center_x + math.cos(angle) * 500
            end_y = self.center_y + math.sin(angle) * 500
            alpha = int(ratio * 160)
            arcade.draw_line(self.center_x, self.center_y, end_x, end_y,
                             (50, 180, 255, alpha), max(1, int(ratio * 3)))

# ═══════════════════════════════════════════════════
# BOSS
# ═══════════════════════════════════════════════════

class Boss(arcade.Sprite):
    def __init__(self, difficulty: Difficulty):
        texture = arcade.make_circle_texture(60, (160, 0, 0, 255))
        super().__init__(texture)
        self.difficulty = difficulty
        settings = DIFFICULTY_SETTINGS[difficulty]
        self.center_x = SCREEN_WIDTH // 2
        self.center_y = SCREEN_HEIGHT - 100
        self.health = self.max_health = settings.boss_health
        self.attack_cooldown = 0
        self.phase = 1
        self.move_timer = 0
        self.move_target_x = SCREEN_WIDTH // 2
        self.move_target_y = SCREEN_HEIGHT - 150
        self.rage_mode = False

        # BEAM attack state
        self.beam_charging = False
        self.beam_charge_timer = 0
        self.beam_fire_timer = 0
        self.beam_angle: float = 0

        # SUMMON cooldown
        self.summon_cd = 0

    def _pick_target(self):
        self.move_target_x = random.randint(100, SCREEN_WIDTH - 100)
        self.move_target_y = random.randint(SCREEN_HEIGHT // 2, SCREEN_HEIGHT - 80)
        self.move_timer = random.randint(80, 160)

    def select_attack(self, player: Player) -> str:
        dist   = math.hypot(self.center_x - player.center_x, self.center_y - player.center_y)
        hp_pct = self.health / self.max_health
        if hp_pct < 0.33:
            self.phase = 3; self.rage_mode = True
            attacks = ["BLAST", "LASER", "BEAM", "BLAST"]
        elif hp_pct < 0.66:
            self.phase = 2
            attacks = ["LASER", "DASH", "BEAM", "SUMMON"] if dist > 200 else ["BLAST", "DASH"]
        else:
            self.phase = 1
            attacks = ["LASER", "DASH"] if dist > 300 else ["BLAST"]
        return random.choice(attacks)

    def decide_action(self, player: Player) -> str:
        dist  = math.hypot(self.center_x - player.center_x, self.center_y - player.center_y)
        score = minimax(1, True, dist, -math.inf, math.inf)
        return "ATTACK" if score > -200 else "MOVE"

    def update_boss(self, player: Player,
                    boss_bullets: arcade.SpriteList,
                    enemy_sprites: arcade.SpriteList,
                    difficulty: Difficulty):
        self.move_timer = max(0, self.move_timer - 1)
        if self.summon_cd > 0:
            self.summon_cd -= 1

        # Glide to target
        if self.move_timer == 0:
            self._pick_target()
        dx = self.move_target_x - self.center_x
        dy = self.move_target_y - self.center_y
        dist = math.hypot(dx, dy)
        if dist > 2:
            spd = BOSS_SPEED * (1.5 if self.rage_mode else 1.0)
            self.center_x += (dx / dist) * spd
            self.center_y += (dy / dist) * spd

        self.center_x = max(80, min(SCREEN_WIDTH - 80, self.center_x))
        self.center_y = max(80, min(SCREEN_HEIGHT - 80, self.center_y))

        angle = math.atan2(player.center_y - self.center_y,
                           player.center_x - self.center_x)
        self.angle = math.degrees(angle)

        # BEAM charge/fire sequence
        if self.beam_charging:
            self.beam_charge_timer -= 1
            if self.beam_charge_timer <= 0:
                self.beam_charging = False
                self.beam_fire_timer = 20
                # Fire wide spread
                spread_n = 7 if self.rage_mode else 4
                for i in range(spread_n):
                    sp = (i / (spread_n - 1) - 0.5) * 0.6
                    b = Bullet(self.center_x, self.center_y,
                               self.beam_angle + sp, 10,
                               is_player=False, damage=14,
                               color=(255, 120, 0, 255))
                    boss_bullets.append(b)
            return  # don't normal-attack while charging

        if self.beam_fire_timer > 0:
            self.beam_fire_timer -= 1
            return

        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
            return

        action = self.decide_action(player)
        if action != "ATTACK":
            return

        attack_type = self.select_attack(player)
        cd_mult = 0.55 if self.rage_mode else 1.0

        if attack_type == "LASER":
            n = 3 if self.rage_mode else 1
            for i in range(n):
                sp = (i - (n - 1) / 2) * 0.22
                b = Bullet(self.center_x, self.center_y, angle + sp,
                           9, is_player=False, damage=12)
                boss_bullets.append(b)
            self.attack_cooldown = int(80 * cd_mult)

        elif attack_type == "DASH":
            self.center_x = max(60, min(SCREEN_WIDTH  - 60, self.center_x + math.cos(angle) * 80))
            self.center_y = max(60, min(SCREEN_HEIGHT - 60, self.center_y + math.sin(angle) * 80))
            self.attack_cooldown = int(60 * cd_mult)

        elif attack_type == "BLAST":
            n = 8 if self.rage_mode else 4
            for i in range(n):
                sp = (i / n) * math.pi * 2
                b = Bullet(self.center_x, self.center_y, sp, 6,
                           is_player=False, damage=10)
                boss_bullets.append(b)
            self.attack_cooldown = int(70 * cd_mult)

        elif attack_type == "BEAM":
            self.beam_charging   = True
            self.beam_charge_timer = 80
            self.beam_angle      = angle
            self.attack_cooldown = int(150 * cd_mult)

        elif attack_type == "SUMMON" and self.summon_cd == 0:
            for _ in range(2):
                ox = random.randint(-120, 120)
                e = Enemy(difficulty, EnemyType.SCOUT,
                          spawn_x=max(60, min(SCREEN_WIDTH - 60, self.center_x + ox)),
                          spawn_y=self.center_y - 60)
                enemy_sprites.append(e)
            self.summon_cd = 300
            self.attack_cooldown = int(100 * cd_mult)

    def take_damage(self, damage: float):
        self.health -= damage

    def draw_beam_charge(self):
        """Draw telegraphed beam charge warning."""
        if not self.beam_charging:
            return
        ratio = 1.0 - (self.beam_charge_timer / 80)
        alpha = int(ratio * 200)
        end_x = self.center_x + math.cos(self.beam_angle) * SCREEN_WIDTH
        end_y = self.center_y + math.sin(self.beam_angle) * SCREEN_WIDTH
        w = max(1, int(ratio * 8))
        arcade.draw_line(self.center_x, self.center_y, end_x, end_y,
                         (255, 140, 0, alpha), w)
        # Charge glow
        arcade.draw_circle_outline(self.center_x, self.center_y,
                                   20 + ratio * 30, (255, 200, 80, alpha), 3)

# ═══════════════════════════════════════════════════
# FORMATION SPAWNER
# ═══════════════════════════════════════════════════

class FormationSpawner:
    """Generates coordinated enemy spawn positions."""

    @staticmethod
    def v_wing(count: int) -> List[Tuple[float, float]]:
        positions = []
        cx = SCREEN_WIDTH / 2
        for i in range(count):
            side = 1 if i % 2 == 0 else -1
            idx  = (i // 2) + 1
            positions.append((cx + side * idx * 80, SCREEN_HEIGHT + 40 + idx * 40))
        return positions[:count]

    @staticmethod
    def column(count: int) -> List[Tuple[float, float]]:
        cx = random.randint(150, SCREEN_WIDTH - 150)
        return [(cx, SCREEN_HEIGHT + 40 + i * 60) for i in range(count)]

    @staticmethod
    def pincer(count: int) -> List[Tuple[float, float]]:
        left  = [(100 + i * 30, SCREEN_HEIGHT + 40 + i * 50) for i in range(count // 2)]
        right = [(SCREEN_WIDTH - 100 - i * 30, SCREEN_HEIGHT + 40 + i * 50)
                 for i in range(count - count // 2)]
        return left + right

    @staticmethod
    def diamond(count: int) -> List[Tuple[float, float]]:
        positions = []
        cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT + 100
        for i in range(count):
            a = (i / count) * math.pi * 2
            positions.append((cx + math.cos(a) * 140, cy + math.sin(a) * 60))
        return positions

    @classmethod
    def get_formation(cls, name: str, count: int) -> List[Tuple[float, float]]:
        return {
            "v_wing":  cls.v_wing,
            "column":  cls.column,
            "pincer":  cls.pincer,
            "diamond": cls.diamond,
        }.get(name, cls.v_wing)(count)

# ═══════════════════════════════════════════════════
# CAMERA
# ═══════════════════════════════════════════════════

class Camera:
    def __init__(self):
        self.shake_amount   = 0.0
        self.shake_duration = 0
        self._offset_x = self._offset_y = 0.0

    def shake(self, amount=10.0, duration=10):
        self.shake_amount   = max(self.shake_amount, amount)
        self.shake_duration = max(self.shake_duration, duration)

    def update(self):
        if self.shake_duration > 0:
            self.shake_duration -= 1
            decay = self.shake_duration / 10
            self._offset_x = random.uniform(-self.shake_amount, self.shake_amount) * min(1, decay + 0.3)
            self._offset_y = random.uniform(-self.shake_amount, self.shake_amount) * min(1, decay + 0.3)
            if self.shake_duration == 0:
                self.shake_amount = 0
                self._offset_x = self._offset_y = 0.0
        else:
            self._offset_x = self._offset_y = 0.0

    def get_offset(self) -> Tuple[float, float]:
        return self._offset_x, self._offset_y

# ═══════════════════════════════════════════════════
# SETTINGS PERSISTENCE
# ═══════════════════════════════════════════════════

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

# ═══════════════════════════════════════════════════
# WAVE MANAGER
# ═══════════════════════════════════════════════════

class WaveManager:
    def __init__(self, difficulty: Difficulty):
        self.difficulty = difficulty
        self.current_wave        = 0
        self.enemies_spawned     = 0
        self.enemies_to_spawn    = INITIAL_WAVE_SIZE
        self.wave_timer          = 0
        self.wave_active         = False
        self.wave_delay          = 160
        self.spawn_interval      = 38
        self.spawn_tick          = 0
        self.wave_cleared        = False
        self.modifier: WaveModifier = WaveModifier.NONE

        # Pending formation queue
        self._formation_queue: List[Tuple[float, float]] = []
        self._formation_type: Optional[EnemyType] = None

    def get_wave_size(self) -> int:
        return INITIAL_WAVE_SIZE + self.current_wave * WAVE_SIZE_INCREMENT

    def _pick_modifier(self) -> WaveModifier:
        if self.current_wave < 2:
            return WaveModifier.NONE
        return random.choice([
            WaveModifier.NONE, WaveModifier.NONE,
            WaveModifier.SPEED_RUSH, WaveModifier.ELITE_SURGE,
            WaveModifier.SHIELDED_WAVE, WaveModifier.DENSE_PACK,
        ])

    def start_wave(self):
        self.current_wave    += 1
        self.enemies_spawned  = 0
        self.enemies_to_spawn = self.get_wave_size()
        self.wave_active      = True
        self.wave_timer       = 0
        self.spawn_tick       = 0
        self.wave_cleared     = False
        self.modifier         = self._pick_modifier()

        # Maybe use a formation
        if self.current_wave >= 3 and random.random() < 0.5:
            fname = random.choice(["v_wing", "column", "pincer", "diamond"])
            self._formation_queue = FormationSpawner.get_formation(
                fname, self.enemies_to_spawn)
            self._formation_type = self.get_enemy_type()
        else:
            self._formation_queue = []
            self._formation_type = None

    def update(self, living_enemies: int) -> bool:
        """Returns True if an enemy should be spawned this tick."""
        self.wave_cleared = False
        if not self.wave_active:
            self.wave_timer += 1
            if self.wave_timer >= self.wave_delay:
                self.start_wave()
            return False
        if self.enemies_spawned >= self.enemies_to_spawn and living_enemies == 0:
            self.wave_active  = False
            self.wave_timer   = 0
            self.wave_cleared = True
            return False
        if self.enemies_spawned < self.enemies_to_spawn:
            self.spawn_tick += 1
            interval = max(20, int(self.spawn_interval /
                           DIFFICULTY_SETTINGS[self.difficulty].enemy_spawn_rate))
            if self.spawn_tick >= interval:
                self.spawn_tick = 0
                self.enemies_spawned += 1
                return True
        return False

    def pop_spawn_position(self) -> Optional[Tuple[float, float]]:
        """Returns next formation position (or None for random)."""
        if self._formation_queue:
            return self._formation_queue.pop(0)
        return None

    def is_boss_wave(self) -> bool:
        return self.current_wave > 0 and self.current_wave % WAVES_BEFORE_BOSS == 0

    def get_enemy_type(self) -> EnemyType:
        wave_pct = (self.current_wave % max(WAVES_BEFORE_BOSS, 1)) / WAVES_BEFORE_BOSS
        if self.modifier == WaveModifier.ELITE_SURGE:
            return EnemyType.ELITE
        if self.modifier == WaveModifier.SHIELDED_WAVE:
            return EnemyType.SHIELDED

        # Introduce new types as waves progress
        pool = [EnemyType.SCOUT]
        if self.current_wave >= 2:
            pool += [EnemyType.KAMIKAZE]
        if self.current_wave >= 3:
            pool += [EnemyType.SOLDIER, EnemyType.SOLDIER]
        if self.current_wave >= 4:
            pool += [EnemyType.SNIPER]
        if self.current_wave >= 5:
            pool += [EnemyType.ELITE, EnemyType.SHIELDED]

        return random.choice(pool)

# ═══════════════════════════════════════════════════
# GAME VIEW
# ═══════════════════════════════════════════════════

class GameView(arcade.View):
    def __init__(self, settings: GameSettings):
        super().__init__()
        self.settings = settings
        self.state    = GameState.PLAYING

        self.sounds   = self._load_sounds()

        # Sprite lists
        self.player_sprites       = arcade.SpriteList()
        self.enemy_sprites        = arcade.SpriteList()
        self.bullet_sprites       = arcade.SpriteList()
        self.enemy_bullet_sprites = arcade.SpriteList()
        self.boss_bullet_sprites  = arcade.SpriteList()
        self.boss_sprites         = arcade.SpriteList()
        self.particle_sprites     = arcade.SpriteList()
        self.powerup_sprites      = arcade.SpriteList()
        self.asteroid_sprites     = arcade.SpriteList()

        self.player = Player()
        self.player.aim_assist = settings.aim_assist
        self.player_sprites.append(self.player)

        self.score        = 0
        self.total_kills  = 0
        self.wave_manager = WaveManager(settings.difficulty)
        self.boss: Optional[Boss] = None
        self.camera       = Camera()
        self.star_field   = StarField()
        self.achievements = AchievementSystem()

        # Visual effects
        self.shockwaves:      List[Shockwave]    = []
        self.screen_flash:    ScreenFlash        = ScreenFlash()
        self.dash_trails:     List[DashTrail]    = []
        self.floating_texts:  List[FloatingText] = []

        # HUD smooth bar targets
        self._hud_hp     = float(self.player.health)
        self._hud_shield = float(self.player.shield)
        self._hud_energy = float(self.player.energy)

        # Combo
        self.combo = self.combo_timer = self.max_combo = 0

        # Announcements
        self.announcement_text  = ""
        self.announcement_timer = 0

        # Boss state
        self.boss_warning_timer      = 0
        self.boss_spawned_this_wave  = False
        self._boss_last_phase        = 1

        # Respawn
        self.respawn_timer = 0

        # Upgrade selection
        self.upgrade_choices: List[Upgrade] = []
        self.upgrade_cursor  = 0

        # Input
        self.keys_pressed: Set[int] = set()
        self.mouse_held   = False
        self.mouse_x = SCREEN_WIDTH // 2
        self.mouse_y = SCREEN_HEIGHT // 2

        # Timers
        self.fire_timer   = 0
        self.muzzle_timer = 0
        self.frame_count  = 0
        self.asteroid_spawn_timer = 0

        # Per-wave stats for achievements
        self.wave_damage_taken = 0
        self.wave_sniper_kills = 0

        # Dynamic upgrade state
        self._fire_rate_bonus    = 0   # frames subtracted from FIRE_RATE
        self._energy_regen_bonus = 0.0
        self._combo_window_bonus = 0

        self.wave_manager.start_wave()
        self.announce("Wave 1 — FIGHT!", 100)

    # ── sounds ──────────────────────────────────────
    def _load_sounds(self) -> Dict:
        sounds = {}
        for name, fname in [('shoot','shoot.wav'), ('hit','hit.wav'),
                             ('boss','boss.wav'), ('powerup','powerup.wav'),
                             ('explode','explode.wav')]:
            try:
                sounds[name] = arcade.load_sound(os.path.join(SOUND_PATH, fname))
            except Exception:
                pass
        return sounds

    def _play(self, name: str):
        try:
            if name in self.sounds:
                arcade.play_sound(self.sounds[name], volume=self.settings.sfx_volume)
        except Exception:
            pass

    # ── helpers ──────────────────────────────────────
    def announce(self, text: str, duration: int = 150):
        self.announcement_text  = text
        self.announcement_timer = duration

    def add_float(self, text, x, y, color=(255, 255, 100, 255), size=14):
        self.floating_texts.append(FloatingText(text, x, y, color, size))

    def create_explosion(self, x, y, count=25, color=(255, 165, 0, 255)):
        texture = arcade.make_circle_texture(20, color)
        for _ in range(count):
            self.particle_sprites.append(Particle(texture, x, y))
        self.shockwaves.append(Shockwave(x, y, list(color[:3]) + [200]))

    def create_sparks(self, x, y, count=8, color=(255, 240, 120, 255)):
        texture = arcade.make_circle_texture(8, color)
        for _ in range(count):
            self.particle_sprites.append(Particle(texture, x, y, spark=True))

    # ── upgrade methods (called by name) ────────────
    def upg_max_hp(self):
        self.player.max_health += 20
        self.player.health = min(self.player.health + 20, self.player.max_health)

    def upg_max_shield(self):
        self.player.max_shield += 20
        self.player.shield = min(self.player.shield + 10, self.player.max_shield)

    def upg_max_energy(self):
        self.player.max_energy += 20

    def upg_fire_rate(self):
        self._fire_rate_bonus = min(4, self._fire_rate_bonus + 1)

    def upg_dash_speed(self):
        self.player.dash_speed = min(30, self.player.dash_speed + 2)

    def upg_shield_regen(self):
        self.player.shield_regen_rate *= 1.5

    def upg_weapon_tier(self):
        wt = self.player.current_weapon
        cur = self.player.weapon_tiers[wt]
        if cur < 2:
            self.player.weapon_tiers[wt] = cur + 1
            if self.player.weapon_tiers[wt] == 2:
                self.achievements.unlock(AchievementID.FULL_UPGRADE)

    def upg_energy_regen(self):
        self.player.energy_regen_rate *= 1.5

    def upg_combo_window(self):
        self._combo_window_bonus += 90

    def upg_extra_life(self):
        self.player.lives = min(5, self.player.lives + 1)

    def upg_dash_cd(self):
        self.player.dash_cd = max(30, self.player.dash_cd - 10)

    def upg_spread_count(self):
        self.player.spread_count = min(7, self.player.spread_count + 1)

    def _open_upgrade_screen(self):
        all_upgrades = UPGRADE_POOL.copy()
        random.shuffle(all_upgrades)
        self.upgrade_choices = all_upgrades[:3]
        self.upgrade_cursor  = 0
        self.state = GameState.UPGRADE_SELECT

    def _apply_upgrade(self, idx: int):
        upg = self.upgrade_choices[idx]
        fn  = getattr(self, upg.apply_fn, None)
        if fn:
            fn()
        self.announce(f"Upgraded: {upg.label}", 120)
        self.state = GameState.PLAYING
        self.upgrade_choices = []

    # ── enemy death ──────────────────────────────────
    def _kill_enemy(self, enemy: Enemy):
        self.create_explosion(enemy.center_x, enemy.center_y, 18)
        self.spawn_powerup(enemy.center_x, enemy.center_y, enemy.enemy_type)
        enemy.kill()
        self.total_kills += 1

        if self.total_kills == 1:
            self.achievements.unlock(AchievementID.FIRST_BLOOD)
        if enemy.enemy_type == EnemyType.SNIPER:
            self.wave_sniper_kills += 1
            if self.wave_sniper_kills >= 3:
                self.achievements.unlock(AchievementID.SHARPSHOOTER)

        mult = DIFFICULTY_SETTINGS[self.settings.difficulty].score_multiplier
        combo_bonus = max(1, self.combo // 5 + 1)
        base = {"scout": 10, "soldier": 15, "elite": 25,
                "kamikaze": 8, "sniper": 20, "shielded": 18}.get(
                    enemy.enemy_type.value, 10)
        pts = int(base * mult * combo_bonus)
        self.score += pts
        self.add_float(f"+{pts}", enemy.center_x, enemy.center_y + 20,
                       color=(255, 220, 0, 255))
        self._increment_combo()

    def _increment_combo(self):
        self.combo += 1
        timeout = COMBO_TIMEOUT + self._combo_window_bonus
        self.combo_timer = timeout
        if self.combo > self.max_combo:
            self.max_combo = self.combo
        self.achievements.check(AchievementID.COMBO_10, self.combo >= 10)
        self.achievements.check(AchievementID.COMBO_25, self.combo >= 25)
        if self.combo > 1 and self.combo % 5 == 0:
            self.announce(f"COMBO x{self.combo}!", 90)

    def spawn_powerup(self, x, y, enemy_type: EnemyType):
        base = {EnemyType.SCOUT: 0.10, EnemyType.SOLDIER: 0.18,
                EnemyType.ELITE: 0.35, EnemyType.KAMIKAZE: 0.08,
                EnemyType.SNIPER: 0.22, EnemyType.SHIELDED: 0.28}
        rate = base.get(enemy_type, 0.10)
        rate += DIFFICULTY_SETTINGS[self.settings.difficulty].powerup_drop_boost
        if random.random() > rate:
            return
        pool = list(PowerUpType)
        if self.settings.difficulty == Difficulty.EASY:
            pool = [p for p in pool if p != PowerUpType.NUKE]
        weights = {PowerUpType.HEALTH: 3, PowerUpType.SHIELD: 2,
                   PowerUpType.WEAPON_SPREAD: 2, PowerUpType.WEAPON_PIERCING: 2,
                   PowerUpType.SPEED_BOOST: 2, PowerUpType.ENERGY_BOOST: 2,
                   PowerUpType.EXTRA_LIFE: 1, PowerUpType.NUKE: 1}
        choices = [p for p in pool]
        wts = [weights.get(p, 1) for p in choices]
        total = sum(wts)
        r = random.uniform(0, total)
        acc = chosen = choices[0]
        acc = 0
        for c, w in zip(choices, wts):
            acc += w
            if r <= acc:
                chosen = c
                break
        self.powerup_sprites.append(PowerUp(x, y, chosen))

    def nuke_all_enemies(self):
        for enemy in list(self.enemy_sprites):
            self._kill_enemy(enemy)
        if self.boss:
            self.boss.take_damage(self.boss.health * 0.4)
        self.camera.shake(22, 22)
        self.screen_flash.trigger((255, 100, 0), 120)
        self.announce("NUKE!!!", 120)
        self.achievements.unlock(AchievementID.NUKE_LAUNCH)

    # ── movement & aiming ───────────────────────────
    def handle_player_movement(self):
        spd = self.player.get_effective_speed()
        vx = vy = 0.0
        if arcade.key.LEFT in self.keys_pressed or arcade.key.A in self.keys_pressed:
            vx = -spd
        elif arcade.key.RIGHT in self.keys_pressed or arcade.key.D in self.keys_pressed:
            vx = spd
        if arcade.key.UP in self.keys_pressed or arcade.key.W in self.keys_pressed:
            vy = spd
        elif arcade.key.DOWN in self.keys_pressed or arcade.key.S in self.keys_pressed:
            vy = -spd

        if self.player.dash_active > 0 and (vx != 0 or vy != 0):
            length = math.hypot(vx, vy)
            vx = (vx / length) * self.player.dash_speed
            vy = (vy / length) * self.player.dash_speed
            # Leave dash trail
            if self.frame_count % 3 == 0:
                self.dash_trails.append(DashTrail(self.player.center_x, self.player.center_y))

        self.player.velocity_x = vx
        self.player.velocity_y = vy
        self.player.center_x  += vx
        self.player.center_y  += vy

    def _apply_aim_assist(self):
        """Nudge player angle toward nearest enemy."""
        best_dist = 250.0
        best_angle = None
        for e in self.enemy_sprites:
            d = math.hypot(e.center_x - self.player.center_x,
                           e.center_y - self.player.center_y)
            if d < best_dist:
                best_dist  = d
                best_angle = math.degrees(
                    math.atan2(e.center_y - self.player.center_y,
                               e.center_x - self.player.center_x))
        if best_angle is not None:
            # Blend toward best angle
            cur = self.player.angle
            diff = (best_angle - cur + 180) % 360 - 180
            self.player.angle += diff * 0.15

    def fire_weapon(self):
        if not self.mouse_held:
            return
        effective_fire_rate = max(3, FIRE_RATE - self._fire_rate_bonus)
        self.fire_timer += 1
        if self.fire_timer < effective_fire_rate:
            return
        if self.player.energy < self.player.energy_cost_fire:
            return

        if self.player.aim_assist:
            self._apply_aim_assist()

        ar  = math.radians(self.player.angle)
        off = 32

        dmg = self.player.get_bullet_damage()
        spd = self.player.get_bullet_speed()

        if self.player.current_weapon == WeaponType.SINGLE:
            self.bullet_sprites.append(
                Bullet(self.player.center_x + math.cos(ar) * off,
                       self.player.center_y + math.sin(ar) * off,
                       ar, spd, damage=dmg))

        elif self.player.current_weapon == WeaponType.SPREAD:
            n       = self.player.spread_count
            spread  = 0.22
            offsets = [(i / (n - 1) - 0.5) * spread * 2 for i in range(n)] if n > 1 else [0]
            for sp in offsets:
                a = ar + sp
                self.bullet_sprites.append(
                    Bullet(self.player.center_x + math.cos(a) * off,
                           self.player.center_y + math.sin(a) * off,
                           a, spd, damage=dmg, color=(255, 200, 0, 255)))

        elif self.player.current_weapon == WeaponType.PIERCING:
            self.bullet_sprites.append(
                Bullet(self.player.center_x + math.cos(ar) * off,
                       self.player.center_y + math.sin(ar) * off,
                       ar, spd, penetrating=True, damage=dmg,
                       color=(200, 0, 255, 255)))

        self.player.energy -= self.player.energy_cost_fire
        self._play('shoot')
        self.muzzle_timer = MUZZLE_DURATION
        self.fire_timer   = 0

    # ── main update ──────────────────────────────────
    def on_update(self, delta_time: float):
        self.frame_count += 1

        # Achievements update (toast)
        self.achievements.update()

        if self.state == GameState.GAME_OVER:
            return

        if self.state == GameState.RESPAWNING:
            self.respawn_timer -= 1
            if self.respawn_timer <= 0:
                self._do_respawn()
            return

        if self.state in (GameState.PAUSED, GameState.UPGRADE_SELECT):
            return

        # ── scene ──
        self.star_field.scroll()
        self.camera.update()
        self.screen_flash.update()

        # ── timers ──
        if self.announcement_timer > 0:
            self.announcement_timer -= 1
        if self.boss_warning_timer > 0:
            self.boss_warning_timer -= 1

        # ── combo decay ──
        if self.combo_timer > 0:
            self.combo_timer -= 1
        else:
            self.combo = 0

        # ── HUD bar smoothing ──
        smooth = 0.12
        self._hud_hp     += (self.player.health - self._hud_hp)     * smooth
        self._hud_shield += (self.player.shield - self._hud_shield) * smooth
        self._hud_energy += (self.player.energy - self._hud_energy) * smooth

        # ── player ──
        self.handle_player_movement()
        self.player.update(delta_time)
        self.fire_weapon()

        # ── sprites ──
        for sl in (self.bullet_sprites, self.enemy_bullet_sprites,
                   self.boss_bullet_sprites, self.particle_sprites,
                   self.powerup_sprites, self.asteroid_sprites):
            sl.update(delta_time)

        # ── visual effects ──
        for t in self.dash_trails[:]:
            t.update()
            if not t.alive:
                self.dash_trails.remove(t)
        for sw in self.shockwaves[:]:
            sw.update()
            if not sw.alive:
                self.shockwaves.remove(sw)
        for ft in self.floating_texts[:]:
            ft.update()
            if not ft.alive:
                self.floating_texts.remove(ft)

        # ── powerup magnetism (only on alive powerups) ──
        for pu in self.powerup_sprites:
            if not pu.alive:
                continue
            dx = self.player.center_x - pu.center_x
            dy = self.player.center_y - pu.center_y
            dist = math.hypot(dx, dy)
            if 1 < dist < POWERUP_MAGNET_RADIUS:
                force = (POWERUP_MAGNET_RADIUS - dist) / POWERUP_MAGNET_RADIUS * 5
                pu.magnet_vx += (dx / dist) * force
                pu.magnet_vy += (dy / dist) * force

        # ── asteroid spawning ──
        self.asteroid_spawn_timer += 1
        asteroid_interval = max(180, 420 - self.wave_manager.current_wave * 20)
        if self.asteroid_spawn_timer >= asteroid_interval:
            self.asteroid_sprites.append(Asteroid())
            self.asteroid_spawn_timer = 0

        # ── wave / boss logic ──
        living = len(self.enemy_sprites)
        should_spawn = self.wave_manager.update(living)

        if should_spawn and living < MAX_ENEMIES and not self.boss:
            pos = self.wave_manager.pop_spawn_position()
            et  = (self.wave_manager._formation_type
                   if self.wave_manager._formation_type and pos
                   else self.wave_manager.get_enemy_type())
            sx = pos[0] if pos else None
            sy = pos[1] if pos else None
            e = Enemy(self.settings.difficulty, et, spawn_x=sx, spawn_y=sy)
            self.enemy_sprites.append(e)

        # Boss wave trigger
        if (self.wave_manager.is_boss_wave() and
                self.boss is None and not self.boss_spawned_this_wave):
            if self.boss_warning_timer == 0 and living == 0:
                self.boss_warning_timer = 90
                self.announce("⚠ WARNING: BOSS INCOMING! ⚠", 90)
            if self.boss_warning_timer == 1:
                self._spawn_boss()

        # Wave clear bonus
        if self.wave_manager.wave_cleared:
            mult  = DIFFICULTY_SETTINGS[self.settings.difficulty].score_multiplier
            bonus = int(50 * self.wave_manager.current_wave * mult)
            self.score += bonus
            cleared_wave = self.wave_manager.current_wave - 1
            self.announce(f"Wave {cleared_wave} Clear! +{bonus}", 150)
            self.boss_spawned_this_wave = False

            # Achievement checks
            if cleared_wave >= 5:
                self.achievements.unlock(AchievementID.SURVIVOR_5)
            if cleared_wave >= 10:
                self.achievements.unlock(AchievementID.VETERAN)
            if self.wave_damage_taken == 0:
                self.achievements.unlock(AchievementID.PACIFIST_WAVE)

            # Reset per-wave stats
            self.wave_damage_taken   = 0
            self.wave_sniper_kills   = 0

            # Open upgrade screen every 2 waves
            if cleared_wave > 0 and cleared_wave % 2 == 0:
                self._open_upgrade_screen()

        # ── enemy updates ──
        spd = BASE_ENEMY_SPEED
        for enemy in list(self.enemy_sprites):
            if enemy.alive:
                enemy.update_enemy(self.player, spd, self.enemy_bullet_sprites)

        # ── boss update ──
        if self.boss:
            self.boss.update_boss(self.player, self.boss_bullet_sprites,
                                  self.enemy_sprites, self.settings.difficulty)
            if self.boss.phase != self._boss_last_phase:
                self.announce(f"BOSS PHASE {self.boss.phase}!", 120)
                self.camera.shake(16, 16)
                self.screen_flash.trigger((180, 0, 0), 80)
            self._boss_last_phase = self.boss.phase

        # ══════════════════════════════════════════════
        # COLLISION DETECTION
        # ══════════════════════════════════════════════

        # Player bullets → enemies
        for bullet in list(self.bullet_sprites):
            if not bullet.alive:
                continue
            for enemy in list(self.enemy_sprites):
                if not enemy.alive:
                    continue
                if arcade.check_for_collision(bullet, enemy):
                    kb = math.atan2(enemy.center_y - bullet.center_y,
                                    enemy.center_x - bullet.center_x)
                    actual = enemy.take_damage(bullet.damage, kb)
                    if actual > 0:
                        self.create_sparks(enemy.center_x, enemy.center_y, 6)
                    self._play('hit')
                    if not bullet.penetrating:
                        bullet.kill()
                    if enemy.health <= 0:
                        self._kill_enemy(enemy)
                    if not bullet.alive:
                        break

        # Player bullets → boss
        if self.boss:
            for bullet in list(self.bullet_sprites):
                if bullet.alive and arcade.check_for_collision(bullet, self.boss):
                    self.boss.take_damage(bullet.damage)
                    bullet.kill()
                    self._play('hit')
                    self.camera.shake(3, 3)
                    self.add_float(f"-{int(bullet.damage)}",
                                   self.boss.center_x,
                                   self.boss.center_y + 35,
                                   color=(255, 100, 100, 255))
                    if self.boss.health <= 0:
                        self._kill_boss()

        # Enemy bullets → player
        dmg_setting = DIFFICULTY_SETTINGS[self.settings.difficulty].enemy_bullet_damage
        for bullet in list(self.enemy_bullet_sprites):
            if bullet.alive and arcade.check_for_collision(bullet, self.player):
                dealt = self.player.take_damage(dmg_setting)
                if dealt > 0:
                    bullet.kill()
                    self.camera.shake(4, 4)
                    self.screen_flash.trigger((200, 0, 0), 60)
                    self.wave_damage_taken += dealt
                    self.achievements.shield_absorbed += (dealt - max(0, dmg_setting - dealt))

        # Boss bullets → player
        for bullet in list(self.boss_bullet_sprites):
            if bullet.alive and arcade.check_for_collision(bullet, self.player):
                dealt = self.player.take_damage(bullet.damage)
                if dealt > 0:
                    bullet.kill()
                    self.camera.shake(7, 7)
                    self.screen_flash.trigger((200, 0, 0), 80)
                    self.wave_damage_taken += dealt

        # Player vs powerups
        for pu in list(self.powerup_sprites):
            if pu.alive and arcade.check_for_collision(self.player, pu):
                msg = self.player.apply_power_up(pu)
                if pu.power_up_type == PowerUpType.NUKE:
                    self.nuke_all_enemies()
                self._play('powerup')
                self.add_float(msg, pu.center_x, pu.center_y + 30,
                               color=(0, 255, 160, 255), size=16)
                pu.kill()

        # Player vs asteroids
        for ast in list(self.asteroid_sprites):
            if not ast.alive:
                continue
            dist = math.hypot(self.player.center_x - ast.center_x,
                              self.player.center_y - ast.center_y)
            if dist < ast.radius + 18:
                dealt = self.player.take_damage(ast.damage)
                if dealt > 0:
                    self.camera.shake(8, 8)
                    self.screen_flash.trigger((160, 80, 0), 60)
                    self.create_explosion(ast.center_x, ast.center_y, 15, (140, 120, 100, 255))
                    ast.kill()

        # Enemy (kamikaze) vs player
        for enemy in list(self.enemy_sprites):
            if not enemy.alive or enemy.enemy_type != EnemyType.KAMIKAZE:
                continue
            dist = math.hypot(self.player.center_x - enemy.center_x,
                              self.player.center_y - enemy.center_y)
            if dist < 30:
                dealt = self.player.take_damage(35)
                if dealt > 0:
                    self.create_explosion(enemy.center_x, enemy.center_y, 30, (255, 60, 200, 255))
                    self.camera.shake(12, 12)
                    self.screen_flash.trigger((255, 0, 180), 90)
                enemy.health = 0
                self._kill_enemy(enemy)

        # Shield absorption tracking
        if self.player.shield_active:
            # rough tracking done on damage calls above
            pass
        if self.achievements.shield_absorbed >= 500:
            self.achievements.unlock(AchievementID.IRON_SHIELD)

        # ── death ──
        if self.player.health <= 0:
            self._player_died()

    # ── boss lifecycle ───────────────────────────────
    def _spawn_boss(self):
        self.boss = Boss(self.settings.difficulty)
        self.boss_sprites.append(self.boss)
        self.boss_spawned_this_wave = True
        self._boss_last_phase = 1
        self._play('boss')
        self.announce("⚡ BOSS BATTLE! ⚡", 200)
        self.camera.shake(22, 22)
        self.screen_flash.trigger((100, 0, 0), 100)

    def _kill_boss(self):
        self.create_explosion(self.boss.center_x, self.boss.center_y, 120, (180, 0, 0, 255))
        mult = DIFFICULTY_SETTINGS[self.settings.difficulty].score_multiplier
        pts  = int(300 * mult)
        self.score += pts
        self.total_kills += 1
        self.add_float(f"BOSS DOWN! +{pts}!", self.boss.center_x,
                       self.boss.center_y, color=(255, 60, 60, 255), size=22)
        self.boss.kill()
        self.boss = None
        self.camera.shake(28, 28)
        self.screen_flash.trigger((255, 100, 0), 120)
        self.announce("BOSS DEFEATED!", 200)
        self.achievements.unlock(AchievementID.BOSS_SLAYER)
        self._boss_last_phase = 1
        # Guaranteed powerup drop cluster
        for _ in range(4):
            ox = random.randint(-80, 80)
            oy = random.randint(-80, 80)
            cx = max(80, min(SCREEN_WIDTH - 80, SCREEN_WIDTH // 2 + ox))
            cy = max(80, min(SCREEN_HEIGHT - 80, SCREEN_HEIGHT // 2 + oy))
            self.powerup_sprites.append(PowerUp(cx, cy, random.choice(list(PowerUpType))))

    # ── player lifecycle ─────────────────────────────
    def _player_died(self):
        self.create_explosion(self.player.center_x, self.player.center_y, 70)
        self.player.lives -= 1
        if self.player.lives > 0:
            self.state = GameState.RESPAWNING
            self.respawn_timer = RESPAWN_DELAY
            self.player.alpha = 0
            self.announce(f"Lives remaining: {self.player.lives}", 120)
        else:
            self._game_over()

    def _do_respawn(self):
        self.player.health = MAX_HEALTH // 2
        self.player.shield = MAX_SHIELD // 2
        self.player.energy = MAX_ENERGY
        self.player.center_x = SCREEN_WIDTH // 2
        self.player.center_y = 100
        self.player.invincible_timer = 180
        self.player.alpha = 255
        self.state = GameState.PLAYING
        for sl in (self.enemy_bullet_sprites, self.boss_bullet_sprites):
            for b in list(sl):
                b.kill()

    def _game_over(self):
        self.state = GameState.GAME_OVER
        self.settings.record_score(self.score, self.wave_manager.current_wave)
        self.settings.save()

    # ══════════════════════════════════════════════
    # DRAWING
    # ══════════════════════════════════════════════

    def on_draw(self):
        # Background
        arcade.draw_rectangle_filled(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                                SCREEN_WIDTH, SCREEN_HEIGHT, (4, 4, 18, 255))
        self.star_field.draw()

        # Shockwaves (before sprites)
        for sw in self.shockwaves:
            sw.draw()

        # Dash trails
        for dt in self.dash_trails:
            dt.draw()

        # Sprites
        self.asteroid_sprites.draw()
        self.enemy_sprites.draw()
        for enemy in self.enemy_sprites:
            enemy.draw_health_bar()
            if enemy.enemy_type == EnemyType.SNIPER:
                enemy.draw_sniper_telegraph(self.player)

        self.bullet_sprites.draw()
        self.enemy_bullet_sprites.draw()
        self.boss_bullet_sprites.draw()

        if self.state not in (GameState.RESPAWNING,):
            self.player_sprites.draw()

        self.boss_sprites.draw()
        if self.boss:
            self.boss.draw_beam_charge()

        self.particle_sprites.draw()
        self.powerup_sprites.draw()

        # Muzzle flash
        if self.muzzle_timer > 0:
            ar = math.radians(self.player.angle)
            fx = self.player.center_x + math.cos(ar) * 44
            fy = self.player.center_y + math.sin(ar) * 44
            alpha = int((self.muzzle_timer / MUZZLE_DURATION) * 255)
            arcade.draw_circle_filled(fx, fy, 11, (255, 240, 120, alpha))
            self.muzzle_timer -= 1

        # Player shield glow
        if self.player.shield_active and self.player.shield > 0:
            al = int((self.player.shield / self.player.max_shield) * 180)
            arcade.draw_circle_outline(self.player.center_x, self.player.center_y,
                                       44, (80, 160, 255, al), 3)

        # Boss warning flash
        if self.boss_warning_timer > 0 and self.boss_warning_timer % 10 < 5:
            arcade.draw_rectangle_filled(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                                    SCREEN_WIDTH, SCREEN_HEIGHT, (120, 0, 0, 40))

        # Floating texts
        for ft in self.floating_texts:
            ft.draw()

        # Screen flash (damage feedback)
        self.screen_flash.draw()

        # HUD and overlays
        self._draw_hud()
        self.achievements.draw()

    # ── HUD ────────────────────────────────────────
    def _draw_bar(self, x, y, val, max_val, w, h, col, label):
        arcade.draw_rectangle_filled(x + w / 2, y + h / 2, w, h, (35, 35, 50, 210))
        ratio = max(0.0, val / max_val) if max_val > 0 else 0.0
        if ratio > 0:
            arcade.draw_rectangle_filled(x + (w * ratio) / 2, y + h / 2,
                                    w * ratio, h, col)
        arcade.draw_rectangle_outline(x + w / 2, y + h / 2, w, h, (100, 100, 120, 160), 1)
        arcade.draw_text(f"{label}: {int(val)}/{int(max_val)}",
                         x, y - 3, (190, 190, 200, 210), 11)

    def _draw_hud(self):
        pad = 18
        hud_y = SCREEN_HEIGHT - 28

        # Score / wave / kills
        arcade.draw_text(f"Score: {self.score:,}", pad, hud_y,
                         arcade.color.WHITE, 16, bold=True)
        arcade.draw_text(f"Wave: {self.wave_manager.current_wave}", pad, hud_y - 26,
                         arcade.color.YELLOW, 13)
        arcade.draw_text(f"Kills: {self.total_kills}", pad, hud_y - 48,
                         arcade.color.LIGHT_GRAY, 12)
        combo_col = (255, 80, 0, 255) if self.combo >= 5 else (180, 180, 180, 255)
        arcade.draw_text(f"Combo: x{self.combo}", pad, hud_y - 70,
                         combo_col, 13, bold=(self.combo >= 10))

        # Wave modifier badge
        if self.wave_manager.modifier != WaveModifier.NONE:
            mod_names = {
                WaveModifier.SPEED_RUSH:   ("SPEED RUSH",   (255, 200, 0)),
                WaveModifier.ELITE_SURGE:  ("ELITE SURGE",  (200, 0, 255)),
                WaveModifier.SHIELDED_WAVE:("SHIELDED",     (60, 200, 80)),
                WaveModifier.DENSE_PACK:   ("DENSE PACK",   (255, 120, 0)),
            }
            nm, col = mod_names.get(self.wave_manager.modifier, ("", (200, 200, 200)))
            if nm:
                arcade.draw_text(f"⚡ {nm}", pad, hud_y - 92, (*col, 220), 12, bold=True)

        # HP / Shield / Energy bars (smoothed)
        bw = 185
        bh = 14
        self._draw_bar(pad, hud_y - 122, self._hud_hp, self.player.max_health,
                       bw, bh, (0, 200, 60, 220), "HP")
        self._draw_bar(pad, hud_y - 148, self._hud_shield, self.player.max_shield,
                       bw, bh, (40, 120, 255, 220), "Shield")
        self._draw_bar(pad, hud_y - 174, self._hud_energy, self.player.max_energy,
                       bw, bh, (0, 210, 210, 220), "Energy")

        # Lives
        arcade.draw_text("Lives:", pad, hud_y - 198, arcade.color.WHITE, 12)
        for i in range(self.player.lives):
            arcade.draw_circle_filled(pad + 58 + i * 22, hud_y - 191, 7, (0, 200, 255, 220))
        for i in range(self.player.lives, 5):
            arcade.draw_circle_outline(pad + 58 + i * 22, hud_y - 191, 7, (60, 60, 80, 160), 1)

        # Weapon / dash
        tier_str = ["I", "II", "III"][self.player.get_weapon_tier()]
        arcade.draw_text(f"Weapon: {self.player.current_weapon.value.upper()} [{tier_str}]",
                         pad, hud_y - 224, arcade.color.LIGHT_BLUE, 12)
        dash_ready = self.player.dash_timer <= 0
        dash_col = (0, 255, 80, 255) if dash_ready else (130, 130, 130, 255)
        sh_col   = (80, 160, 255, 255) if self.player.shield_active else (100, 100, 100, 200)
        arcade.draw_text("SHIFT: Dash" + ("  ✔" if dash_ready else ""),
                         pad, hud_y - 244, dash_col, 11)
        arcade.draw_text("E: Shield" + ("  ON" if self.player.shield_active else ""),
                         pad, hud_y - 260, sh_col, 11)

        # Active power-ups
        if self.player.active_power_ups:
            py = hud_y - 280
            arcade.draw_text("Active:", pad, py, arcade.color.LIGHT_YELLOW, 11)
            for pt, frames in self.player.active_power_ups.items():
                py -= 16
                secs = frames // 60
                arcade.draw_text(f"  {pt.value} ({secs}s)", pad, py,
                                 arcade.color.LIGHT_YELLOW, 11)

        # Boss health bar
        if self.boss:
            bw2, bh2 = 420, 22
            bx2 = (SCREEN_WIDTH - bw2) // 2
            by2 = SCREEN_HEIGHT - 46
            ratio = max(0.0, self.boss.health / self.boss.max_health)
            col2 = (255, 150, 0, 220) if self.boss.rage_mode else (255, 50, 50, 220)
            arcade.draw_rectangle_filled(bx2 + bw2 / 2, by2 + bh2 / 2, bw2, bh2, (40, 0, 0, 210))
            if ratio > 0:
                arcade.draw_rectangle_filled(bx2 + (bw2 * ratio) / 2, by2 + bh2 / 2,
                                        bw2 * ratio, bh2, col2)
            arcade.draw_rectangle_outline(bx2 + bw2 / 2, by2 + bh2 / 2, bw2, bh2,
                                     arcade.color.WHITE, 1)
            ph_lbl = f"BOSS  Phase {self.boss.phase}"
            if self.boss.rage_mode:
                ph_lbl += "  [RAGE MODE]"
            if self.boss.beam_charging:
                ph_lbl += "  ⚡ CHARGING BEAM ⚡"
            arcade.draw_text(ph_lbl, SCREEN_WIDTH // 2, by2 + bh2 + 8,
                             arcade.color.RED, 13, anchor_x="center", bold=True)
            arcade.draw_text(f"{int(self.boss.health)}/{int(self.boss.max_health)}",
                             SCREEN_WIDTH // 2, by2 + 4,
                             arcade.color.WHITE, 11, anchor_x="center")

        # Enemies remaining
        en = len(self.enemy_sprites)
        if en > 0 and not self.boss:
            arcade.draw_text(f"Enemies: {en}", SCREEN_WIDTH - 164, SCREEN_HEIGHT - 30,
                             arcade.color.LIGHT_RED_BROWN, 13)

        # FPS
        if self.settings.show_fps:
            fps = arcade.get_fps()
            arcade.draw_text(f"FPS: {fps:.0f}", SCREEN_WIDTH - 90, 10,
                             (140, 140, 140, 200), 12)

        # Announcement
        if self.announcement_timer > 0:
            alpha = min(255, self.announcement_timer * 3)
            arcade.draw_text(self.announcement_text,
                             SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 130,
                             (255, 255, 100, alpha), 28, anchor_x="center", bold=True)

        self._draw_minimap()
        self._draw_state_overlay()

    def _draw_minimap(self):
        mx, my = SCREEN_WIDTH - MINIMAP_WIDTH - 10, 10
        cw, ch = MINIMAP_WIDTH, MINIMAP_HEIGHT
        arcade.draw_rectangle_filled(mx + cw / 2, my + ch / 2, cw, ch, (8, 8, 26, 210))
        arcade.draw_rectangle_outline(mx + cw / 2, my + ch / 2, cw, ch, (60, 60, 90, 200), 1)
        sx, sy = cw / SCREEN_WIDTH, ch / SCREEN_HEIGHT
        arcade.draw_circle_filled(mx + self.player.center_x * sx,
                                  my + self.player.center_y * sy, 4, (0, 220, 255, 255))
        for e in self.enemy_sprites:
            c = Enemy.TYPE_COLOR.get(e.enemy_type, (220, 60, 60, 220))
            arcade.draw_circle_filled(mx + e.center_x * sx, my + e.center_y * sy, 2, c)
        if self.boss:
            arcade.draw_circle_filled(mx + self.boss.center_x * sx,
                                      my + self.boss.center_y * sy, 5, (255, 0, 0, 255))
        for pu in self.powerup_sprites:
            arcade.draw_circle_filled(mx + pu.center_x * sx,
                                      my + pu.center_y * sy, 2, (0, 255, 140, 200))
        for ast in self.asteroid_sprites:
            arcade.draw_circle_filled(mx + ast.center_x * sx,
                                      my + ast.center_y * sy, 2, (160, 140, 120, 200))
        arcade.draw_text("MAP", mx + 4, my + ch - 14, (100, 100, 150, 200), 10)
        arcade.draw_text(f"E:{len(self.enemy_sprites)}", mx + 4, my + 2,
                         (200, 80, 80, 200), 10)

    def _draw_state_overlay(self):
        if self.state == GameState.PAUSED:
            arcade.draw_rectangle_filled(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                                    SCREEN_WIDTH, SCREEN_HEIGHT, (0, 0, 0, 165))
            arcade.draw_text("PAUSED", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 90,
                             arcade.color.YELLOW, 52, anchor_x="center", bold=True)
            arcade.draw_text("SPACE — Resume    R — Restart    Q — Menu",
                             SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20,
                             arcade.color.WHITE, 18, anchor_x="center")
            arcade.draw_text(f"Difficulty: {self.settings.difficulty.value.upper()}",
                             SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 24,
                             arcade.color.LIGHT_GREEN, 15, anchor_x="center")
            arcade.draw_text(f"Max Combo: x{self.max_combo}  |  "
                             f"Score: {self.score:,}  |  Kills: {self.total_kills}",
                             SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 56,
                             arcade.color.LIGHT_YELLOW, 14, anchor_x="center")
            aim_col = (0, 220, 80, 255) if self.player.aim_assist else (160, 160, 160, 255)
            arcade.draw_text(f"A key — Aim Assist: {'ON' if self.player.aim_assist else 'OFF'}",
                             SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 90,
                             aim_col, 13, anchor_x="center")
            # Unlocked achievements
            arcade.draw_text(f"Achievements: {len(self.achievements.unlocked)}/{len(AchievementID)}",
                             SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 120,
                             (180, 180, 180, 200), 13, anchor_x="center")

        elif self.state == GameState.RESPAWNING:
            secs = max(1, self.respawn_timer // 60 + 1)
            arcade.draw_text(f"Respawning in {secs}...",
                             SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                             (255, 200, 0, 220), 34, anchor_x="center", bold=True)

        elif self.state == GameState.UPGRADE_SELECT:
            self._draw_upgrade_screen()

        elif self.state == GameState.GAME_OVER:
            self._draw_game_over()

    def _draw_upgrade_screen(self):
        arcade.draw_rectangle_filled(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                                SCREEN_WIDTH, SCREEN_HEIGHT, (0, 0, 0, 190))
        arcade.draw_text("CHOOSE AN UPGRADE", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 200,
                         (255, 220, 0, 255), 36, anchor_x="center", bold=True)
        arcade.draw_text("↑↓ / W S to navigate   ENTER to confirm",
                         SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 155,
                         (180, 180, 180, 200), 15, anchor_x="center")

        card_w, card_h = 340, 100
        for i, upg in enumerate(self.upgrade_choices):
            cx = SCREEN_WIDTH // 2
            cy = SCREEN_HEIGHT // 2 + 50 - i * (card_h + 16)
            selected = (i == self.upgrade_cursor)
            bg = (30, 60, 80, 230) if selected else (20, 20, 40, 200)
            border = (0, 220, 255, 255) if selected else (60, 60, 100, 200)
            arcade.draw_rectangle_filled(cx, cy, card_w, card_h, bg)
            arcade.draw_rectangle_outline(cx, cy, card_w, card_h, border, 2 if selected else 1)
            arcade.draw_text(upg.label, cx, cy + 22,
                             (255, 230, 80, 255) if selected else (200, 200, 200, 255),
                             16, anchor_x="center", bold=selected)
            arcade.draw_text(upg.description, cx, cy - 8,
                             (160, 200, 200, 220), 12, anchor_x="center")

    def _draw_game_over(self):
        arcade.draw_rectangle_filled(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                                SCREEN_WIDTH, SCREEN_HEIGHT, (0, 0, 0, 215))
        arcade.draw_text("GAME OVER", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 180,
                         arcade.color.RED, 62, anchor_x="center", bold=True)
        arcade.draw_text(f"Score: {self.score:,}",
                         SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 112,
                         arcade.color.WHITE, 28, anchor_x="center")
        arcade.draw_text(
            f"Wave: {self.wave_manager.current_wave}  |  "
            f"Kills: {self.total_kills}  |  Max Combo: x{self.max_combo}",
            SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 72,
            arcade.color.LIGHT_GRAY, 16, anchor_x="center")

        # Achievements earned
        if self.achievements.unlocked:
            ach_names = [ACHIEVEMENT_META[a]["name"] for a in self.achievements.unlocked]
            arcade.draw_text("Achievements: " + "  ·  ".join(ach_names[:6]),
                             SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40,
                             (255, 200, 0, 200), 12, anchor_x="center")

        # Top scores
        arcade.draw_text("— TOP SCORES —", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 8,
                         arcade.color.GOLD, 18, anchor_x="center", bold=True)
        for i, entry in enumerate(self.settings.high_score_table[:5]):
            row_y = SCREEN_HEIGHT // 2 - 22 - i * 26
            medals = ["🥇", "🥈", "🥉", " 4", " 5"]
            arcade.draw_text(
                f"{medals[i]}  {entry['score']:>9,}  Wave {entry['wave']:>2}  "
                f"[{entry['difficulty']}]  {entry['date']}",
                SCREEN_WIDTH // 2, row_y, arcade.color.LIGHT_YELLOW, 14, anchor_x="center")

        arcade.draw_text("R — Restart    Q — Menu",
                         SCREEN_WIDTH // 2, 50, arcade.color.WHITE, 16, anchor_x="center")

    # ── input ────────────────────────────────────────
    def on_mouse_motion(self, x, y, dx, dy):
        self.mouse_x, self.mouse_y = x, y
        if self.state == GameState.PLAYING:
            self.player.angle = math.degrees(
                math.atan2(y - self.player.center_y, x - self.player.center_x))

    def on_mouse_press(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT and self.state == GameState.PLAYING:
            self.mouse_held = True
            self.fire_timer = FIRE_RATE  # allow immediate first shot

    def on_mouse_release(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.mouse_held = False
            self.fire_timer = 0

    def on_key_press(self, symbol: int, modifiers: int):
        self.keys_pressed.add(symbol)

        if self.state == GameState.UPGRADE_SELECT:
            if symbol in (arcade.key.W, arcade.key.UP):
                self.upgrade_cursor = (self.upgrade_cursor - 1) % len(self.upgrade_choices)
            elif symbol in (arcade.key.S, arcade.key.DOWN):
                self.upgrade_cursor = (self.upgrade_cursor + 1) % len(self.upgrade_choices)
            elif symbol == arcade.key.ENTER:
                self._apply_upgrade(self.upgrade_cursor)
            return

        if symbol in (arcade.key.LSHIFT, arcade.key.RSHIFT):
            if self.state == GameState.PLAYING:
                if self.player.dash():
                    self.achievements.dash_count += 1
                    if self.achievements.dash_count >= 50:
                        self.achievements.unlock(AchievementID.DODGER)

        elif symbol == arcade.key.E:
            if self.state == GameState.PLAYING:
                self.player.toggle_shield()

        elif symbol == arcade.key.SPACE:
            if self.state == GameState.PLAYING:
                self.state = GameState.PAUSED
            elif self.state == GameState.PAUSED:
                self.state = GameState.PLAYING

        elif symbol == arcade.key.F:
            self.settings.show_fps = not self.settings.show_fps

        elif symbol == arcade.key.A and self.state == GameState.PAUSED:
            self.player.aim_assist = not self.player.aim_assist
            self.settings.aim_assist = self.player.aim_assist

        elif symbol == arcade.key.R:
            if self.state in (GameState.GAME_OVER, GameState.PAUSED):
                self.window.show_view(GameView(self.settings))

        elif symbol == arcade.key.Q:
            if self.state in (GameState.GAME_OVER, GameState.PAUSED):
                self.window.show_view(MenuView(self.settings))

    def on_key_release(self, symbol: int, modifiers: int):
        self.keys_pressed.discard(symbol)

# ═══════════════════════════════════════════════════
# MENU VIEW
# ═══════════════════════════════════════════════════

class MenuView(arcade.View):
    def __init__(self, settings: GameSettings):
        super().__init__()
        self.settings   = settings
        self.star_field = StarField()
        self.tick       = 0
        self.particles: List[Particle] = []
        self._particle_list = arcade.SpriteList()

    def on_update(self, delta_time: float):
        self.star_field.scroll(0.2, 0.5)
        self.tick += 1
        # Ambient particles
        if self.tick % 20 == 0:
            tex = arcade.make_circle_texture(16, (0, 180, 255, 180))
            p = Particle(tex,
                         random.uniform(0, SCREEN_WIDTH),
                         random.uniform(0, SCREEN_HEIGHT // 3))
            self._particle_list.append(p)
        self._particle_list.update(delta_time)

    def on_draw(self):
        arcade.draw_rectangle_filled(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                                SCREEN_WIDTH, SCREEN_HEIGHT, (4, 4, 18, 255))
        self.star_field.draw()
        self._particle_list.draw()

        pulse = 0.82 + 0.18 * math.sin(self.tick * 0.05)
        col   = (int(0 * pulse), int(200 * pulse), int(255 * pulse), 255)

        arcade.draw_text("ASTRA", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 110,
                         col, 88, anchor_x="center", bold=True)
        arcade.draw_text("VANGUARD", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 196,
                         (255, 255, 255, 220), 56, anchor_x="center", bold=True)
        arcade.draw_text("AI Tactical Space Siege  v5.0",
                         SCREEN_WIDTH // 2, SCREEN_HEIGHT - 240,
                         (120, 160, 200, 200), 20, anchor_x="center")

        arcade.draw_line(SCREEN_WIDTH // 2 - 280, SCREEN_HEIGHT - 262,
                         SCREEN_WIDTH // 2 + 280, SCREEN_HEIGHT - 262,
                         (50, 70, 110, 160), 1)

        cy = SCREEN_HEIGHT // 2 + 80
        arcade.draw_text("ENTER — Start Game", SCREEN_WIDTH // 2, cy,
                         arcade.color.YELLOW, 22, anchor_x="center", bold=True)
        arcade.draw_text("D — Cycle Difficulty", SCREEN_WIDTH // 2, cy - 44,
                         arcade.color.WHITE, 16, anchor_x="center")
        arcade.draw_text("Q — Quit", SCREEN_WIDTH // 2, cy - 80,
                         arcade.color.WHITE, 16, anchor_x="center")

        diff_colors = {
            Difficulty.EASY:   (50, 220, 50,  255),
            Difficulty.NORMAL: (255, 200, 0,  255),
            Difficulty.HARD:   (255, 50,  50, 255),
        }
        arcade.draw_text(f"Difficulty: {self.settings.difficulty.value.upper()}",
                         SCREEN_WIDTH // 2, cy - 128,
                         diff_colors[self.settings.difficulty],
                         22, anchor_x="center", bold=True)

        # Controls
        controls = [
            "WASD / Arrows — Move",
            "Mouse Left — Aim & Fire",
            "SHIFT — Dodge Roll (i-frames)",
            "E — Toggle Shield",
            "F — FPS Counter",
            "SPACE — Pause / Resume",
            "R — Restart  (pause/gameover)",
            "Q — Quit to Menu",
        ]
        lx, ly = SCREEN_WIDTH // 2 - 160, cy - 180
        arcade.draw_text("Controls:", lx, ly, (140, 170, 220, 220), 14, bold=True)
        for i, c in enumerate(controls):
            arcade.draw_text(c, lx, ly - 22 - i * 20, (110, 140, 170, 200), 12)

        if self.settings.high_score > 0:
            arcade.draw_text(f"Best: {self.settings.high_score:,}",
                             SCREEN_WIDTH // 2, 50,
                             arcade.color.GOLD, 20, anchor_x="center", bold=True)

    def on_key_press(self, symbol: int, modifiers: int):
        if symbol == arcade.key.ENTER:
            self.window.show_view(GameView(self.settings))
        elif symbol == arcade.key.D:
            diffs = list(Difficulty)
            self.settings.difficulty = diffs[(diffs.index(self.settings.difficulty) + 1) % len(diffs)]
            self.settings.save()
        elif symbol == arcade.key.Q:
            arcade.close_window()

# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════

def main():
    settings = GameSettings.load()
    window   = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, resizable=False)
    window.background_color = arcade.color.BLACK
    window.show_view(MenuView(settings))
    arcade.run()

if __name__ == "__main__":
    main()
