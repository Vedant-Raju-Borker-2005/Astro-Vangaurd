import arcade
import random
import math
import os
from typing import List

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, IMG_PATH, BASE_DIR, Difficulty
from core.settings import GameSettings
from entities.vfx import StarField, Particle

class MenuView(arcade.View):
    def __init__(self, settings: GameSettings):
        super().__init__()
        self.settings   = settings
        self.star_field = StarField()
        self.tick       = 0
        self.particles: List[Particle] = []
        self._particle_list = arcade.SpriteList()

        try:
            from PIL import ImageFilter
            import PIL.Image as PILImage
            pil_img = PILImage.open(os.path.join(IMG_PATH, "background.jpg")).convert('RGBA')
            blurred_img = pil_img.filter(ImageFilter.GaussianBlur(radius=8))
            self.bg_texture = arcade.Texture(name="bg_blurred", image=blurred_img)
        except ImportError:
            print("Pillow not installed, falling back to sharp background.")
            self.bg_texture = arcade.load_texture(os.path.join(IMG_PATH, "background.jpg"))
        except Exception as e:
            print("Could not blur background:", e)
            self.bg_texture = arcade.load_texture(os.path.join(IMG_PATH, "background.jpg"))

        self._bg_music_player = None
        try:
            self._bg_music = arcade.Sound(os.path.join(BASE_DIR, "bg_music.mp3"))
            self._bg_music_player = self._bg_music.play(
                volume=settings.music_volume, loop=True)
        except Exception as e:
            print(f"⚠ Could not load bg_music.mp3: {e}")
            self._bg_music = None

    def on_update(self, delta_time: float):
        self.star_field.scroll(0.2, 0.5)
        self.tick += 1
        if self.tick % 20 == 0:
            tex = arcade.make_circle_texture(16, (0, 180, 255, 180))
            p = Particle(tex,
                         random.uniform(0, SCREEN_WIDTH),
                         random.uniform(0, SCREEN_HEIGHT // 3))
            self._particle_list.append(p)
        self._particle_list.update()

    def on_draw(self):
        arcade.draw_lrwh_rectangle_textured(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, self.bg_texture)
        self.star_field.draw()
        self._particle_list.draw()

        pulse = 0.82 + 0.18 * math.sin(self.tick * 0.05)
        col   = (int(0 * pulse), int(200 * pulse), int(255 * pulse), 255)

        arcade.draw_text("ASTRO", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 110,
                        (255, 255, 255, 220), 88, anchor_x="center", bold=True, font_name="Times New Roman")
        arcade.draw_text("VANGUARD", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 196,
                         (255, 255, 255, 220), 56, anchor_x="center", bold=True, font_name="Times New Roman")
        arcade.draw_text("AI Tactical Space Siege  v5.0",
                         SCREEN_WIDTH // 2, SCREEN_HEIGHT - 240,
                         (255, 255, 255, 220), 20, anchor_x="center", font_name="Times New Roman")

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

        controls = [
            "WASD / Arrows — Move",
            "Mouse Left — Aim & Fire",
            "SHIFT — Dodge Roll (i-frames)",
            "E — Toggle Shield",
            "G — Toggle Gesture Control",
            "F — FPS Counter",
            "SPACE — Pause / Resume",
            "R — Restart  (pause/gameover)",
            "Q — Quit to Menu",
        ]
        lx, ly = SCREEN_WIDTH // 2 - 160, cy - 180
        arcade.draw_text("Controls:", lx, ly, (255, 255, 255, 220), 14, bold=True)
        for i, c in enumerate(controls):
            arcade.draw_text(c, lx, ly - 22 - i * 20, (255, 255, 255, 220), 12)

        if self.settings.high_score > 0:
            arcade.draw_text(f"Best: {self.settings.high_score:,}",
                             SCREEN_WIDTH // 2, 50,
                             arcade.color.GOLD, 20, anchor_x="center", bold=True)

    def on_key_press(self, symbol: int, modifiers: int):
        if symbol == arcade.key.ENTER:
            self._stop_music()
            from views.game_view import GameView
            self.window.show_view(GameView(self.settings))
        elif symbol == arcade.key.D:
            diffs = list(Difficulty)
            self.settings.difficulty = diffs[(diffs.index(self.settings.difficulty) + 1) % len(diffs)]
            self.settings.save()
        elif symbol == arcade.key.Q:
            arcade.close_window()

    def _stop_music(self):
        if self._bg_music_player:
            try:
                self._bg_music_player.pause()
            except Exception:
                pass
            self._bg_music_player = None
