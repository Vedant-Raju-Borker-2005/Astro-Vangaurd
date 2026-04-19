import arcade
import random
import math
import os
from typing import List, Optional, Dict
from collections import defaultdict

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, IMG_PATH,
    Difficulty, EnemyType, PowerUpType, WeaponType,
    DIFFICULTY_SETTINGS, WEAPON_TIERS, WEAPON_SPEED_BONUS,
    PLAYER_SPEED, DASH_SPEED, DASH_COOLDOWN, DASH_DURATION,
    MAX_ENERGY, MAX_HEALTH, MAX_LIVES, SHIELD_REGEN,
    SHIELD_COOLDOWN, SHIELD_ABSORPTION, SHIELD_DRAIN, MAX_SHIELD,
    BULLET_SPEED, ENEMY_BULLET_SPEED, FIRE_RATE, MUZZLE_DURATION,
    BASE_ENEMY_SPEED, BOSS_SPEED, GRID_SIZE
)
from core.utils import astar

# ═══════════════════════════════════════════════════
# ASTEROIDS
# ═══════════════════════════════════════════════════

class Asteroid(arcade.Sprite):
    def __init__(self):
        size = random.randint(18, 38)
        gray = random.randint(90, 160)
        texture = arcade.make_circle_texture(size, (gray, gray, gray, 230))
        super().__init__(texture=texture)
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
        super().__init__(texture=texture)
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
# BULLET
# ═══════════════════════════════════════════════════

class Bullet(arcade.Sprite):
    def __init__(self, x, y, angle, speed, is_player=True,
                 penetrating=False, damage=20.0, color=None,
                 texture_path="bullet.png", custom_scale=None):
        if color is None:
            color = (255, 240, 0, 255) if is_player else (255, 60, 60, 255)
        if custom_scale is not None:
            scale = custom_scale
        else:
            scale = 0.01 if texture_path == "bullet.png" else 0.05
        super().__init__(os.path.join(IMG_PATH, texture_path), scale=scale)
        self.color = color
        self.center_x, self.center_y = x, y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.is_player = is_player
        self.penetrating = penetrating
        self.damage = damage
        self.lifetime = 480
        self.is_power_weapon = ("player_power_weapon" in texture_path)
        self.is_missile = (texture_path != "bullet.png")
        if self.is_missile:
            self.angle = math.degrees(math.atan2(self.vy, self.vx)) - 90

    def on_update(self, delta_time=1 / 60):
        if self.is_power_weapon:
            speed = math.hypot(self.vx, self.vy)
            if speed > 0:
                self.vx *= 0.997
                self.vy *= 0.997
                self.vy -= 0.05
        if self.is_missile:
            self.angle = math.degrees(math.atan2(self.vy, self.vx)) - 90
        self.center_x += self.vx
        self.center_y += self.vy
        self.lifetime -= 1
        if (self.center_x < -80 or self.center_x > SCREEN_WIDTH + 80 or
                self.center_y < -80 or self.center_y > SCREEN_HEIGHT + 80 or
                self.lifetime <= 0):
            self.kill()

# ═══════════════════════════════════════════════════
# PLAYER
# ═══════════════════════════════════════════════════

