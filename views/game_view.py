import arcade
import random
import math
import os
from typing import List, Optional, Set, Dict
from dataclasses import dataclass

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    GameState, ControlMode, PowerUpType, WeaponType, WaveModifier, EnemyType, Difficulty,
    DIFFICULTY_SETTINGS, MAX_HEALTH, MAX_SHIELD, MAX_ENERGY, WEAPON_TIERS,
    IMG_PATH, BASE_DIR, SOUND_PATH, COMBO_TIMEOUT, FIRE_RATE, MUZZLE_DURATION,
    POWERUP_MAGNET_RADIUS, MAX_ENEMIES, BASE_ENEMY_SPEED, RESPAWN_DELAY,
    MINIMAP_WIDTH, MINIMAP_HEIGHT
)
from core.settings import GameSettings
from systems.achievements import AchievementSystem, AchievementID, ACHIEVEMENT_META
from systems.gesture import GestureController
from systems.wave_manager import WaveManager
from entities.sprites import Bullet, Player, Enemy, Boss, PowerUp, Asteroid
from entities.vfx import FloatingText, Shockwave, ScreenFlash, DashTrail, Particle, StarField
from core.utils import Camera
from views.menu_view import MenuView

@dataclass
class Upgrade:
    label: str
    description: str
    apply_fn: str

UPGRADE_POOL = [
    Upgrade("Weapon Tier +", "Enhance current weapon level", "upg_weapon_tier"),
    Upgrade("Max HP +", "Increase maximum hull integrity", "upg_max_hp"),
    Upgrade("Max Shield +", "Increase maximum shield capacity", "upg_max_shield"),
    Upgrade("Max Energy +", "Increase maximum weapon energy", "upg_max_energy"),
    Upgrade("Fire Rate +", "Shoot faster", "upg_fire_rate"),
    Upgrade("Dash Speed +", "Dodge roll travels further", "upg_dash_speed"),
    Upgrade("Shield Regen +", "Restore shields faster", "upg_shield_regen"),
    Upgrade("Energy Regen +", "Restore weapon energy faster", "upg_energy_regen"),
    Upgrade("Combo Window +", "More time to maintain combo", "upg_combo_window"),
    Upgrade("Extra Life", "Gain an additional ship", "upg_extra_life"),
    Upgrade("Dash Cooldown -", "Dodge roll off cooldown sooner", "upg_dash_cd"),
    Upgrade("Spread Count +", "Spread gun fires more bullets", "upg_spread_count"),
]

# Provide fallback for CustomColor if not present in core.constants (we used hex tuples instead)
# Just use standard tuple handling for missing aliases to avoid compile error


