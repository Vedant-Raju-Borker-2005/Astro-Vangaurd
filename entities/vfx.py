import arcade
import random
import math
from typing import Tuple, List, Optional
from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT

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


class Shockwave:
    """Expanding ring after explosions."""
    def __init__(self, x: float, y: float,
                 color: Tuple = (255, 200, 80, 200), max_radius: float = 90):
        self.x = x
        self.y = y
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

class Particle(arcade.Sprite):
    def __init__(self, texture: arcade.Texture, x: float, y: float,
                 velocity: Optional[Tuple[float, float]] = None,
                 spark: bool = False):
        super().__init__(texture=texture)
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
