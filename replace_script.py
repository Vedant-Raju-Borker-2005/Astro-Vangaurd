import sys
import os

def main():
    with open('main.py', 'r', encoding='utf-8') as f:
        text = f.read()

    # 1. Update GameView._load_sounds
    text = text.replace(
        "('boss','boss.wav'), ('powerup','powerup.wav'),\n                   ('explode','explode.wav')]:",
        "('boss','boss.wav'), ('powerup','powerup.wav'),\n                   ('explode','explode.wav'),\n                   ('boss_weapon_sound','boss_weapon_sound.mp3'),\n                   ('player_power_weapon_sound','player_power_weapon_sound.mp3')]:"
    )
    # Also handle alternate tabs/spaces
    text = text.replace(
        "('boss','boss.wav'), ('powerup','powerup.wav'),\n                       ('explode','explode.wav')]:",
        "('boss','boss.wav'), ('powerup','powerup.wav'),\n                       ('explode','explode.wav'),\n                       ('boss_weapon_sound','boss_weapon_sound.mp3'),\n                       ('player_power_weapon_sound','player_power_weapon_sound.mp3')]:"
    )

    # 2. Update fire_weapon to play player_power_weapon_sound
    orig_fire = """self.player.energy -= self.player.energy_cost_fire
        self._play('shoot')"""
    new_fire = """self.player.energy -= self.player.energy_cost_fire
        if is_boss_fight:
            self._play('player_power_weapon_sound')
        else:
            self._play('shoot')"""
    text = text.replace(orig_fire, new_fire)

    # 3. Add is_power_weapon flag and physics to Bullet
    bullet_init_orig = """self.is_player = is_player
        self.penetrating = penetrating
        self.damage = damage
        self.lifetime = 480"""
    bullet_init_new = """self.is_player = is_player
        self.penetrating = penetrating
        self.damage = damage
        self.lifetime = 480
        self.is_power_weapon = ("player_power_weapon.png" in texture_path)"""
    text = text.replace(bullet_init_orig, bullet_init_new)

    bullet_update_orig = """def on_update(self, delta_time=1 / 60):
        self.center_x += self.vx
        self.center_y += self.vy"""
    bullet_update_new = """def on_update(self, delta_time=1 / 60):
        if getattr(self, 'is_power_weapon', False):
            # Realistic physics: apply acceleration mapped as 'velocity increase' or pseudo gravity
            self.vy -= 0.15 # Gravity effect
            self.vx *= 1.01 # subtle acceleration
        self.center_x += self.vx
        self.center_y += self.vy"""
    text = text.replace(bullet_update_orig, bullet_update_new)

    # 4. Boss collision: single hit kill
    boss_col_orig = """self.boss.take_damage(bullet.damage)
                    bullet.kill()
                    self._play('hit')"""
    boss_col_new = """if getattr(bullet, 'is_power_weapon', False):
                        self.boss.take_damage(self.boss.max_health)
                    else:
                        self.boss.take_damage(bullet.damage)
                    bullet.kill()
                    self._play('hit')"""
    text = text.replace(boss_col_orig, boss_col_new)

    # 5. Play boss weapon sound when Boss fires
    boss_fire_orig = """for i in range(spread_n):
                    sp = (i / (spread_n - 1) - 0.5) * 0.6
                    b = Bullet(self.center_x, self.center_y,"""
    boss_fire_new = """arcade.play_sound(arcade.load_sound(os.path.join(SOUND_PATH, "boss_weapon_sound.mp3")))
                for i in range(spread_n):
                    sp = (i / (spread_n - 1) - 0.5) * 0.6
                    b = Bullet(self.center_x, self.center_y,"""
    text = text.replace(boss_fire_orig, boss_fire_new)

    # 6. Monkey-patch arcade.draw_text for Times New Roman, Bold, Dark Gray
    patch = '''import arcade

_original_draw_text = arcade.draw_text

def _custom_draw_text(text, start_x, start_y, color=(40, 40, 40, 255), font_size=12, width=0, align="left",
                      font_name="Times New Roman", bold=True, italic=False, anchor_x="left", anchor_y="baseline",
                      rotation=0, *args, **kwargs):
    # Override visual settings based on user request
    color = (40, 40, 40, 255) # Dark Gray
    bold = True
    font_name = "Times New Roman"
    
    # Forward to the original function 
    # Notice we pass the overridden parameters explicitly.
    # In arcade < 3.0, draw_text args might differ, so kwargs capture the rest.
    return _original_draw_text(text, start_x, start_y, color, font_size, width, align, font_name, bold, italic, anchor_x, anchor_y, rotation, *args, **kwargs)

arcade.draw_text = _custom_draw_text
'''
    text = text.replace('import arcade', patch, 1)

    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(text)

if __name__ == '__main__':
    main()
