import arcade
import math
from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, C_DEEP_SPACE

class MorphTransitionView(arcade.View):
    """Cinematic morph transition between views."""
    def __init__(self, from_view, to_view, duration=2.5):
        super().__init__()
        self.from_view = from_view
        self.to_view = to_view
        self.duration = duration
        self.time = 0.0

    def on_update(self, delta_time):
        self.time += delta_time
        if hasattr(self.from_view, 'on_update'):
            self.from_view.on_update(delta_time)
        if hasattr(self.to_view, 'on_update'):
            self.to_view.on_update(delta_time)
            
        if self.time >= self.duration:
            self.window.show_view(self.to_view)

    def on_draw(self):
        w = SCREEN_WIDTH
        h = SCREEN_HEIGHT
        rad = math.atan2(h, w)
        
        progress = min(1.0, max(0.0, self.time / self.duration))
        
        # Ship travels across screen during first 40% (0.0 -> 0.4)
        flight_t = min(1.0, progress / 0.4)
        is_sliced = progress >= 0.2
        
        self.window.clear()
        
        if not is_sliced:
            self.from_view.on_draw()
        else:
            self.to_view.on_draw()
            
            # The slices slide apart smoothly
            slide_progress = min(1.0, (progress - 0.2) / 0.8)
            ease_slide = 1.0 - (1.0 - slide_progress)**3
            
            if ease_slide < 0.95:
                nx = -math.sin(rad)
                ny = math.cos(rad)
                dist = ease_slide * (h * 0.8)
                
                ptl = [(0, 0), (0, h), (w, h)]
                pbr = [(0, 0), (w, 0), (w, h)]
                
                ptl_shifted = [(x + nx * dist, y + ny * dist) for x, y in ptl]
                pbr_shifted = [(x - nx * dist, y - ny * dist) for x, y in pbr]
                
                alpha = max(0, int(255 * (1.0 - ease_slide)**2))
                c = (C_DEEP_SPACE[0], C_DEEP_SPACE[1], C_DEEP_SPACE[2], alpha)
                
                arcade.draw_polygon_filled(ptl_shifted, c)
                arcade.draw_polygon_filled(pbr_shifted, c)
                
                line_alpha = max(0, int(255 * (1.0 - ease_slide)**3))
                arcade.draw_line(*ptl_shifted[0], *ptl_shifted[2], (100, 255, 255, line_alpha), 5)
                arcade.draw_line(*pbr_shifted[0], *pbr_shifted[2], (100, 255, 255, line_alpha), 5)

        # Draw the sleek white spaceship
        if flight_t < 1.0:
            ship_x = -0.2 * w + flight_t * 1.4 * w
            ship_y = -0.2 * h + flight_t * 1.4 * h
            
            scale = 45
            poly = [
                (scale*1.8, 0),
                (-scale*1.0, scale*0.5),
                (-scale*0.4, 0),
                (-scale*1.0, -scale*0.5)
            ]
            
            ship_pts = []
            for px, py in poly:
                rx = px * math.cos(rad) - py * math.sin(rad)
                ry = px * math.sin(rad) + py * math.cos(rad)
                ship_pts.append((ship_x + rx, ship_y + ry))
                
            arcade.draw_polygon_filled(ship_pts, arcade.color.WHITE)
            
            # Thruster trail
            t1x, t1y = ship_x + (-scale*0.8)*math.cos(rad), ship_y + (-scale*0.8)*math.sin(rad)
            t2x, t2y = ship_x + (-scale*2.5)*math.cos(rad), ship_y + (-scale*2.5)*math.sin(rad)
            
            arcade.draw_line(t1x, t1y, t2x, t2y, (0, 220, 255, 200), max(1, 10))
