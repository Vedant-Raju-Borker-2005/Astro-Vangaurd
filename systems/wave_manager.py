import random
from typing import List, Tuple, Optional
from core.constants import Difficulty, EnemyType, WaveModifier, INITIAL_WAVE_SIZE, WAVE_SIZE_INCREMENT, WAVES_BEFORE_BOSS, DIFFICULTY_SETTINGS
from core.utils import FormationSpawner

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
        if self._formation_queue:
            return self._formation_queue.pop(0)
        return None

    def is_boss_wave(self) -> bool:
        return self.current_wave > 0 and self.current_wave % WAVES_BEFORE_BOSS == 0

    def get_enemy_type(self) -> EnemyType:
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