class GameView(arcade.View):
    def __init__(self, settings: GameSettings):
        super().__init__()
        self.settings = settings
        self.state    = GameState.PLAYING

        self.sounds   = self._load_sounds()

        # Background music
        self._bg_music_player = None
        try:
            self._bg_music = arcade.Sound(os.path.join(BASE_DIR, "bg_music.mp3"))
            self._bg_music_player = self._bg_music.play(
                volume=settings.music_volume, loop=True)
        except Exception as e:
            print(f"⚠ Could not load bg_music.mp3: {e}")
            self._bg_music = None

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
        self.bg_texture = arcade.load_texture(os.path.join(IMG_PATH, "background.jpg"))

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

        # Gesture control system (DISABLED BY DEFAULT, press G to activate)
        self.control_mode = ControlMode.KEYBOARD_MOUSE
        self.gesture_controller = GestureController()
        # self.gesture_controller.start() # Start only on 'G' press
        self.announce("⌨️ KEYBOARD MODE ACTIVATED", 120)
        self._gesture_fire_active = False
        self._gesture_cam_texture: Optional[arcade.Texture] = None
        self._gesture_cam_update_timer = 0
        # Physics-based turning (angular velocity in degrees/frame)
        self._gesture_angular_vel = 0.0
        # Track previous gesture for edge-detection (single-fire power weapon)
        self._prev_gesture_state = "IDLE"
        # Grace period: ignore gesture input for the first N frames after restart
        self._gesture_grace_frames = 60


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

        # Power weapon state (M key)
        self._power_weapon_active = False
        self._power_weapon_ammo   = 10

        # Death position for respawn
        self._death_x = SCREEN_WIDTH // 2
        self._death_y = 100

        self.wave_manager.start_wave()
        self.announce("Wave 1 — FIGHT!", 100)

    # ── sounds ──────────────────────────────────────
    def _load_sounds(self) -> Dict:
        sounds = {}
        for name, fname in [('shoot','shoot.wav'), ('hit','hit.wav'),
                             ('boss','boss.wav'), ('powerup','powerup.wav'),
                             ('explode','explode.wav'),
                             ('player_power_weapon_sound','player_power_weapon_sound.mp3'),
                             ('boss_weapon_sound','boss_weapon_sound.mp3')]:
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
        if self.control_mode == ControlMode.GESTURE:
            self._handle_gesture_movement()
        else:
            self._handle_keyboard_movement()

    def _handle_keyboard_movement(self):
        """Original WASD + mouse movement (unchanged logic)."""
        accel = 1.0
        friction = 0.85

        ix = iy = 0.0
        if arcade.key.LEFT in self.keys_pressed or arcade.key.A in self.keys_pressed:
            ix -= 1
        if arcade.key.RIGHT in self.keys_pressed or arcade.key.D in self.keys_pressed:
            ix += 1
        if arcade.key.UP in self.keys_pressed or arcade.key.W in self.keys_pressed:
            iy += 1
        if arcade.key.DOWN in self.keys_pressed or arcade.key.S in self.keys_pressed:
            iy -= 1

        if ix != 0 or iy != 0:
            length = math.hypot(ix, iy)
            ix /= length
            iy /= length

        if self.player.dash_active > 0:
            if ix != 0 or iy != 0:
                self.player.velocity_x = ix * self.player.dash_speed
                self.player.velocity_y = iy * self.player.dash_speed
            else:
                ar = math.radians(self.player.angle + 90)
                self.player.velocity_x = math.cos(ar) * self.player.dash_speed
                self.player.velocity_y = math.sin(ar) * self.player.dash_speed
            if self.frame_count % 3 == 0:
                self.dash_trails.append(DashTrail(self.player.center_x, self.player.center_y))
        else:
            self.player.velocity_x += ix * accel
            self.player.velocity_y += iy * accel

            max_spd = self.player.get_effective_speed()
            speed = math.hypot(self.player.velocity_x, self.player.velocity_y)
            if speed > max_spd:
                self.player.velocity_x = (self.player.velocity_x / speed) * max_spd
                self.player.velocity_y = (self.player.velocity_y / speed) * max_spd

            self.player.velocity_x *= friction
            self.player.velocity_y *= friction

        self.player.center_x += self.player.velocity_x
        self.player.center_y += self.player.velocity_y

    def _handle_gesture_movement(self):
        """Physics-based gesture movement with realistic turning."""
        gc = self.gesture_controller
        state = gc.gesture_state
        speed = self.player.get_effective_speed()

        # ── Angular velocity physics for turning ──
        TURN_ACCEL = 0.20       # degrees/frame² acceleration (gentler for gesture)
        TURN_MAX_SPEED = 2.0    # degrees/frame max rotation speed
        TURN_FRICTION = 0.88    # angular deceleration when not turning

        if state == "TURN_RIGHT":
            # Apply angular acceleration (clockwise = negative in arcade)
            self._gesture_angular_vel -= TURN_ACCEL
            self._gesture_angular_vel = max(self._gesture_angular_vel, -TURN_MAX_SPEED)
        elif state == "TURN_LEFT":
            # Apply angular acceleration (counter-clockwise = positive)
            self._gesture_angular_vel += TURN_ACCEL
            self._gesture_angular_vel = min(self._gesture_angular_vel, TURN_MAX_SPEED)
        else:
            # Angular friction — slow rotation naturally
            self._gesture_angular_vel *= TURN_FRICTION
            if abs(self._gesture_angular_vel) < 0.08:
                self._gesture_angular_vel = 0.0

        # Apply angular velocity to player rotation
        self.player.angle += self._gesture_angular_vel

        # ── Linear movement (based on ship's current facing direction) ──
        # Ship's forward direction: angle + 90 (sprite faces up at angle 0)
        forward_rad = math.radians(self.player.angle + 90)

        if state == "FORWARD":
            # Thrust forward in facing direction (boosted for gesture responsiveness)
            self.player.velocity_x += math.cos(forward_rad) * 1.2
            self.player.velocity_y += math.sin(forward_rad) * 1.2
            # Clamp to max speed
            spd = math.hypot(self.player.velocity_x, self.player.velocity_y)
            if spd > speed:
                self.player.velocity_x = (self.player.velocity_x / spd) * speed
                self.player.velocity_y = (self.player.velocity_y / spd) * speed

        elif state == "BACKWARD":
            # Thrust backward (opposite of facing) at 50% power
            self.player.velocity_x -= math.cos(forward_rad) * 0.5
            self.player.velocity_y -= math.sin(forward_rad) * 0.5
            # Clamp to half max speed for reverse
            spd = math.hypot(self.player.velocity_x, self.player.velocity_y)
            if spd > speed * 0.5:
                self.player.velocity_x = (self.player.velocity_x / spd) * speed * 0.5
                self.player.velocity_y = (self.player.velocity_y / spd) * speed * 0.5

        elif state == "FIRE":
            # Slight drag while firing (drift in current direction)
            self.player.velocity_x *= 0.96
            self.player.velocity_y *= 0.96

        elif state in ("TURN_LEFT", "TURN_RIGHT"):
            # Gentle drag while turning (allows turn-and-drift maneuvers)
            self.player.velocity_x *= 0.97
            self.player.velocity_y *= 0.97

        else:
            # IDLE — standard space friction
            self.player.velocity_x *= 0.94
            self.player.velocity_y *= 0.94

        # Dash handling (keyboard SHIFT still works in gesture mode)
        if self.player.dash_active > 0:
            self.player.velocity_x = math.cos(forward_rad) * self.player.dash_speed
            self.player.velocity_y = math.sin(forward_rad) * self.player.dash_speed
            if self.frame_count % 3 == 0:
                self.dash_trails.append(DashTrail(self.player.center_x, self.player.center_y))

        self.player.center_x += self.player.velocity_x
        self.player.center_y += self.player.velocity_y

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
        # Determine if we should be firing
        if self.control_mode == ControlMode.GESTURE:
            if not self._gesture_fire_active:
                return
        else:
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

        ar  = math.radians(self.player.angle + 90)
        off = 48

        dmg = self.player.get_bullet_damage()
        spd = self.player.get_bullet_speed()

        # Decide texture: power weapon (M key active + ammo) OR normal bullet
        if self._power_weapon_active and self._power_weapon_ammo > 0:
            player_tex_path = "player_power_weapon.png"
            self._power_weapon_ammo -= 1
            if self._power_weapon_ammo <= 0:
                self._power_weapon_active = False
        else:
            player_tex_path = "bullet.png"

        if self.player.current_weapon == WeaponType.SINGLE:
            self.bullet_sprites.append(
                Bullet(self.player.center_x + math.cos(ar) * off,
                       self.player.center_y + math.sin(ar) * off,
                       ar, spd, damage=dmg, texture_path=player_tex_path))

        elif self.player.current_weapon == WeaponType.SPREAD:
            n       = self.player.spread_count
            spread  = 0.22
            offsets = [(i / (n - 1) - 0.5) * spread * 2 for i in range(n)] if n > 1 else [0]
            for sp in offsets:
                a = ar + sp
                self.bullet_sprites.append(
                    Bullet(self.player.center_x + math.cos(a) * off,
                           self.player.center_y + math.sin(a) * off,
                           a, spd, damage=dmg, color=(255, 200, 0, 255), texture_path=player_tex_path))

        elif self.player.current_weapon == WeaponType.PIERCING:
            self.bullet_sprites.append(
                Bullet(self.player.center_x + math.cos(ar) * off,
                       self.player.center_y + math.sin(ar) * off,
                       ar, spd, penetrating=True, damage=dmg,
                       color=(200, 0, 255, 255), texture_path=player_tex_path))

        self.player.energy -= self.player.energy_cost_fire
        if "player_power_weapon" in player_tex_path:
            self._play('player_power_weapon_sound')
        else:
            self._play('shoot')
        self.muzzle_timer = MUZZLE_DURATION
        self.fire_timer   = 0

    def _apply_gesture_input(self):
        """Read gesture controller state and set fire flag."""
        if self.control_mode != ControlMode.GESTURE:
            self._gesture_fire_active = False
            return

        # Grace period after restart — ignore all gesture input
        if self._gesture_grace_frames > 0:
            self._gesture_grace_frames -= 1
            self._gesture_fire_active = False
            self._prev_gesture_state = "IDLE"
            return

        gc = self.gesture_controller
        current = gc.gesture_state
        prev = self._prev_gesture_state

        # Normal FIRE gesture → continuous fire with standard bullets
        if current == "FIRE":
            self._gesture_fire_active = True
            self._power_weapon_active = False

        # POWER_WEAPON gesture → continuous fire while held
        elif current == "POWER_WEAPON":
            if self._power_weapon_ammo > 0:
                self._power_weapon_active = True
                self._gesture_fire_active = True
            else:
                self._gesture_fire_active = False
                self._power_weapon_active = False
        else:
            self._gesture_fire_active = False
            self._power_weapon_active = False

        self._prev_gesture_state = current

    # ── main update ──────────────────────────────────
    def on_update(self, delta_time: float):
        self.frame_count += 1
        self._apply_gesture_input()

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
        self.player.on_update(delta_time)
        self.fire_weapon()

        # ── sprites ──
        for sl in (self.bullet_sprites, self.enemy_bullet_sprites,
                   self.boss_bullet_sprites, self.particle_sprites,
                   self.powerup_sprites, self.asteroid_sprites):
            sl.on_update(delta_time)

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
            self._power_weapon_ammo += 1
            self.announce(f"Wave {cleared_wave} Clear! +{bonus} [Missile +1]", 150)
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
                                  self.enemy_sprites, self.settings.difficulty,
                                  sound_callback=self._play)
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
                    # Power weapon = instant kill on any target
                    if bullet.is_power_weapon:
                        enemy.health = 0
                        self._kill_enemy(enemy)
                        self.create_sparks(enemy.center_x, enemy.center_y, 12)
                    else:
                        actual = enemy.take_damage(bullet.damage, kb)
                        if actual > 0:
                            self.create_sparks(enemy.center_x, enemy.center_y, 6)
                        if enemy.health <= 0:
                            self._kill_enemy(enemy)
                    self._play('hit')
                    if not bullet.penetrating:
                        bullet.kill()
                    if not bullet.alive:
                        break

        # Player bullets → boss
        if self.boss:
            for bullet in list(self.bullet_sprites):
                if bullet.alive and arcade.check_for_collision(bullet, self.boss):
                    # Power weapon = instant boss kill
                    if bullet.is_power_weapon:
                        self.boss.take_damage(self.boss.max_health)
                    else:
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
                        break

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
        # Clear all existing enemies before boss appears
        for enemy in list(self.enemy_sprites):
            self.create_explosion(enemy.center_x, enemy.center_y, 15, (255, 160, 60, 255))
            enemy.kill()
        for b in list(self.enemy_bullet_sprites):
            b.kill()

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
        # Remember death position for respawn
        self._death_x = self.player.center_x
        self._death_y = self.player.center_y
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
        # Respawn at exact death position
        self.player.center_x = self._death_x
        self.player.center_y = self._death_y
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
        arcade.draw_lrwh_rectangle_textured(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, self.bg_texture)
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
            ar = math.radians(self.player.angle + 90)
            fx = self.player.center_x + math.cos(ar) * 48
            fy = self.player.center_y + math.sin(ar) * 48
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
                         arcade.color.WHITE, 12)
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
        # Power weapon HUD indicator
        pw_col = (255, 255, 255, 255) if self._power_weapon_active else (255, 255, 255, 255)
        pw_label = f"M: Power Weapon {'ON' if self._power_weapon_active else 'OFF'} [{self._power_weapon_ammo}]"
        arcade.draw_text(pw_label, pad, hud_y - 242, pw_col, 11, bold=self._power_weapon_active)
        dash_ready = self.player.dash_timer <= 0
        dash_col = (0, 255, 80, 255) if dash_ready else (130, 130, 130, 255)
        sh_col   = (80, 160, 255, 255) if self.player.shield_active else (100, 100, 100, 200)
        arcade.draw_text("SHIFT: Dash" + ("  ✔" if dash_ready else ""),
                         pad, hud_y - 260, dash_col, 11)
        arcade.draw_text("E: Shield" + ("  ON" if self.player.shield_active else ""),
                         pad, hud_y - 278, sh_col, 11)

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
                             (255, 100, 100, 255), 13)

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
        self._draw_camera_preview()
        self._draw_gesture_hud()
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

    def _draw_camera_preview(self):
        """Render live webcam feed inside the game window (top-right HUD)."""
        if self.control_mode != ControlMode.GESTURE:
            return
        if not self.gesture_controller.is_running:
            return

        # Update texture every few frames to avoid performance hit
        self._gesture_cam_update_timer += 1
        if self._gesture_cam_update_timer >= 2:  # update every 2 draw frames
            self._gesture_cam_update_timer = 0
            tex = self.gesture_controller.get_camera_texture()
            if tex is not None:
                self._gesture_cam_texture = tex

        if self._gesture_cam_texture is None:
            return

        pw, ph = GestureController.PREVIEW_W, GestureController.PREVIEW_H
        px = SCREEN_WIDTH - pw - 12
        py = SCREEN_HEIGHT - ph - 42  # below top HUD bar

        # Background panel
        arcade.draw_rectangle_filled(px + pw / 2, py + ph / 2, pw + 4, ph + 4,
                                     (10, 10, 30, 200))

        # Draw the camera texture
        arcade.draw_lrwh_rectangle_textured(
            px, py, pw, ph, self._gesture_cam_texture
        )

        # Border
        arcade.draw_rectangle_outline(px + pw / 2, py + ph / 2, pw, ph,
                                      (0, 200, 255, 180), 2)

        # Label
        arcade.draw_text("📷 CAMERA", px + 4, py + ph - 14,
                         (0, 220, 255, 220), 10, bold=True)

        # Gesture state badge
        gesture = self.gesture_controller.gesture_state
        g_colors = {
            "FORWARD": (0, 255, 100, 255),
            "BACKWARD": (255, 100, 50, 255),
            "FIRE": (255, 50, 0, 255),
            "POWER_WEAPON": (255, 60, 255, 255),
            "TURN_RIGHT": (100, 200, 255, 255),
            "TURN_LEFT": (100, 200, 255, 255),
            "IDLE": (150, 150, 150, 200),
        }
        g_col = g_colors.get(gesture, (150, 150, 150, 200))
        arcade.draw_text(gesture, px + pw - 8, py + 4,
                         g_col, 11, anchor_x="right", bold=True)

    def _draw_gesture_hud(self):
        """Draw control mode indicator and gesture state on screen."""
        # Control mode indicator (always visible, bottom-center)
        if self.control_mode == ControlMode.KEYBOARD_MOUSE:
            mode_text = "Mode: KEYBOARD  [G → Gesture]"
            mode_color = (180, 180, 200, 180)
        else:
            mode_text = "Mode: GESTURE  [G → Keyboard]"
            mode_color = (0, 220, 255, 255)

        arcade.draw_text(mode_text, SCREEN_WIDTH // 2, 12,
                         mode_color, 12, anchor_x="center", bold=True)

        # In gesture mode, show current gesture label prominently
        if self.control_mode == ControlMode.GESTURE:
            gesture = self.gesture_controller.gesture_state
            g_icons = {
                "FORWARD": "☝️ FORWARD",
                "BACKWARD": "✊ REVERSE",
                "FIRE": "✌️ FIRE",
                "TURN_RIGHT": "👉 TURN RIGHT",
                "TURN_LEFT": "👈 TURN LEFT",
                "IDLE": "✋ IDLE",
            }
            g_colors = {
                "FORWARD": (0, 255, 100, 255),
                "BACKWARD": (255, 100, 50, 255),
                "FIRE": (255, 50, 0, 255),
                "TURN_RIGHT": (100, 200, 255, 255),
                "TURN_LEFT": (100, 200, 255, 255),
                "IDLE": (120, 120, 120, 180),
            }
            label = g_icons.get(gesture, gesture)
            col = g_colors.get(gesture, (180, 180, 180, 200))
            arcade.draw_text(f"Gesture: {label}", SCREEN_WIDTH // 2, 32,
                             col, 14, anchor_x="center", bold=True)

            # Angular velocity indicator (shows rotation momentum)
            av = self._gesture_angular_vel
            if abs(av) > 0.1:
                if av > 0:
                    rot_text = f"↺ {av:.1f}°/f"
                    rot_col = (100, 200, 255, 220)
                else:
                    rot_text = f"↻ {abs(av):.1f}°/f"
                    rot_col = (100, 200, 255, 220)
                arcade.draw_text(rot_text, SCREEN_WIDTH // 2, 52,
                                 rot_col, 11, anchor_x="center", bold=True)

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
        if self.state == GameState.PLAYING and self.control_mode == ControlMode.KEYBOARD_MOUSE:
            self.player.angle = math.degrees(
                math.atan2(y - self.player.center_y, x - self.player.center_x)) - 90

    def on_mouse_press(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT and self.state == GameState.PLAYING:
            self.mouse_held = True
            if self.fire_timer == 0:
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

        elif symbol == arcade.key.G:
            # Toggle control mode
            if self.control_mode == ControlMode.KEYBOARD_MOUSE:
                # Stop any old controller and create a completely fresh one
                self.gesture_controller.stop()
                self.gesture_controller = GestureController()
                self.gesture_controller.start()
                self.control_mode = ControlMode.GESTURE
                self._gesture_fire_active = False
                self._prev_gesture_state = "IDLE"
                self._gesture_grace_frames = 60
                self._gesture_cam_texture = None
                self.announce("🎮 GESTURE MODE ACTIVATED", 120)
            else:
                self.control_mode = ControlMode.KEYBOARD_MOUSE
                self.gesture_controller.stop()
                self._gesture_fire_active = False
                self._gesture_cam_texture = None
                self.announce("⌨️ KEYBOARD MODE ACTIVATED", 120)

        elif symbol == arcade.key.M and self.state == GameState.PLAYING:
            if self._power_weapon_ammo > 0:
                self._power_weapon_active = not self._power_weapon_active
                status = "ON" if self._power_weapon_active else "OFF"
                self.announce(f"⚡ POWER WEAPON {status} ({self._power_weapon_ammo} left)", 90)
            else:
                self.announce("⚠ POWER WEAPON DEPLETED", 90)

        elif symbol == arcade.key.A and self.state == GameState.PAUSED:
            self.player.aim_assist = not self.player.aim_assist
            self.settings.aim_assist = self.player.aim_assist

        elif symbol == arcade.key.R:
            if self.state in (GameState.GAME_OVER, GameState.PAUSED):
                self.gesture_controller.stop()
                self._stop_music()
                self.window.show_view(GameView(self.settings))

        elif symbol == arcade.key.Q:
            if self.state in (GameState.GAME_OVER, GameState.PAUSED):
                self.gesture_controller.stop()
                self._stop_music()
                self.window.show_view(MenuView(self.settings))

    def _stop_music(self):
        if self._bg_music_player:
            try:
                self._bg_music_player.pause()
            except Exception:
                pass
            self._bg_music_player = None

    def on_key_release(self, symbol: int, modifiers: int):
        self.keys_pressed.discard(symbol)

# ═══════════════════════════════════════════════════
# MENU VIEW
# ═══════════════════════════════════════════════════

