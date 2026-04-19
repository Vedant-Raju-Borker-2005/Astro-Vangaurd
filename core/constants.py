import os
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict

# ─── Control Mode ───────────────────────────────────────────────────────────
class ControlMode(Enum):
    KEYBOARD_MOUSE = "keyboard_mouse"
    GESTURE = "gesture"

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
    PACIFIST_WAVE  = "pacifist_wave"
    NUKE_LAUNCH    = "nuke_launch"
    SHARPSHOOTER   = "sharpshooter"
    FULL_UPGRADE   = "full_upgrade"
    DODGER         = "dodger"
    IRON_SHIELD    = "iron_shield"
    VETERAN        = "veteran"

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
SCREEN_TITLE  = "AstroVanguard: AI Tactical Space Siege — Enhanced v5.0"

PLAYER_SPEED   = 8
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

# ── Color palette ─────────────────────────────────────────
C_BLACK       = (0,   0,   0,   255)
C_DEEP_SPACE  = (4,   6,   18,  255)
C_NEBULA_BLUE = (8,   18,  55,  255)
C_STEEL       = (110, 120, 140, 255)
C_CHROME      = (180, 192, 210, 255)
C_SILVER      = (220, 228, 240, 255)
C_WHITE       = (255, 255, 255, 255)
C_GOLD        = (200, 162,  48, 255)
C_GOLD_LIGHT  = (255, 215,  90, 255)
C_GOLD_DARK   = (130, 100,  20, 255)
C_CYAN        = (0,   210, 255, 255)
C_CYAN_DIM    = (0,   100, 160, 255)
C_RED_WARN    = (220,  40,  40, 255)
C_ORANGE      = (255, 120,   0, 255)
C_PURPLE_NEB  = (70,  20, 100, 255)

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

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_PATH = os.path.join(BASE_DIR, "assets")
IMG_PATH    = os.path.join(ASSETS_PATH, "images")
SOUND_PATH  = os.path.join(ASSETS_PATH, "sounds")
SAVE_PATH   = os.path.join(BASE_DIR, "saves")
os.makedirs(SAVE_PATH, exist_ok=True)
