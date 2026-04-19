import arcade

# Detect major version
_arcade_major = int(arcade.__version__.split('.')[0])

def apply_patches():
    # --- Compatibility Patch for arcade.Sprite ---
    _original_sprite_init = arcade.Sprite.__init__
    def _new_sprite_init(self, *args, **kwargs):
        if 'texture' in kwargs and _arcade_major >= 3:
            tex = kwargs.pop('texture')
            if not args and tex is not None:
                args = (tex,) + args
        _original_sprite_init(self, *args, **kwargs)
        self.alive = True
    arcade.Sprite.__init__ = _new_sprite_init

    _original_sprite_kill = arcade.Sprite.kill
    def _new_sprite_kill(self):
        self.alive = False
        _original_sprite_kill(self)
    arcade.Sprite.kill = _new_sprite_kill

    # --- Arcade 3.x Compatibility Shims ---
    # These functions were removed/renamed in Arcade 3.0
    if _arcade_major >= 3:

        def _draw_rect_filled_shim(center_x, center_y, width, height, color, tilt_angle=0):
            left   = center_x - width  / 2.0
            bottom = center_y - height / 2.0
            if tilt_angle == 0:
                arcade.draw_xywh_rectangle_filled(left, bottom, width, height, color) \
                    if hasattr(arcade, 'draw_xywh_rectangle_filled') else \
                    arcade.draw_rect_filled(arcade.XYWH(left, bottom, width, height), color)
            else:
                arcade.draw_rect_filled(arcade.XYWH(left, bottom, width, height), color, tilt_angle)

        def _draw_rect_outline_shim(center_x, center_y, width, height, color, border_width=1, tilt_angle=0):
            left   = center_x - width  / 2.0
            bottom = center_y - height / 2.0
            if tilt_angle == 0:
                arcade.draw_xywh_rectangle_outline(left, bottom, width, height, color, border_width) \
                    if hasattr(arcade, 'draw_xywh_rectangle_outline') else \
                    arcade.draw_rect_outline(arcade.XYWH(left, bottom, width, height), color, border_width)
            else:
                arcade.draw_rect_outline(arcade.XYWH(left, bottom, width, height), color, border_width, tilt_angle)

        def _draw_texture_rectangle_shim(center_x, center_y, width, height, texture, angle=0.0, alpha=255, **kwargs):
            rect = arcade.XYWH(center_x - width / 2.0, center_y - height / 2.0, width, height)
            arcade.draw_texture_rect(texture, rect, angle=angle, alpha=alpha, **kwargs)

        def _draw_lrwh_rectangle_textured_shim(left, bottom, width, height, texture, angle=0.0, alpha=255, **kwargs):
            rect = arcade.XYWH(left, bottom, width, height)
            arcade.draw_texture_rect(texture, rect, angle=angle, alpha=alpha, **kwargs)

        arcade.draw_rectangle_filled       = _draw_rect_filled_shim
        arcade.draw_rectangle_outline      = _draw_rect_outline_shim
        arcade.draw_texture_rectangle      = _draw_texture_rectangle_shim
        arcade.draw_lrwh_rectangle_textured = _draw_lrwh_rectangle_textured_shim
    # -------------------------------------------
