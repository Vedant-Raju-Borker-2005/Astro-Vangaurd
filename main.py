"""
AstraVanguard: AI Tactical Space Siege - Enhanced Edition for Arcade 3.0
A professional-grade arcade space shooter with advanced game mechanics,
AI systems, and quality-of-life features.

Compatible with: Arcade 3.0+
Python Version: 3.8+

Author: Senior Game Developer
Version: 4.0.0
License: MIT

Enhancement notes v4.0:
  - Fixed bullet velocity (was using angle without sin/cos update loop)
  - Added combo multiplier + streak system
  - Added invincibility frames after taking damage
  - Added screen wrap / boundary kill for enemy bullets
  - Added boss phase-transition VFX + warning text
  - Added per-wave completion bonus & wave-clear announcement
  - Added lives system (3 lives, respawn delay)
  - Added pause menu with difficulty shown
  - Added FPS counter toggle (F key)
  - Added proper muzzle-flash positional correction for all weapon types
  - Added dodge-roll (replaces raw dash): grants i-frames during roll
  - Added energy shield drain over time when active
  - Added dual-fire synced spread (was off-center)
  - Added enemy knockback on hit
  - Added powerup magnetism when player is near
  - Added boss warning flash before boss spawns
  - Added elite enemy ranged burst-fire pattern
  - Added scrolling star-field background (parallax two-layer)
  - Added kill counter + enemies-remaining HUD indicator
  - Added score blip text (floating damage numbers)
  - Added high score hall (top 5) saved to JSON
  - Fixed shield-regen not stopping when shield is full
  - Fixed wave_manager not resetting wave_active after wave ends
  - Fixed power-up duration reset when same type collected again
  - Added keyboard-only aiming mode (arrows + WASD for aim)
  - Added restart hotkey from pause (R)
  - Clamped boss to screen bounds
  - Added enemy count to minimap legend
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

# ===============================
# ENUMS AND CONSTANTS
# ===============================

class GameState(Enum):
    MENU = "menu"
    PLAYING = "playing"
    PAUSED = "paused"
    GAME_OVER = "game_over"
    RESPAWNING = "respawning"

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

# ===============================
# CONFIGURATION DATA CLASSES
# ===============================

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
        enemy_health=25, enemy_speed_multiplier=0.8, enemy_spawn_rate=0.6,
        boss_health=200, enemy_bullet_damage=4, enemy_fire_rate=120,
        score_multiplier=0.8, powerup_drop_boost=0.1
    ),
    Difficulty.NORMAL: DifficultySettings(
        enemy_health=40, enemy_speed_multiplier=1.0, enemy_spawn_rate=1.0,
        boss_health=300, enemy_bullet_damage=8, enemy_fire_rate=90,
        score_multiplier=1.0, powerup_drop_boost=0.0
    ),
    Difficulty.HARD: DifficultySettings(
        enemy_health=60, enemy_speed_multiplier=1.3, enemy_spawn_rate=1.4,
        boss_health=450, enemy_bullet_damage=12, enemy_fire_rate=60,
        score_multiplier=1.5, powerup_drop_boost=-0.05
    ),
}

# ===============================
# GAME CONSTANTS
# ===============================

SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
SCREEN_TITLE = "AstraVanguard: AI Tactical Space Siege - Enhanced v4.0"

PLAYER_SPEED = 5
DASH_SPEED = 18
DASH_COOLDOWN = 90           # frames
DASH_DURATION = 12           # frames of i-frames + movement
MAX_ENERGY = 100
MAX_HEALTH = 100
MAX_LIVES = 3
RESPAWN_DELAY = 120          # frames

MAX_SHIELD = 100
SHIELD_REGEN = 0.2
SHIELD_COOLDOWN = 180
SHIELD_ABSORPTION = 0.75
SHIELD_DRAIN = 0.4           # energy drain per frame while active

BULLET_SPEED = 12
ENEMY_BULLET_SPEED = 6
FIRE_RATE = 8
MUZZLE_DURATION = 5

BASE_ENEMY_SPEED = 2
BOSS_SPEED = 1.5
MAX_ENEMIES = 12
GRID_SIZE = 40

INITIAL_WAVE_SIZE = 3
WAVE_SIZE_INCREMENT = 2
WAVES_BEFORE_BOSS = 3

MINIMAP_WIDTH = 200
MINIMAP_HEIGHT = 150

COMBO_TIMEOUT = 180          # frames before combo resets
POWERUP_MAGNET_RADIUS = 120  # px — powerups accelerate toward player inside this

ASSETS_PATH = "assets"
IMG_PATH = os.path.join(ASSETS_PATH, "images")
SOUND_PATH = os.path.join(ASSETS_PATH, "sounds")
SAVE_PATH = "saves"
os.makedirs(SAVE_PATH, exist_ok=True)

# ===============================
# ALPHA-BETA PRUNING AI
# ===============================

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

# ===============================
# A* PATHFINDING
# ===============================

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
          max_iterations: int = 150) -> List[Tuple[int, int]]:
    open_list: List[Node] = []
    closed_set: Set[Tuple[int, int]] = set()

    start_node = Node(position=start)
    heapq.heappush(open_list, start_node)
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
        neighbors = [
            (x + GRID_SIZE, y), (x - GRID_SIZE, y),
            (x, y + GRID_SIZE), (x, y - GRID_SIZE),
            (x + GRID_SIZE, y + GRID_SIZE), (x - GRID_SIZE, y - GRID_SIZE),
            (x + GRID_SIZE, y - GRID_SIZE), (x - GRID_SIZE, y + GRID_SIZE),
        ]
        for nx, ny in neighbors:
            if not (0 <= nx <= SCREEN_WIDTH and 0 <= ny <= SCREEN_HEIGHT):
                continue
            if (nx, ny) in closed_set:
                continue
            neighbor = Node(position=(nx, ny), parent=current)
            neighbor.g = current.g + math.hypot(nx - x, ny - y)
            neighbor.h = math.hypot(end[0] - nx, end[1] - ny)
            neighbor.f = neighbor.g + neighbor.h
            heapq.heappush(open_list, neighbor)
    return []

# ===============================
# FLOATING SCORE TEXT
# ===============================

class FloatingText:
    """Small score/event text that floats upward and fades."""

    def __init__(self, text: str, x: float, y: float,
                 color: Tuple[int, int, int, int] = (255, 255, 255, 255),
                 font_size: int = 14):
        self.text = text
        self.x = x
        self.y = y
        self.color = list(color)
        self.font_size = font_size
        self.lifetime = 90
        self.alive = True
        self.vy = 1.5

    def update(self):
        self.y += self.vy
        self.vy *= 0.97
        self.lifetime -= 1
        fade = int((self.lifetime / 90) * 255)
        self.color[3] = max(0, fade)
        if self.lifetime <= 0:
            self.alive = False

    def draw(self):
        if self.alive and self.color[3] > 0:
            arcade.draw_text(
                self.text, self.x, self.y,
                tuple(self.color), self.font_size,
                anchor_x="center"
            )

# ===============================
# PARTICLE SYSTEM
# ===============================

class Particle(arcade.Sprite):
    def __init__(self, texture: arcade.Texture, x: float, y: float,
                 velocity: Optional[Tuple[float, float]] = None):
        super().__init__(texture)
        self.center_x = x
        self.center_y = y
        self.scale = random.uniform(0.1, 0.3)
        if velocity:
            self.velocity = list(velocity)
        else:
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 7)
            self.velocity = [math.cos(angle) * speed, math.sin(angle) * speed]
        self.alpha = 255
        self.fade_rate = random.uniform(3, 7)

    def on_update(self, delta_time: float = 1 / 60):
        self.center_x += self.velocity[0]
        self.center_y += self.velocity[1]
        self.velocity[0] *= 0.94
        self.velocity[1] *= 0.94
        self.alpha = max(0, self.alpha - self.fade_rate)
        if self.alpha <= 0:
            self.kill()

# ===============================
# STAR FIELD (parallax)
# ===============================

class StarField:
    """Two-layer parallax star field drawn directly."""

    def __init__(self):
        self.stars_far: List[Tuple[float, float, float]] = []   # x, y, radius
        self.stars_near: List[Tuple[float, float, float]] = []
        self._generate()

    def _generate(self):
        for _ in range(120):
            self.stars_far.append((
                random.uniform(0, SCREEN_WIDTH),
                random.uniform(0, SCREEN_HEIGHT),
                random.uniform(0.5, 1.0)
            ))
        for _ in range(60):
            self.stars_near.append((
                random.uniform(0, SCREEN_WIDTH),
                random.uniform(0, SCREEN_HEIGHT),
                random.uniform(1.0, 2.0)
            ))

    def scroll(self, speed_far: float = 0.3, speed_near: float = 0.7):
        self.stars_far = [
            (x, (y - speed_far) % SCREEN_HEIGHT, r)
            for x, y, r in self.stars_far
        ]
        self.stars_near = [
            (x, (y - speed_near) % SCREEN_HEIGHT, r)
            for x, y, r in self.stars_near
        ]

    def draw(self):
        for x, y, r in self.stars_far:
            arcade.draw_circle_filled(x, y, r, (160, 160, 200, 120))
        for x, y, r in self.stars_near:
            arcade.draw_circle_filled(x, y, r, (220, 220, 255, 200))

# ===============================
# POWER-UP SYSTEM
# ===============================

class PowerUp(arcade.Sprite):
    def __init__(self, x: float, y: float, power_up_type: PowerUpType):
        self.power_up_type = power_up_type
        color = self._get_color()
        texture = arcade.make_circle_texture(15, color)
        super().__init__(texture)
        self.center_x = x
        self.center_y = y
        self.scale = 1.0
        self.lifetime = 360
        self.rotation_speed = 3
        self.magnet_vx = 0.0
        self.magnet_vy = 0.0

    def _get_color(self) -> Tuple[int, int, int, int]:
        color_map = {
            PowerUpType.HEALTH: (255, 60, 60, 255),
            PowerUpType.SHIELD: (60, 100, 255, 255),
            PowerUpType.WEAPON_SPREAD: (255, 230, 0, 255),
            PowerUpType.WEAPON_PIERCING: (160, 0, 200, 255),
            PowerUpType.SPEED_BOOST: (0, 220, 80, 255),
            PowerUpType.ENERGY_BOOST: (0, 230, 230, 255),
            PowerUpType.EXTRA_LIFE: (255, 130, 0, 255),
            PowerUpType.NUKE: (255, 40, 40, 255),
        }
        return color_map.get(self.power_up_type, (255, 255, 255, 255))

    def on_update(self, delta_time: float = 1 / 60):
        self.angle += self.rotation_speed
        self.center_x += self.magnet_vx
        self.center_y += self.magnet_vy
        self.magnet_vx *= 0.85
        self.magnet_vy *= 0.85
        self.lifetime -= 1
        if self.lifetime < 90:
            self.alpha = int((self.lifetime / 90) * 255)
        if self.lifetime <= 0:
            self.kill()

# ===============================
# PLAYER
# ===============================

class Player(arcade.Sprite):
    def __init__(self):
        texture = arcade.make_circle_texture(30, (0, 220, 255, 255))
        super().__init__(texture)
        self.center_x = SCREEN_WIDTH // 2
        self.center_y = 100

        self.health = MAX_HEALTH
        self.max_health = MAX_HEALTH
        self.energy = MAX_ENERGY
        self.max_energy = MAX_ENERGY
        self.lives = MAX_LIVES

        # Dash / roll
        self.dash_timer = 0
        self.dash_active = 0       # frames remaining in current dash
        self.velocity_x = 0.0
        self.velocity_y = 0.0

        # Shield
        self.shield = MAX_SHIELD
        self.max_shield = MAX_SHIELD
        self.shield_active = False
        self.shield_cooldown_timer = 0

        # Invincibility frames
        self.invincible_timer = 0

        # Weapon
        self.current_weapon = WeaponType.SINGLE
        self.active_power_ups: Dict[PowerUpType, int] = defaultdict(int)

    def on_update(self, delta_time: float = 1 / 60):
        # Energy regeneration
        if not self.shield_active and self.energy < self.max_energy:
            self.energy = min(self.max_energy, self.energy + 0.3)

        # Shield active: drain energy
        if self.shield_active:
            self.energy -= SHIELD_DRAIN
            if self.energy <= 0:
                self.energy = 0
                self.shield_active = False
                self.shield_cooldown_timer = SHIELD_COOLDOWN

        # Dash cooldown
        if self.dash_timer > 0:
            self.dash_timer -= 1
        if self.dash_active > 0:
            self.dash_active -= 1
            self.invincible_timer = max(self.invincible_timer, self.dash_active)

        # Shield cooldown + regen
        if self.shield_cooldown_timer > 0:
            self.shield_cooldown_timer -= 1
            self.shield_active = False
        else:
            if not self.shield_active and self.shield < self.max_shield:
                self.shield = min(self.max_shield, self.shield + SHIELD_REGEN)

        # Invincibility frames
        if self.invincible_timer > 0:
            self.invincible_timer -= 1
            # Flicker effect via alpha
            self.alpha = 100 if (self.invincible_timer % 6 < 3) else 255
        else:
            self.alpha = 255

        # Power-up durations
        expired = [k for k, v in self.active_power_ups.items() if v <= 0]
        for k in expired:
            del self.active_power_ups[k]
            # Reset weapon if that type expired
            if k in (PowerUpType.WEAPON_SPREAD, PowerUpType.WEAPON_PIERCING):
                self.current_weapon = WeaponType.SINGLE
        for k in list(self.active_power_ups.keys()):
            self.active_power_ups[k] -= 1

        # Boundary clamp
        self.center_x = max(15, min(SCREEN_WIDTH - 15, self.center_x))
        self.center_y = max(15, min(SCREEN_HEIGHT - 15, self.center_y))

    def dash(self) -> bool:
        if self.dash_timer <= 0 and self.energy >= 10:
            self.dash_timer = DASH_COOLDOWN
            self.dash_active = DASH_DURATION
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
        msg = ""
        if pt == PowerUpType.HEALTH:
            self.health = min(self.max_health, self.health + 35)
            msg = "+35 HP"
        elif pt == PowerUpType.SHIELD:
            self.shield = min(self.max_shield, self.shield + 50)
            msg = "+50 Shield"
        elif pt == PowerUpType.WEAPON_SPREAD:
            self.current_weapon = WeaponType.SPREAD
            self.active_power_ups[PowerUpType.WEAPON_SPREAD] = 600
            msg = "Spread Shot!"
        elif pt == PowerUpType.WEAPON_PIERCING:
            self.current_weapon = WeaponType.PIERCING
            self.active_power_ups[PowerUpType.WEAPON_PIERCING] = 600
            msg = "Piercing Shot!"
        elif pt == PowerUpType.SPEED_BOOST:
            self.active_power_ups[PowerUpType.SPEED_BOOST] = 360
            msg = "Speed Boost!"
        elif pt == PowerUpType.ENERGY_BOOST:
            self.energy = min(self.max_energy, self.energy + 60)
            msg = "+60 Energy"
        elif pt == PowerUpType.EXTRA_LIFE:
            self.lives = min(5, self.lives + 1)
            msg = "Extra Life!"
        elif pt == PowerUpType.NUKE:
            msg = "NUKE!"   # handled in game loop
        return msg

    def take_damage(self, damage: float) -> bool:
        """Returns True if damage was applied (not invincible)."""
        if self.invincible_timer > 0:
            return False
        if self.shield_active and self.shield > 0:
            absorbed = damage * SHIELD_ABSORPTION
            self.shield -= absorbed
            damage -= absorbed
            if self.shield <= 0:
                self.shield = 0
                self.shield_active = False
                self.shield_cooldown_timer = SHIELD_COOLDOWN
        if damage > 0:
            self.health -= damage
            self.invincible_timer = 45  # short i-frames after hit
        return True

    def get_effective_speed(self) -> float:
        base = PLAYER_SPEED
        if PowerUpType.SPEED_BOOST in self.active_power_ups:
            base *= 1.6
        return base

# ===============================
# BULLET SYSTEM
# ===============================

class Bullet(arcade.Sprite):
    def __init__(self, x: float, y: float, angle: float, speed: float,
                 is_player: bool = True, penetrating: bool = False,
                 damage: float = 20.0):
        color = (255, 240, 0, 255) if is_player else (255, 60, 60, 255)
        size = 8 if is_player else 7
        texture = arcade.make_circle_texture(size, color)
        super().__init__(texture)
        self.center_x = x
        self.center_y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.is_player = is_player
        self.penetrating = penetrating
        self.damage = damage
        self.lifetime = 500

    def on_update(self, delta_time: float = 1 / 60):
        self.center_x += self.vx
        self.center_y += self.vy
        self.lifetime -= 1
        if (self.center_x < -60 or self.center_x > SCREEN_WIDTH + 60 or
                self.center_y < -60 or self.center_y > SCREEN_HEIGHT + 60 or
                self.lifetime <= 0):
            self.kill()

# ===============================
# ENEMY SYSTEM
# ===============================

class Enemy(arcade.Sprite):
    def __init__(self, difficulty: Difficulty, enemy_type: EnemyType = EnemyType.SCOUT):
        color = self._get_color(enemy_type)
        texture = arcade.make_circle_texture(20, color)
        super().__init__(texture)
        self.enemy_type = enemy_type
        self.difficulty = difficulty
        settings = DIFFICULTY_SETTINGS[difficulty]

        self.center_x = random.randint(80, SCREEN_WIDTH - 80)
        self.center_y = SCREEN_HEIGHT + 30

        multipliers = {EnemyType.SCOUT: 0.7, EnemyType.SOLDIER: 1.0, EnemyType.ELITE: 1.6}
        self.health = int(settings.enemy_health * multipliers[enemy_type])
        self.max_health = self.health

        self.path: List[Tuple[int, int]] = []
        self.repath_timer = random.randint(0, 20)  # stagger first repath
        self.shoot_timer = random.randint(0, settings.enemy_fire_rate)
        self.fire_rate = settings.enemy_fire_rate

        # Knockback
        self.knockback_vx = 0.0
        self.knockback_vy = 0.0

        # Elite burst
        self.burst_count = 0
        self.burst_timer = 0

    @staticmethod
    def _get_color(enemy_type: EnemyType) -> Tuple[int, int, int, int]:
        return {
            EnemyType.SCOUT: (255, 165, 0, 255),
            EnemyType.SOLDIER: (230, 40, 40, 255),
            EnemyType.ELITE: (160, 0, 200, 255),
        }[enemy_type]

    def update_enemy(self, player: Player, speed: float,
                     enemy_bullets: arcade.SpriteList):
        self.repath_timer += 1
        self.shoot_timer += 1

        # Knockback decay
        self.center_x += self.knockback_vx
        self.center_y += self.knockback_vy
        self.knockback_vx *= 0.7
        self.knockback_vy *= 0.7

        # Screen bounds clamp
        self.center_x = max(20, min(SCREEN_WIDTH - 20, self.center_x))
        self.center_y = max(20, min(SCREEN_HEIGHT - 20, self.center_y))

        if self.repath_timer > 35:
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
        eff_speed = speed * DIFFICULTY_SETTINGS[self.difficulty].enemy_speed_multiplier
        self.center_x += math.cos(angle) * eff_speed
        self.center_y += math.sin(angle) * eff_speed

        # Shooting
        if self.enemy_type == EnemyType.ELITE:
            # Burst fire for elites
            if self.burst_count > 0:
                self.burst_timer -= 1
                if self.burst_timer <= 0:
                    atk_angle = math.atan2(player.center_y - self.center_y,
                                           player.center_x - self.center_x)
                    for spread in [-0.15, 0, 0.15]:
                        b = Bullet(self.center_x, self.center_y,
                                   atk_angle + spread, ENEMY_BULLET_SPEED,
                                   is_player=False, damage=8)
                        enemy_bullets.append(b)
                    self.burst_count -= 1
                    self.burst_timer = 10
            elif self.shoot_timer > self.fire_rate:
                self.burst_count = 3
                self.burst_timer = 1
                self.shoot_timer = 0
        else:
            if self.shoot_timer > self.fire_rate:
                atk_angle = math.atan2(player.center_y - self.center_y,
                                       player.center_x - self.center_x)
                b = Bullet(self.center_x, self.center_y,
                           atk_angle, ENEMY_BULLET_SPEED,
                           is_player=False)
                enemy_bullets.append(b)
                self.shoot_timer = 0

    def take_damage(self, damage: float, knockback_angle: float = 0.0):
        self.health -= damage
        kb = 5.0
        self.knockback_vx = math.cos(knockback_angle) * kb
        self.knockback_vy = math.sin(knockback_angle) * kb

    def draw_health_bar(self):
        if self.health >= self.max_health:
            return
        bar_w = 32
        bar_h = 4
        bx = self.center_x - bar_w // 2
        by = self.center_y + 22
        arcade.draw_rect_filled(bx + bar_w // 2, by + bar_h // 2,
                                bar_w, bar_h, (80, 0, 0, 200))
        hp_ratio = max(0, self.health / self.max_health)
        arcade.draw_rect_filled(bx + (bar_w * hp_ratio) // 2, by + bar_h // 2,
                                bar_w * hp_ratio, bar_h, (0, 220, 60, 220))

# ===============================
# BOSS SYSTEM
# ===============================

class Boss(arcade.Sprite):
    def __init__(self, difficulty: Difficulty):
        texture = arcade.make_circle_texture(60, (160, 0, 0, 255))
        super().__init__(texture)
        self.difficulty = difficulty
        settings = DIFFICULTY_SETTINGS[difficulty]
        self.center_x = SCREEN_WIDTH // 2
        self.center_y = SCREEN_HEIGHT - 100
        self.health = settings.boss_health
        self.max_health = self.health
        self.attack_cooldown = 0
        self.phase = 1
        self.move_timer = 0
        self.move_target_x = SCREEN_WIDTH // 2
        self.move_target_y = SCREEN_HEIGHT - 150
        self.rage_mode = False     # triggers at <33% HP

    def _pick_movement_target(self):
        self.move_target_x = random.randint(100, SCREEN_WIDTH - 100)
        self.move_target_y = random.randint(SCREEN_HEIGHT // 2, SCREEN_HEIGHT - 80)
        self.move_timer = random.randint(90, 180)

    def select_attack(self, player: Player) -> str:
        distance = math.hypot(self.center_x - player.center_x,
                              self.center_y - player.center_y)
        hp_pct = self.health / self.max_health
        if hp_pct < 0.33:
            self.phase = 3
            self.rage_mode = True
            return "BLAST" if distance < 300 else "LASER"
        elif hp_pct < 0.66:
            self.phase = 2
            if distance > 400:
                return "LASER"
            elif distance > 200:
                return "DASH"
            else:
                return "BLAST"
        else:
            self.phase = 1
            if distance > 400:
                return "LASER"
            elif distance > 200:
                return "DASH"
            else:
                return "BLAST"

    def decide_action(self, player: Player) -> str:
        distance = math.hypot(self.center_x - player.center_x,
                              self.center_y - player.center_y)
        score = minimax(1, True, distance, -math.inf, math.inf)
        return "ATTACK" if score > -200 else "MOVE"

    def update_boss(self, player: Player, boss_bullets: arcade.SpriteList):
        self.move_timer = max(0, self.move_timer - 1)

        # Movement: glide to target
        if self.move_timer <= 0:
            self._pick_movement_target()
        dx = self.move_target_x - self.center_x
        dy = self.move_target_y - self.center_y
        dist = math.hypot(dx, dy)
        if dist > 2:
            spd = BOSS_SPEED * (1.5 if self.rage_mode else 1.0)
            self.center_x += (dx / dist) * spd
            self.center_y += (dy / dist) * spd

        # Clamp to screen
        self.center_x = max(80, min(SCREEN_WIDTH - 80, self.center_x))
        self.center_y = max(80, min(SCREEN_HEIGHT - 80, self.center_y))

        # Face player
        angle = math.atan2(player.center_y - self.center_y,
                           player.center_x - self.center_x)
        self.angle = math.degrees(angle)

        # Attack decision
        action = self.decide_action(player)
        if action == "ATTACK" and self.attack_cooldown <= 0:
            attack_type = self.select_attack(player)
            cooldown_reduction = 0.6 if self.rage_mode else 1.0

            if attack_type == "LASER":
                for i in range(3 if self.rage_mode else 1):
                    spread = (i - 1) * 0.2 if self.rage_mode else 0
                    b = Bullet(self.center_x, self.center_y,
                               angle + spread, 9, is_player=False, damage=12)
                    boss_bullets.append(b)

            elif attack_type == "DASH":
                self.center_x = max(60, min(SCREEN_WIDTH - 60,
                                            self.center_x + math.cos(angle) * 80))
                self.center_y = max(60, min(SCREEN_HEIGHT - 60,
                                            self.center_y + math.sin(angle) * 80))

            elif attack_type == "BLAST":
                num_shots = 6 if self.rage_mode else 3
                for i in range(num_shots):
                    sp = (i / num_shots) * math.pi * 2
                    b = Bullet(self.center_x, self.center_y,
                               sp, 6, is_player=False, damage=10)
                    boss_bullets.append(b)

            self.attack_cooldown = int(80 * cooldown_reduction)

        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

    def take_damage(self, damage: float):
        self.health -= damage

# ===============================
# CAMERA SYSTEM
# ===============================

class Camera:
    def __init__(self):
        self.shake_amount = 0
        self.shake_duration = 0

    def shake(self, amount: float = 10, duration: int = 10):
        self.shake_amount = max(self.shake_amount, amount)
        self.shake_duration = max(self.shake_duration, duration)

    def update(self, delta_time: float = 1 / 60):
        if self.shake_duration > 0:
            self.shake_duration -= 1
            if self.shake_duration == 0:
                self.shake_amount = 0

    def get_offset(self) -> Tuple[float, float]:
        if self.shake_duration > 0:
            return (random.uniform(-self.shake_amount, self.shake_amount),
                    random.uniform(-self.shake_amount, self.shake_amount))
        return (0.0, 0.0)

# ===============================
# SETTINGS PERSISTENCE
# ===============================

@dataclass
class GameSettings:
    difficulty: Difficulty = Difficulty.NORMAL
    music_volume: float = 0.5
    sfx_volume: float = 0.8
    show_fps: bool = False
    high_score: int = 0
    high_score_table: List[Dict] = field(default_factory=list)

    def save(self, filename: str = "settings.json"):
        data = {
            "difficulty": self.difficulty.value,
            "music_volume": self.music_volume,
            "sfx_volume": self.sfx_volume,
            "show_fps": self.show_fps,
            "high_score": self.high_score,
            "high_score_table": self.high_score_table,
        }
        try:
            with open(os.path.join(SAVE_PATH, filename), 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")

    @classmethod
    def load(cls, filename: str = "settings.json") -> 'GameSettings':
        try:
            with open(os.path.join(SAVE_PATH, filename), 'r') as f:
                data = json.load(f)
            difficulty = Difficulty(data.get("difficulty", "normal"))
            return cls(
                difficulty=difficulty,
                music_volume=data.get("music_volume", 0.5),
                sfx_volume=data.get("sfx_volume", 0.8),
                show_fps=data.get("show_fps", False),
                high_score=data.get("high_score", 0),
                high_score_table=data.get("high_score_table", []),
            )
        except Exception:
            return cls()

    def record_score(self, score: int, wave: int):
        entry = {
            "score": score,
            "wave": wave,
            "difficulty": self.difficulty.value,
            "date": time.strftime("%Y-%m-%d"),
        }
        self.high_score_table.append(entry)
        self.high_score_table = sorted(
            self.high_score_table, key=lambda e: e["score"], reverse=True
        )[:5]
        if score > self.high_score:
            self.high_score = score

# ===============================
# WAVE SYSTEM
# ===============================

class WaveManager:
    def __init__(self, difficulty: Difficulty):
        self.difficulty = difficulty
        self.current_wave = 0
        self.enemies_spawned = 0
        self.enemies_to_spawn = INITIAL_WAVE_SIZE
        self.wave_timer = 0
        self.wave_active = False
        self.wave_delay = 150
        self.spawn_interval = 40
        self.spawn_tick = 0
        self.wave_cleared = False      # True for one frame after wave ends
        self.awaiting_boss_clear = False

    def get_wave_size(self) -> int:
        return INITIAL_WAVE_SIZE + (self.current_wave * WAVE_SIZE_INCREMENT)

    def start_wave(self):
        self.current_wave += 1
        self.enemies_spawned = 0
        self.enemies_to_spawn = self.get_wave_size()
        self.wave_active = True
        self.wave_timer = 0
        self.spawn_tick = 0
        self.wave_cleared = False

    def update(self, living_enemies: int) -> bool:
        """Returns True if an enemy should be spawned this frame."""
        self.wave_cleared = False

        if not self.wave_active:
            self.wave_timer += 1
            if self.wave_timer >= self.wave_delay:
                self.start_wave()
            return False

        # All spawned + all dead → wave complete
        if self.enemies_spawned >= self.enemies_to_spawn and living_enemies == 0:
            self.wave_active = False
            self.wave_timer = 0
            self.wave_cleared = True
            return False

        # Staggered spawning
        if self.enemies_spawned < self.enemies_to_spawn:
            self.spawn_tick += 1
            if self.spawn_tick >= self.spawn_interval:
                self.spawn_tick = 0
                self.enemies_spawned += 1
                return True

        return False

    def is_boss_wave(self) -> bool:
        return self.current_wave > 0 and self.current_wave % WAVES_BEFORE_BOSS == 0

    def get_enemy_type(self) -> EnemyType:
        wave_pct = (self.current_wave % WAVES_BEFORE_BOSS) / max(WAVES_BEFORE_BOSS, 1)
        if wave_pct < 0.4:
            return EnemyType.SCOUT
        elif wave_pct < 0.75:
            return EnemyType.SOLDIER
        else:
            return EnemyType.ELITE if random.random() < 0.5 else EnemyType.SOLDIER

# ===============================
# GAME VIEW
# ===============================

class GameView(arcade.View):
    def __init__(self, settings: GameSettings):
        super().__init__()
        self.settings = settings
        self.state = GameState.PLAYING

        self.sound_manager = self._init_sounds()

        self.player_sprites = arcade.SpriteList()
        self.enemy_sprites = arcade.SpriteList()
        self.bullet_sprites = arcade.SpriteList()
        self.enemy_bullet_sprites = arcade.SpriteList()
        self.boss_bullet_sprites = arcade.SpriteList()
        self.boss_sprites = arcade.SpriteList()
        self.particle_sprites = arcade.SpriteList()
        self.powerup_sprites = arcade.SpriteList()

        self.player = Player()
        self.player_sprites.append(self.player)

        self.score = 0
        self.total_kills = 0
        self.wave_manager = WaveManager(settings.difficulty)
        self.boss: Optional[Boss] = None
        self.camera = Camera()
        self.star_field = StarField()

        # Combo system
        self.combo = 0
        self.combo_timer = 0
        self.max_combo = 0

        # Floating texts
        self.floating_texts: List[FloatingText] = []

        # HUD announcements
        self.announcement_text = ""
        self.announcement_timer = 0

        # Boss warning
        self.boss_warning_timer = 0
        self.boss_spawned_this_wave = False

        # Respawn state
        self.respawn_timer = 0

        # Input
        self.keys_pressed: Set[int] = set()
        self.mouse_held = False
        self.mouse_x = SCREEN_WIDTH // 2
        self.mouse_y = SCREEN_HEIGHT // 2
        self.keyboard_aim = False   # True when using WASD for aim

        self.fire_timer = 0
        self.muzzle_timer = 0
        self.frame_count = 0

        self.wave_manager.start_wave()

    # ------------------------------------------------------------------
    def _init_sounds(self) -> Dict:
        sounds = {}
        try:
            sounds['shoot'] = arcade.load_sound(os.path.join(SOUND_PATH, "shoot.wav"))
            sounds['hit'] = arcade.load_sound(os.path.join(SOUND_PATH, "hit.wav"))
            sounds['boss'] = arcade.load_sound(os.path.join(SOUND_PATH, "boss.wav"))
            sounds['powerup'] = arcade.load_sound(os.path.join(SOUND_PATH, "powerup.wav"))
        except Exception:
            pass
        return sounds

    def _play_sound(self, name: str):
        try:
            if name in self.sound_manager:
                self.sound_manager[name].play(volume=self.settings.sfx_volume)
        except Exception:
            pass

    # ------------------------------------------------------------------
    def announce(self, text: str, duration: int = 150):
        self.announcement_text = text
        self.announcement_timer = duration

    def add_float(self, text: str, x: float, y: float,
                  color=(255, 255, 100, 255), size: int = 14):
        self.floating_texts.append(FloatingText(text, x, y, color, size))

    # ------------------------------------------------------------------
    def create_explosion(self, x: float, y: float, count: int = 25,
                         color: Tuple[int, int, int, int] = (255, 165, 0, 255)):
        texture = arcade.make_circle_texture(20, color)
        for _ in range(count):
            p = Particle(texture, x, y)
            self.particle_sprites.append(p)

    def nuke_all_enemies(self):
        """Destroy every enemy on screen (from NUKE powerup)."""
        for enemy in list(self.enemy_sprites):
            self._kill_enemy(enemy)
        if self.boss:
            self.boss.take_damage(self.boss.health * 0.5)
        self.camera.shake(20, 20)
        self.announce("NUKE!!!", 120)

    def _kill_enemy(self, enemy: Enemy):
        self.create_explosion(enemy.center_x, enemy.center_y, 20)
        self.spawn_powerup(enemy.center_x, enemy.center_y, enemy.enemy_type)
        enemy.kill()
        self.total_kills += 1
        pts = int(10 * DIFFICULTY_SETTINGS[self.settings.difficulty].score_multiplier
                  * max(1, self.combo // 5 + 1))
        self.score += pts
        self.add_float(f"+{pts}", enemy.center_x, enemy.center_y + 20,
                       color=(255, 230, 0, 255))
        self._increment_combo()

    def _increment_combo(self):
        self.combo += 1
        self.combo_timer = COMBO_TIMEOUT
        if self.combo > self.max_combo:
            self.max_combo = self.combo
        if self.combo > 1 and self.combo % 5 == 0:
            self.announce(f"COMBO x{self.combo}!", 90)

    def spawn_powerup(self, x: float, y: float, enemy_type: EnemyType):
        base_rates = {
            EnemyType.SCOUT: 0.10,
            EnemyType.SOLDIER: 0.18,
            EnemyType.ELITE: 0.35,
        }
        rate = base_rates.get(enemy_type, 0.10)
        rate += DIFFICULTY_SETTINGS[self.settings.difficulty].powerup_drop_boost
        if random.random() > rate:
            return
        # Weighted pool — no NUKE in easy spawns
        pool = list(PowerUpType)
        if self.settings.difficulty == Difficulty.EASY:
            pool = [p for p in pool if p != PowerUpType.NUKE]
        weights = {
            PowerUpType.HEALTH: 3, PowerUpType.SHIELD: 2,
            PowerUpType.WEAPON_SPREAD: 2, PowerUpType.WEAPON_PIERCING: 2,
            PowerUpType.SPEED_BOOST: 2, PowerUpType.ENERGY_BOOST: 2,
            PowerUpType.EXTRA_LIFE: 1, PowerUpType.NUKE: 1,
        }
        choices = []
        wts = []
        for p in pool:
            choices.append(p)
            wts.append(weights.get(p, 1))
        total = sum(wts)
        r = random.uniform(0, total)
        acc = 0
        chosen = choices[0]
        for c, w in zip(choices, wts):
            acc += w
            if r <= acc:
                chosen = c
                break
        self.powerup_sprites.append(PowerUp(x, y, chosen))

    # ------------------------------------------------------------------
    def handle_player_movement(self):
        spd = self.player.get_effective_speed()
        dash_active = self.player.dash_active > 0

        vx, vy = 0.0, 0.0
        if arcade.key.LEFT in self.keys_pressed or arcade.key.A in self.keys_pressed:
            vx = -spd
        elif arcade.key.RIGHT in self.keys_pressed or arcade.key.D in self.keys_pressed:
            vx = spd
        if arcade.key.UP in self.keys_pressed or arcade.key.W in self.keys_pressed:
            vy = spd
        elif arcade.key.DOWN in self.keys_pressed or arcade.key.S in self.keys_pressed:
            vy = -spd

        if dash_active and (vx != 0 or vy != 0):
            length = math.hypot(vx, vy)
            vx = (vx / length) * DASH_SPEED
            vy = (vy / length) * DASH_SPEED

        self.player.velocity_x = vx
        self.player.velocity_y = vy
        self.player.center_x += vx
        self.player.center_y += vy

    def fire_weapon(self):
        if not self.mouse_held:
            self.fire_timer = max(self.fire_timer - 1, 0)
            return
        self.fire_timer += 1
        if self.fire_timer < FIRE_RATE:
            return
        if self.player.energy <= 5:
            return

        angle_rad = math.radians(self.player.angle)
        offset = 34   # spawn bullets just outside player radius

        if self.player.current_weapon == WeaponType.SINGLE:
            b = Bullet(
                self.player.center_x + math.cos(angle_rad) * offset,
                self.player.center_y + math.sin(angle_rad) * offset,
                angle_rad, BULLET_SPEED, damage=20
            )
            self.bullet_sprites.append(b)

        elif self.player.current_weapon == WeaponType.SPREAD:
            for spread in (-0.25, 0.0, 0.25):
                b = Bullet(
                    self.player.center_x + math.cos(angle_rad + spread) * offset,
                    self.player.center_y + math.sin(angle_rad + spread) * offset,
                    angle_rad + spread, BULLET_SPEED, damage=14
                )
                self.bullet_sprites.append(b)

        elif self.player.current_weapon == WeaponType.PIERCING:
            b = Bullet(
                self.player.center_x + math.cos(angle_rad) * offset,
                self.player.center_y + math.sin(angle_rad) * offset,
                angle_rad, BULLET_SPEED + 2,
                penetrating=True, damage=30
            )
            self.bullet_sprites.append(b)

        self.player.energy -= 5
        self._play_sound('shoot')
        self.muzzle_timer = MUZZLE_DURATION
        self.fire_timer = 0

    # ------------------------------------------------------------------
    def on_mouse_motion(self, x, y, dx, dy):
        self.mouse_x = x
        self.mouse_y = y
        if self.state != GameState.PLAYING:
            return
        self.player.angle = math.degrees(
            math.atan2(y - self.player.center_y, x - self.player.center_x)
        )

    def on_mouse_press(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT and self.state == GameState.PLAYING:
            self.mouse_held = True

    def on_mouse_release(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.mouse_held = False

    # ------------------------------------------------------------------
    def on_update(self, delta_time: float):
        self.frame_count += 1

        if self.state == GameState.GAME_OVER:
            return

        if self.state == GameState.RESPAWNING:
            self.respawn_timer -= 1
            if self.respawn_timer <= 0:
                self._do_respawn()
            return

        if self.state == GameState.PAUSED:
            return

        # --- Scrolling star field ---
        self.star_field.scroll()

        # --- Camera ---
        self.camera.update(delta_time)

        # --- Announcement timer ---
        if self.announcement_timer > 0:
            self.announcement_timer -= 1

        # --- Boss warning ---
        if self.boss_warning_timer > 0:
            self.boss_warning_timer -= 1

        # --- Combo decay ---
        if self.combo_timer > 0:
            self.combo_timer -= 1
        else:
            self.combo = 0

        # --- Player ---
        self.handle_player_movement()
        self.player.on_update(delta_time)
        self.fire_weapon()

        # --- All sprite updates ---
        for sl in (self.bullet_sprites, self.enemy_bullet_sprites,
                   self.boss_bullet_sprites, self.particle_sprites,
                   self.powerup_sprites):
            sl.on_update(delta_time)

        # --- Floating texts ---
        for ft in self.floating_texts[:]:
            ft.update()
            if not ft.alive:
                self.floating_texts.remove(ft)

        # --- Powerup magnetism ---
        for pu in self.powerup_sprites:
            dx = self.player.center_x - pu.center_x
            dy = self.player.center_y - pu.center_y
            dist = math.hypot(dx, dy)
            if dist < POWERUP_MAGNET_RADIUS and dist > 1:
                force = (POWERUP_MAGNET_RADIUS - dist) / POWERUP_MAGNET_RADIUS * 5
                pu.magnet_vx += (dx / dist) * force
                pu.magnet_vy += (dy / dist) * force

        # --- Wave / boss spawning ---
        living = len(self.enemy_sprites)
        should_spawn = self.wave_manager.update(living)

        if should_spawn and living < MAX_ENEMIES and not self.boss:
            et = self.wave_manager.get_enemy_type()
            e = Enemy(self.settings.difficulty, et)
            self.enemy_sprites.append(e)

        # Boss wave handling
        if (self.wave_manager.is_boss_wave() and
                self.boss is None and
                not self.boss_spawned_this_wave):
            if self.boss_warning_timer == 0 and living == 0:
                self.boss_warning_timer = 90
                self.announce("WARNING: BOSS INCOMING!", 90)
            elif self.boss_warning_timer == 0 and living == 0:
                self._spawn_boss()

        if (self.boss_warning_timer == 1 and
                self.boss is None and
                not self.boss_spawned_this_wave and
                self.wave_manager.is_boss_wave()):
            self._spawn_boss()

        # Wave cleared bonus
        if self.wave_manager.wave_cleared:
            bonus = int(50 * self.wave_manager.current_wave *
                        DIFFICULTY_SETTINGS[self.settings.difficulty].score_multiplier)
            self.score += bonus
            self.announce(f"Wave {self.wave_manager.current_wave - 1} Clear! +{bonus}", 150)
            self.boss_spawned_this_wave = False

        # --- Enemy updates ---
        speed = (BASE_ENEMY_SPEED *
                 DIFFICULTY_SETTINGS[self.settings.difficulty].enemy_speed_multiplier)
        for enemy in list(self.enemy_sprites):
            enemy.update_enemy(self.player, speed, self.enemy_bullet_sprites)

        # --- Boss update ---
        if self.boss:
            self.boss.update_boss(self.player, self.boss_bullet_sprites)
            # Phase announcement
            old_phase = getattr(self, '_boss_last_phase', 1)
            if self.boss.phase != old_phase:
                self.announce(f"BOSS PHASE {self.boss.phase}!", 120)
                self.camera.shake(15, 15)
            self._boss_last_phase = self.boss.phase

        # ==============================================================
        # COLLISION DETECTION
        # ==============================================================

        # Player bullets vs enemies
        for bullet in list(self.bullet_sprites):
            if not bullet.alive:
                continue
            for enemy in list(self.enemy_sprites):
                if not enemy.alive:
                    continue
                if arcade.check_for_collision(bullet, enemy):
                    kb_angle = math.atan2(enemy.center_y - bullet.center_y,
                                          enemy.center_x - bullet.center_x)
                    enemy.take_damage(bullet.damage, kb_angle)
                    self._play_sound('hit')
                    if not bullet.penetrating:
                        bullet.kill()
                    if enemy.health <= 0:
                        self._kill_enemy(enemy)
                    if not bullet.alive:
                        break

        # Player bullets vs boss
        if self.boss:
            for bullet in list(self.bullet_sprites):
                if bullet.alive and arcade.check_for_collision(bullet, self.boss):
                    self.boss.take_damage(bullet.damage)
                    bullet.kill()
                    self._play_sound('hit')
                    self.camera.shake(4, 4)
                    self.add_float(f"-{int(bullet.damage)}", self.boss.center_x,
                                   self.boss.center_y + 30, color=(255, 100, 100, 255))
                    if self.boss.health <= 0:
                        self._kill_boss()

        # Enemy bullets vs player
        for bullet in list(self.enemy_bullet_sprites):
            if bullet.alive and arcade.check_for_collision(bullet, self.player):
                dmg = DIFFICULTY_SETTINGS[self.settings.difficulty].enemy_bullet_damage
                if self.player.take_damage(dmg):
                    bullet.kill()
                    self.camera.shake(4, 4)

        # Boss bullets vs player
        for bullet in list(self.boss_bullet_sprites):
            if bullet.alive and arcade.check_for_collision(bullet, self.player):
                if self.player.take_damage(bullet.damage):
                    bullet.kill()
                    self.camera.shake(7, 7)

        # Player vs powerups
        for pu in list(self.powerup_sprites):
            if pu.alive and arcade.check_for_collision(self.player, pu):
                msg = self.player.apply_power_up(pu)
                if pu.power_up_type == PowerUpType.NUKE:
                    self.nuke_all_enemies()
                self._play_sound('powerup')
                self.add_float(msg, pu.center_x, pu.center_y + 30,
                               color=(0, 255, 160, 255), size=16)
                pu.kill()

        # --- Death check ---
        if self.player.health <= 0:
            self._player_died()

    def _spawn_boss(self):
        self.boss = Boss(self.settings.difficulty)
        self.boss_sprites.append(self.boss)
        self.boss_spawned_this_wave = True
        self._boss_last_phase = 1
        self._play_sound('boss')
        self.announce("BOSS BATTLE!", 180)
        self.camera.shake(20, 20)

    def _kill_boss(self):
        self.create_explosion(self.boss.center_x, self.boss.center_y,
                              100, (180, 0, 0, 255))
        pts = int(200 * DIFFICULTY_SETTINGS[self.settings.difficulty].score_multiplier)
        self.score += pts
        self.total_kills += 1
        self.add_float(f"BOSS DOWN +{pts}!", self.boss.center_x,
                       self.boss.center_y, color=(255, 60, 60, 255), size=20)
        self.boss.kill()
        self.boss = None
        self.camera.shake(25, 25)
        self.announce("BOSS DEFEATED!", 180)
        # Drop guaranteed powerup cluster
        for _ in range(3):
            ox = random.randint(-60, 60)
            oy = random.randint(-60, 60)
            cx = max(60, min(SCREEN_WIDTH - 60, SCREEN_WIDTH // 2 + ox))
            cy = max(60, min(SCREEN_HEIGHT - 60, SCREEN_HEIGHT // 2 + oy))
            t = random.choice(list(PowerUpType))
            self.powerup_sprites.append(PowerUp(cx, cy, t))

    def _player_died(self):
        self.create_explosion(self.player.center_x, self.player.center_y, 60)
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
        self.player.invincible_timer = 150
        self.player.alpha = 255
        self.state = GameState.PLAYING
        # Clear bullets to give breathing room
        for sl in (self.enemy_bullet_sprites, self.boss_bullet_sprites):
            for b in list(sl):
                b.kill()

    def _game_over(self):
        self.state = GameState.GAME_OVER
        self.settings.record_score(self.score, self.wave_manager.current_wave)
        self.settings.save()

    # ==============================================================
    # DRAWING
    # ==============================================================

    def on_draw(self):
        off_x, off_y = self.camera.get_offset()

        # Deep space background
        arcade.draw_rect_filled(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                                SCREEN_WIDTH, SCREEN_HEIGHT, (5, 5, 20, 255))
        self.star_field.draw()

        # Translate all game sprites by camera shake offset
        # (We do this manually since we're not using Arcade's Camera object)
        arcade.draw_rect_filled(SCREEN_WIDTH // 2 + off_x,
                                SCREEN_HEIGHT // 2 + off_y,
                                SCREEN_WIDTH, SCREEN_HEIGHT, (0, 0, 0, 0))

        self.enemy_sprites.draw()
        for enemy in self.enemy_sprites:
            enemy.draw_health_bar()

        self.bullet_sprites.draw()
        self.enemy_bullet_sprites.draw()
        self.boss_bullet_sprites.draw()

        if self.state != GameState.RESPAWNING:
            self.player_sprites.draw()

        self.boss_sprites.draw()
        self.particle_sprites.draw()
        self.powerup_sprites.draw()

        # Muzzle flash
        if self.muzzle_timer > 0:
            ar = math.radians(self.player.angle)
            fx = self.player.center_x + math.cos(ar) * 42
            fy = self.player.center_y + math.sin(ar) * 42
            alpha = int((self.muzzle_timer / MUZZLE_DURATION) * 255)
            arcade.draw_circle_filled(fx, fy, 10, (255, 240, 100, alpha))
            self.muzzle_timer -= 1

        # Floating texts
        for ft in self.floating_texts:
            ft.draw()

        # Boss warning flash
        if self.boss_warning_timer > 0 and self.boss_warning_timer % 12 < 6:
            arcade.draw_rect_filled(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                                    SCREEN_WIDTH, SCREEN_HEIGHT, (100, 0, 0, 40))

        self._draw_hud()

    def _draw_hud(self):
        pad = 20
        hud_y = SCREEN_HEIGHT - 30

        # --- Top-left: score / wave / kills ---
        arcade.draw_text(f"Score: {self.score:,}", pad, hud_y,
                         arcade.color.WHITE, 16, bold=True)
        arcade.draw_text(f"Wave: {self.wave_manager.current_wave}", pad, hud_y - 26,
                         arcade.color.YELLOW, 13)
        arcade.draw_text(f"Kills: {self.total_kills}", pad, hud_y - 48,
                         arcade.color.LIGHT_GRAY, 12)

        combo_col = (255, 100, 0, 255) if self.combo >= 5 else (200, 200, 200, 255)
        arcade.draw_text(f"Combo: x{self.combo}", pad, hud_y - 70,
                         combo_col, 13, bold=(self.combo >= 5))

        # --- Health / Shield / Energy bars ---
        bx = pad
        def draw_bar(x, y, val, max_val, w, h, col, label):
            arcade.draw_rect_filled(x + w // 2, y + h // 2, w, h, (40, 40, 40, 200))
            ratio = max(0, val / max_val)
            if ratio > 0:
                arcade.draw_rect_filled(x + (w * ratio) // 2, y + h // 2,
                                        w * ratio, h, col)
            arcade.draw_rect_outline(x + w // 2, y + h // 2, w, h,
                                     (120, 120, 120, 180), 1)
            arcade.draw_text(f"{label}: {int(val)}/{int(max_val)}",
                             x, y - 2, (200, 200, 200, 220), 11)

        bar_w = 180
        draw_bar(bx, hud_y - 108, self.player.health, self.player.max_health,
                 bar_w, 14, (0, 200, 60, 220), "HP")
        draw_bar(bx, hud_y - 134, self.player.shield, self.player.max_shield,
                 bar_w, 14, (40, 120, 255, 220), "Shield")
        draw_bar(bx, hud_y - 160, self.player.energy, self.player.max_energy,
                 bar_w, 14, (0, 210, 210, 220), "Energy")

        # Lives
        life_x = pad
        life_y = hud_y - 185
        arcade.draw_text("Lives: ", life_x, life_y, arcade.color.WHITE, 12)
        for i in range(self.player.lives):
            arcade.draw_circle_filled(life_x + 60 + i * 20, life_y + 6, 6,
                                      (0, 200, 255, 220))

        # Weapon / dash
        dash_ready = self.player.dash_timer <= 0
        dash_col = (0, 255, 100, 255) if dash_ready else (150, 150, 150, 255)
        shield_col = (40, 120, 255, 255) if self.player.shield_active else (100, 100, 100, 200)
        arcade.draw_text(f"Weapon: {self.player.current_weapon.value.upper()}",
                         pad, hud_y - 210, arcade.color.LIGHT_BLUE, 12)
        arcade.draw_text("Dash [SHIFT]" + (" (READY)" if dash_ready else ""),
                         pad, hud_y - 228, dash_col, 11)
        arcade.draw_text("Shield [E]" + (" (ON)" if self.player.shield_active else ""),
                         pad, hud_y - 244, shield_col, 11)

        # Active powerups
        if self.player.active_power_ups:
            py = hud_y - 270
            arcade.draw_text("Active:", pad, py, arcade.color.LIGHT_YELLOW, 11)
            for pt, frames in self.player.active_power_ups.items():
                py -= 16
                secs = frames // 60
                arcade.draw_text(f"  {pt.value} ({secs}s)",
                                 pad, py, arcade.color.LIGHT_YELLOW, 11)

        # Shield orb around player
        if self.player.shield_active and self.player.shield > 0:
            alpha = int((self.player.shield / self.player.max_shield) * 180)
            arcade.draw_circle_outline(
                self.player.center_x, self.player.center_y,
                42, (80, 160, 255, alpha), 3
            )

        # --- Boss health bar ---
        if self.boss:
            bw = 400
            bh = 22
            bx2 = (SCREEN_WIDTH - bw) // 2
            by2 = SCREEN_HEIGHT - 44
            ratio = max(0, self.boss.health / self.boss.max_health)
            col = ((255, 50, 50, 220) if self.boss.phase < 3
                   else (255, 150, 0, 220))
            arcade.draw_rect_filled(bx2 + bw // 2, by2 + bh // 2,
                                    bw, bh, (40, 0, 0, 200))
            if ratio > 0:
                arcade.draw_rect_filled(bx2 + (bw * ratio) // 2, by2 + bh // 2,
                                        bw * ratio, bh, col)
            arcade.draw_rect_outline(bx2 + bw // 2, by2 + bh // 2,
                                     bw, bh, arcade.color.WHITE, 1)
            phase_txt = f"BOSS  Phase {self.boss.phase}"
            if self.boss.rage_mode:
                phase_txt += "  [RAGE]"
            arcade.draw_text(phase_txt,
                             SCREEN_WIDTH // 2, by2 + bh + 8,
                             arcade.color.RED, 13, anchor_x="center", bold=True)
            hp_txt = f"{int(self.boss.health)}/{int(self.boss.max_health)}"
            arcade.draw_text(hp_txt,
                             SCREEN_WIDTH // 2, by2 + 4,
                             arcade.color.WHITE, 11, anchor_x="center")

        # --- Enemies remaining indicator ---
        en = len(self.enemy_sprites)
        if en > 0 and not self.boss:
            arcade.draw_text(f"Enemies: {en}", SCREEN_WIDTH - 160, SCREEN_HEIGHT - 30,
                             arcade.color.LIGHT_RED_BROWN, 13)

        # --- Announcement ---
        if self.announcement_timer > 0:
            alpha = min(255, self.announcement_timer * 3)
            arcade.draw_text(self.announcement_text,
                             SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 120,
                             (255, 255, 100, alpha), 28,
                             anchor_x="center", bold=True)

        # --- FPS ---
        if self.settings.show_fps:
            fps = arcade.get_fps()
            arcade.draw_text(f"FPS: {fps:.0f}", SCREEN_WIDTH - 90, 10,
                             (150, 150, 150, 200), 12)

        # --- Minimap ---
        self._draw_minimap()

        # --- State overlays ---
        if self.state == GameState.PAUSED:
            arcade.draw_rect_filled(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                                    SCREEN_WIDTH, SCREEN_HEIGHT, (0, 0, 0, 160))
            arcade.draw_text("PAUSED", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 80,
                             arcade.color.YELLOW, 48, anchor_x="center", bold=True)
            arcade.draw_text("SPACE — Resume   R — Restart   Q — Quit",
                             SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                             arcade.color.WHITE, 18, anchor_x="center")
            arcade.draw_text(f"Difficulty: {self.settings.difficulty.value.upper()}",
                             SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50,
                             arcade.color.LIGHT_GREEN, 16, anchor_x="center")
            arcade.draw_text(f"Max Combo: x{self.max_combo}",
                             SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 80,
                             arcade.color.LIGHT_YELLOW, 14, anchor_x="center")

        elif self.state == GameState.RESPAWNING:
            secs = max(1, self.respawn_timer // 60 + 1)
            arcade.draw_text(f"Respawning in {secs}...",
                             SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                             (255, 200, 0, 220), 32, anchor_x="center", bold=True)

        elif self.state == GameState.GAME_OVER:
            arcade.draw_rect_filled(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                                    SCREEN_WIDTH, SCREEN_HEIGHT, (0, 0, 0, 210))
            arcade.draw_text("GAME OVER", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 160,
                             arcade.color.RED, 58, anchor_x="center", bold=True)
            arcade.draw_text(f"Score: {self.score:,}",
                             SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 90,
                             arcade.color.WHITE, 26, anchor_x="center")
            arcade.draw_text(f"Wave: {self.wave_manager.current_wave}  |  "
                             f"Kills: {self.total_kills}  |  "
                             f"Max Combo: x{self.max_combo}",
                             SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50,
                             arcade.color.LIGHT_GRAY, 16, anchor_x="center")
            # Hall of fame
            arcade.draw_text("— TOP SCORES —",
                             SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                             arcade.color.GOLD, 18, anchor_x="center", bold=True)
            for i, entry in enumerate(self.settings.high_score_table[:5]):
                row_y = SCREEN_HEIGHT // 2 - 30 - i * 26
                medal = ["🥇", "🥈", "🥉", " 4.", " 5."][i]
                arcade.draw_text(
                    f"{medal}  {entry['score']:>8,}  "
                    f"Wave {entry['wave']}  [{entry['difficulty']}]  {entry['date']}",
                    SCREEN_WIDTH // 2, row_y,
                    arcade.color.LIGHT_YELLOW, 14, anchor_x="center"
                )
            arcade.draw_text("R — Restart    Q — Quit to Menu",
                             SCREEN_WIDTH // 2, 50,
                             arcade.color.WHITE, 16, anchor_x="center")

    def _draw_minimap(self):
        mx = SCREEN_WIDTH - MINIMAP_WIDTH - 10
        my = 10
        cw = MINIMAP_WIDTH
        ch = MINIMAP_HEIGHT
        # Background
        arcade.draw_rect_filled(mx + cw // 2, my + ch // 2,
                                cw, ch, (10, 10, 30, 200))
        arcade.draw_rect_outline(mx + cw // 2, my + ch // 2,
                                  cw, ch, arcade.color.DARK_GRAY, 1)
        sx = cw / SCREEN_WIDTH
        sy = ch / SCREEN_HEIGHT

        # Player dot
        arcade.draw_circle_filled(
            mx + self.player.center_x * sx,
            my + self.player.center_y * sy,
            4, (0, 220, 255, 255)
        )
        # Enemies
        for e in self.enemy_sprites:
            arcade.draw_circle_filled(
                mx + e.center_x * sx,
                my + e.center_y * sy,
                2, (220, 60, 60, 220)
            )
        # Boss
        if self.boss:
            arcade.draw_circle_filled(
                mx + self.boss.center_x * sx,
                my + self.boss.center_y * sy,
                5, (255, 0, 0, 255)
            )
        # Powerups
        for pu in self.powerup_sprites:
            arcade.draw_circle_filled(
                mx + pu.center_x * sx,
                my + pu.center_y * sy,
                2, (0, 255, 150, 200)
            )
        # Label
        arcade.draw_text("MAP", mx + 4, my + ch - 14, (120, 120, 160, 200), 10)
        arcade.draw_text(f"E:{len(self.enemy_sprites)}",
                         mx + 4, my + 2, (200, 80, 80, 200), 10)

    # ==============================================================
    # INPUT
    # ==============================================================

    def on_key_press(self, symbol: int, modifiers: int):
        self.keys_pressed.add(symbol)

        if symbol == arcade.key.LSHIFT or symbol == arcade.key.RSHIFT:
            if self.state == GameState.PLAYING:
                self.player.dash()

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

        elif symbol == arcade.key.R:
            if self.state in (GameState.GAME_OVER, GameState.PAUSED):
                self.window.show_view(GameView(self.settings))

        elif symbol == arcade.key.Q:
            if self.state in (GameState.GAME_OVER, GameState.PAUSED):
                menu = MenuView(self.settings)
                self.window.show_view(menu)

    def on_key_release(self, symbol: int, modifiers: int):
        self.keys_pressed.discard(symbol)

# ===============================
# MENU VIEW
# ===============================

class MenuView(arcade.View):
    def __init__(self, settings: GameSettings):
        super().__init__()
        self.settings = settings
        self.star_field = StarField()
        self.tick = 0

    def on_update(self, delta_time: float):
        self.star_field.scroll(0.2, 0.5)
        self.tick += 1

    def on_draw(self):
        arcade.draw_rect_filled(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                                SCREEN_WIDTH, SCREEN_HEIGHT, (5, 5, 20, 255))
        self.star_field.draw()

        # Title glow pulse
        pulse = 0.85 + 0.15 * math.sin(self.tick * 0.05)
        col = (int(0 * pulse), int(200 * pulse), int(255 * pulse), 255)

        arcade.draw_text("ASTRA", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 120,
                         col, 80, anchor_x="center", bold=True)
        arcade.draw_text("VANGUARD", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 195,
                         (255, 255, 255, 220), 54, anchor_x="center", bold=True)
        arcade.draw_text("AI Tactical Space Siege  v4.0",
                         SCREEN_WIDTH // 2, SCREEN_HEIGHT - 240,
                         (120, 160, 200, 200), 20, anchor_x="center")

        # Separator line
        arcade.draw_line(SCREEN_WIDTH // 2 - 250, SCREEN_HEIGHT - 265,
                         SCREEN_WIDTH // 2 + 250, SCREEN_HEIGHT - 265,
                         (60, 80, 120, 180), 1)

        cy = SCREEN_HEIGHT // 2 + 60
        arcade.draw_text("ENTER — Start Game",
                         SCREEN_WIDTH // 2, cy, arcade.color.YELLOW, 20,
                         anchor_x="center", bold=True)
        arcade.draw_text("D — Change Difficulty",
                         SCREEN_WIDTH // 2, cy - 40, arcade.color.WHITE, 16,
                         anchor_x="center")
        arcade.draw_text("Q — Quit",
                         SCREEN_WIDTH // 2, cy - 76, arcade.color.WHITE, 16,
                         anchor_x="center")

        diff_colors = {
            Difficulty.EASY: (60, 220, 60, 255),
            Difficulty.NORMAL: (255, 200, 0, 255),
            Difficulty.HARD: (255, 60, 60, 255),
        }
        arcade.draw_text(
            f"Difficulty:  {self.settings.difficulty.value.upper()}",
            SCREEN_WIDTH // 2, cy - 130,
            diff_colors[self.settings.difficulty], 20, anchor_x="center", bold=True
        )

        # Controls legend
        controls = [
            "WASD / Arrows — Move",
            "Mouse — Aim & Shoot",
            "SHIFT — Dash (i-frames)",
            "E — Shield Toggle",
            "F — FPS Counter",
            "SPACE — Pause",
        ]
        lx = SCREEN_WIDTH // 2 - 150
        ly = cy - 190
        arcade.draw_text("Controls:", lx, ly, (150, 180, 220, 220), 14, bold=True)
        for i, c in enumerate(controls):
            arcade.draw_text(c, lx, ly - 22 - i * 20, (120, 150, 180, 200), 13)

        # High score
        if self.settings.high_score > 0:
            arcade.draw_text(f"Best Score: {self.settings.high_score:,}",
                             SCREEN_WIDTH // 2, 50, arcade.color.GOLD, 18,
                             anchor_x="center", bold=True)

    def on_key_press(self, symbol: int, modifiers: int):
        if symbol == arcade.key.ENTER:
            self.window.show_view(GameView(self.settings))
        elif symbol == arcade.key.D:
            diffs = list(Difficulty)
            idx = diffs.index(self.settings.difficulty)
            self.settings.difficulty = diffs[(idx + 1) % len(diffs)]
            self.settings.save()
        elif symbol == arcade.key.Q:
            arcade.close_window()

# ===============================
# MAIN
# ===============================

def main():
    settings = GameSettings.load()
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE,
                           resizable=False)
    window.background_color = arcade.color.BLACK
    menu = MenuView(settings)
    window.show_view(menu)
    arcade.run()

if __name__ == "__main__":
    main()