class Player(arcade.Sprite):
    def __init__(self):
        super().__init__(os.path.join(IMG_PATH, "player.png"), scale=0.15)
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

        self.dash_speed = DASH_SPEED
        self.dash_cd    = DASH_COOLDOWN
        self.shield_regen_rate = SHIELD_REGEN
        self.energy_regen_rate = 0.30
        self.spread_count = 3
        self.combo_window_mult = 1.0
        self.energy_cost_fire = 5
        self.aim_assist = False

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
        else:
            if not self.shield_active and self.shield < self.max_shield:
                self.shield = min(self.max_shield, self.shield + self.shield_regen_rate)

        if self.invincible_timer > 0:
            self.invincible_timer -= 1
            self.alpha = 90 if (self.invincible_timer % 6 < 3) else 255
        else:
            self.alpha = 255

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

    def apply_power_up(self, power_up: PowerUp) -> str:
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
        return damage + absorbed

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
        super().__init__(os.path.join(IMG_PATH, "enemy.png"), scale=0.025)
        self.color = color
        self.enemy_type = enemy_type
        self.difficulty  = difficulty
        settings = DIFFICULTY_SETTINGS[difficulty]

        self.center_x = spawn_x if spawn_x is not None else random.randint(80, SCREEN_WIDTH - 80)
        self.center_y = spawn_y if spawn_y is not None else SCREEN_HEIGHT + 30

        mult = {EnemyType.SCOUT: 0.65, EnemyType.SOLDIER: 1.0, EnemyType.ELITE: 1.6,
                EnemyType.KAMIKAZE: 0.4, EnemyType.SNIPER: 0.9, EnemyType.SHIELDED: 1.4}
        self.health = self.max_health = int(settings.enemy_health * mult.get(enemy_type, 1.0))

        self.enemy_shield = 40 if enemy_type == EnemyType.SHIELDED else 0
        self.max_enemy_shield = self.enemy_shield

        self.path: List[Tuple[int, int]] = []
        self.repath_timer = random.randint(0, 20)
        self.shoot_timer  = random.randint(0, settings.enemy_fire_rate)
        self.fire_rate    = settings.enemy_fire_rate

        self.knockback_vx = self.knockback_vy = 0.0
        self.hit_flash = 0

        self.burst_count = self.burst_timer = 0
        self.sniper_charge = 0
        self.sniper_locked_angle: Optional[float] = None

    def take_damage(self, damage: float, knockback_angle: float = 0.0) -> float:
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

        if self.enemy_type == EnemyType.KAMIKAZE:
            angle = math.atan2(player.center_y - self.center_y,
                               player.center_x - self.center_x)
            self.center_x += math.cos(angle) * eff_speed * 1.8
            self.center_y += math.sin(angle) * eff_speed * 1.8
            self.angle = math.degrees(angle) - 90
            return

        if self.enemy_type == EnemyType.SNIPER:
            dist = math.hypot(player.center_x - self.center_x,
                              player.center_y - self.center_y)
            if dist < 300:
                angle = math.atan2(self.center_y - player.center_y,
                                   self.center_x - player.center_x)
                self.center_x += math.cos(angle) * eff_speed * 0.6
                self.center_y += math.sin(angle) * eff_speed * 0.6
            self.sniper_charge += 1
            charge_time = max(50, self.fire_rate - 20)
            if self.sniper_charge < charge_time:
                ratio = self.sniper_charge / charge_time
                if ratio > 0.8:
                    self.sniper_locked_angle = math.atan2(
                        player.center_y - self.center_y,
                        player.center_x - self.center_x)
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

        if self.repath_timer > 38:
            sx = int(self.center_x // GRID_SIZE) * GRID_SIZE
            sy = int(self.center_y // GRID_SIZE) * GRID_SIZE
            ex = int(player.center_x // GRID_SIZE) * GRID_SIZE
            ey = int(player.center_y // GRID_SIZE) * GRID_SIZE
            self.path = astar((sx, sy), (ex, ey))
            self.repath_timer = 0

        if self.path and len(self.path) > 1:
            target = self.path[1]
            move_angle = math.atan2(target[1] - self.center_y, target[0] - self.center_x)
        else:
            move_angle = math.atan2(player.center_y - self.center_y,
                                    player.center_x - self.center_x)

        face_angle = math.atan2(player.center_y - self.center_y,
                                player.center_x - self.center_x)

        self.angle = math.degrees(face_angle) - 90
        self.center_x += math.cos(move_angle) * eff_speed
        self.center_y += math.sin(move_angle) * eff_speed

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
        super().__init__(os.path.join(IMG_PATH, "boss.png"), scale=0.85)
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

        self.beam_charging = False
        self.beam_charge_timer = 0
        self.beam_fire_timer = 0
        self.beam_angle: float = 0

        self.summon_cd = 0
        self.weapon_phase_timer = 0
        self.WEAPON_SWITCH_THRESHOLD = 600
        self.using_weapon_2 = False

    def _pick_target(self):
        self.move_target_x = random.randint(100, SCREEN_WIDTH - 100)
        self.move_target_y = random.randint(SCREEN_HEIGHT // 2, SCREEN_HEIGHT - 80)
        self.move_timer = random.randint(80, 160)

    def select_attack(self, player: Player) -> str:
        dist   = math.hypot(self.center_x - player.center_x, self.center_y - player.center_y)
        hp_pct = self.health / self.max_health
        if hp_pct < 0.33:
            self.phase = 3; self.rage_mode = True
            attacks = ["BLAST", "LASER", "BEAM", "BLAST", "LASER"]
        elif hp_pct < 0.66:
            self.phase = 2
            attacks = ["LASER", "BLAST", "BEAM", "SUMMON"] if dist > 200 else ["BLAST", "LASER", "DASH"]
        else:
            self.phase = 1
            attacks = ["LASER", "BLAST", "LASER"]
        return random.choice(attacks)

    def decide_action(self, player: Player) -> str:
        dist = math.hypot(self.center_x - player.center_x, self.center_y - player.center_y)
        attack_chance = 0.95 if dist < 300 else 0.85
        return "ATTACK" if random.random() < attack_chance else "MOVE"

    def update_boss(self, player: Player,
                    boss_bullets: arcade.SpriteList,
                    enemy_sprites: arcade.SpriteList,
                    difficulty: Difficulty,
                    sound_callback=None):
        self.move_timer = max(0, self.move_timer - 1)
        if self.summon_cd > 0:
            self.summon_cd -= 1

        self.weapon_phase_timer += 1
        if not self.using_weapon_2 and self.weapon_phase_timer >= self.WEAPON_SWITCH_THRESHOLD:
            self.using_weapon_2 = True

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
        self.angle = math.degrees(angle) - 90

        if self.beam_charging:
            self.beam_charge_timer -= 1
            if self.beam_charge_timer <= 0:
                self.beam_charging = False
                self.beam_fire_timer = 20
                spread_n = 7 if self.rage_mode else 4
                if sound_callback:
                    sound_callback('boss_weapon_sound')
                for i in range(spread_n):
                    sp = (i / (spread_n - 1) - 0.5) * 0.6
                    boss_tex = "boss_weapon_2.png" if self.using_weapon_2 else "boss_weapon_1.png"
                    b = Bullet(self.center_x, self.center_y,
                               self.beam_angle + sp, 10,
                               is_player=False, damage=14,
                               color=(255, 120, 0, 255),
                               texture_path=boss_tex)
                    boss_bullets.append(b)
            return

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
            if sound_callback:
                sound_callback('boss_weapon_sound')
            for i in range(n):
                sp = (i - (n - 1) / 2) * 0.22
                tex = "boss_weapon_2.png" if self.using_weapon_2 else "boss_weapon_1.png"
                b = Bullet(self.center_x, self.center_y, angle + sp,
                           9, is_player=False, damage=12, texture_path=tex)
                boss_bullets.append(b)
            self.attack_cooldown = int(55 * cd_mult)

        elif attack_type == "DASH":
            self.center_x = max(60, min(SCREEN_WIDTH  - 60, self.center_x + math.cos(angle) * 80))
            self.center_y = max(60, min(SCREEN_HEIGHT - 60, self.center_y + math.sin(angle) * 80))
            self.attack_cooldown = int(40 * cd_mult)

        elif attack_type == "BLAST":
            n = 8 if self.rage_mode else 4
            if sound_callback:
                sound_callback('boss_weapon_sound')
            for i in range(n):
                sp = (i / n) * math.pi * 2
                tex = "boss_weapon_2.png" if self.using_weapon_2 else "boss_weapon_1.png"
                b = Bullet(self.center_x, self.center_y, sp, 6,
                           is_player=False, damage=10, texture_path=tex)
                boss_bullets.append(b)
            self.attack_cooldown = int(45 * cd_mult)

        elif attack_type == "BEAM":
            self.beam_charging   = True
            self.beam_charge_timer = 60
            self.beam_angle      = angle
            self.attack_cooldown = int(100 * cd_mult)

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
        if not self.beam_charging:
            return
        ratio = 1.0 - (self.beam_charge_timer / 80)
        alpha = int(ratio * 200)
        end_x = self.center_x + math.cos(self.beam_angle) * SCREEN_WIDTH
        end_y = self.center_y + math.sin(self.beam_angle) * SCREEN_WIDTH
        w = max(1, int(ratio * 8))
        arcade.draw_line(self.center_x, self.center_y, end_x, end_y,
                         (255, 140, 0, alpha), w)
        arcade.draw_circle_outline(self.center_x, self.center_y,
                                   20 + ratio * 30, (255, 200, 80, alpha), 3)
