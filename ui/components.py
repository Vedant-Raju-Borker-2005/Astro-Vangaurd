import arcade
import math
import random
from core.constants import C_GOLD, C_SILVER, C_STEEL, C_CHROME, C_WHITE, C_CYAN, SCREEN_WIDTH, SCREEN_HEIGHT

def draw_metal_panel(x, y, w, h, alpha=255, accent=False):
    """Layered rectangle simulating brushed-metal surface."""
    alpha = 0  # Force invisibility as requested
    arcade.draw_rectangle_filled(x, y, w, h, (12, 14, 22, min(255, alpha)))
    ht = max(2, int(h * 0.06))
    arcade.draw_rectangle_filled(x, y + (h - ht) / 2, w, ht,
                                 (90, 100, 130, min(200, alpha)))
    hm = max(2, int(h * 0.03))
    arcade.draw_rectangle_filled(x, y, w, hm,
                                 (60, 68, 90, min(140, alpha)))
    hs = max(2, int(h * 0.08))
    arcade.draw_rectangle_filled(x, y - (h - hs) / 2, w, hs,
                                 (4, 4, 10, min(200, alpha)))
    brd_col = (C_GOLD[0], C_GOLD[1], C_GOLD[2], min(200, alpha)) if accent else \
              (50, 58, 80, min(180, alpha))
    arcade.draw_rectangle_outline(x, y, w, h, brd_col, 1)

def draw_hex_badge(cx, cy, r, col, alpha=255):
    """Hexagon badge."""
    alpha = 0  # Force invisibility as requested
    pts = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    c = (*col[:3], alpha)
    arcade.draw_polygon_filled(pts, c)
    arcade.draw_polygon_outline(pts, (C_GOLD[0], C_GOLD[1], C_GOLD[2], alpha), 2)

def draw_corner_bracket(x, y, w, h, size=18, col=(180, 162, 48, 255)):
    """Four corner L-brackets for a panel."""
    col = (*col[:3], 0)  # Force invisibility as requested
    lw = 2
    arcade.draw_line(x - w/2, y + h/2, x - w/2 + size, y + h/2, col, lw)
    arcade.draw_line(x - w/2, y + h/2, x - w/2, y + h/2 - size, col, lw)
    arcade.draw_line(x + w/2, y + h/2, x + w/2 - size, y + h/2, col, lw)
    arcade.draw_line(x + w/2, y + h/2, x + w/2, y + h/2 - size, col, lw)
    arcade.draw_line(x - w/2, y - h/2, x - w/2 + size, y - h/2, col, lw)
    arcade.draw_line(x - w/2, y - h/2, x - w/2, y - h/2 + size, col, lw)
    arcade.draw_line(x + w/2, y - h/2, x + w/2 - size, y - h/2, col, lw)
    arcade.draw_line(x + w/2, y - h/2, x + w/2, y - h/2 + size, col, lw)

class NebulaCloud:
    def __init__(self):
        self.blobs = []
        configs = [
            (200,  550, 280, 200, (30, 0, 70,  30)),
            (900,  300, 320, 200, (0,  10, 80, 28)),
            (640,  650, 360, 180, (0,  25, 80, 22)),
            (100,  200, 200, 150, (60, 0,  90, 20)),
            (1100, 600, 240, 180, (0,  40, 100,22)),
            (500,  100, 300, 160, (20, 0,  80, 18)),
        ]
        for x, y, rx, ry, col in configs:
            self.blobs.append((x, y, rx, ry, col))

    def draw(self):
        for x, y, rx, ry, col in self.blobs:
            for i in range(6, 0, -1):
                f = i / 6
                a = int(col[3] * (1 - f * 0.7))
                c = (col[0], col[1], col[2], a)
                arcade.draw_ellipse_filled(x, y, rx * f, ry * f, c)

class LoadingStarField:
    def __init__(self):
        self.stars = []
        for _ in range(260):
            x     = random.uniform(0, SCREEN_WIDTH)
            y     = random.uniform(0, SCREEN_HEIGHT)
            size  = random.uniform(0.3, 2.2)
            speed = random.uniform(0.05, 0.35) * size
            alpha = random.randint(60, 220)
            twinkle_phase = random.uniform(0, math.pi * 2)
            self.stars.append([x, y, size, speed, alpha, twinkle_phase])

    def update(self, t: float):
        for s in self.stars:
            s[1] -= s[3]
            if s[1] < -4:
                s[1] = SCREEN_HEIGHT + 4
                s[0] = random.uniform(0, SCREEN_WIDTH)
            s[4] = int(80 + 140 * (0.5 + 0.5 * math.sin(t * 2.5 + s[5])))

    def draw(self):
        for x, y, size, _, alpha, _ in self.stars:
            col = (int(180 + 75 * (size / 2.2)),
                   int(180 + 75 * (size / 2.2)),
                   255, alpha)
            arcade.draw_circle_filled(x, y, size, col)


class LoadingBar:
    def __init__(self, cx, cy, w, h):
        self.cx, self.cy = cx, cy
        self.w, self.h = w, h
        self.progress = 0.0
        self.target   = 0.0
        self._segments = 32
        self._glint_pos = 0.0

    def set_target(self, t: float):
        self.target = min(1.0, max(0.0, t))

    def update(self):
        speed = 0.006 if self.target - self.progress > 0.05 else 0.002
        if self.progress < self.target:
            self.progress = min(self.target, self.progress + speed)
        self._glint_pos = (self._glint_pos + 0.015) % 1.2

    def draw(self):
        x = self.cx - self.w / 2
        y = self.cy - self.h / 2

        arcade.draw_rectangle_filled(self.cx, self.cy, self.w, self.h, (8, 10, 20, 230))
        arcade.draw_rectangle_outline(self.cx, self.cy, self.w, self.h, (40, 50, 80, 200), 1)

        if self.progress <= 0:
            return

        fill_w = self.w * self.progress
        seg_w = fill_w / self._segments
        gap   = max(1, seg_w * 0.12)
        for i in range(self._segments):
            sx = x + i * seg_w
            if sx + seg_w > x + fill_w:
                break
            t = i / self._segments
            r = int(0   + 200 * t)
            g = int(210 - 50  * t)
            b = int(255 - 205 * t)
            arcade.draw_rectangle_filled(
                sx + seg_w / 2, self.cy,
                max(0, seg_w - gap), self.h - 2,
                (r, g, b, 220))

        gx = x + self._glint_pos * self.w
        if gx < x + fill_w:
            gw = 30
            arcade.draw_rectangle_filled(
                min(gx + gw / 2, x + fill_w - gw / 2),
                self.cy, gw, self.h,
                (255, 255, 255, 60))

        ship_x = x + fill_w
        s = 8
        ship_pts = [
            (ship_x + s*2.5, self.cy),
            (ship_x - s,     self.cy + s*1.2),
            (ship_x - s/2,   self.cy),
            (ship_x - s,     self.cy - s*1.2),
        ]
        arcade.draw_polygon_filled(ship_pts, (240, 248, 255, 255))
        arcade.draw_polygon_outline(ship_pts, (0, 210, 255, 255), 1)

        arcade.draw_circle_filled(ship_x - s - 2, self.cy, s*0.8, (255, 120, 0, 220))
        arcade.draw_circle_filled(ship_x - s - 5, self.cy, s*0.5, (255, 220, 0, 255))
        arcade.draw_circle_filled(ship_x - s - 9, self.cy, s*0.3, (255, 255, 255, 200))

        arcade.draw_rectangle_outline(self.cx, self.cy, self.w, self.h,
                                      (60, 70, 100, 180), 1)

class ShipSilhouette:
    def __init__(self, cx, cy):
        self.cx, self.cy = cx, cy
        self.angle = 0.0
        self.scale = 1.0
        self._pulse_t = 0.0
        self._trail: list = []

    def update(self, t: float):
        self.angle += 0.6
        self._pulse_t = t
        self.scale = 0.92 + 0.08 * math.sin(t * 2.0)
        self._trail.append(self.angle)
        if len(self._trail) > 18:
            self._trail.pop(0)

    def _ship_points(self, cx, cy, angle_deg, scale=1.0):
        s = 36 * scale
        pts = [
            (0,     s * 1.5),
            (-s,   -s * 1.0),
            (0,    -s * 0.5),
            (s,    -s * 1.0),
        ]
        rad = math.radians(angle_deg)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        return [(cx + x * cos_a - y * sin_a,
                 cy + x * sin_a + y * cos_a) for x, y in pts]

    def draw(self):
        for i, a in enumerate(self._trail):
            alpha = int(8 + 25 * (i / len(self._trail)))
            pts = self._ship_points(self.cx, self.cy, a, self.scale)
            arcade.draw_polygon_filled(pts, (0, 180, 255, alpha))

        pts = self._ship_points(self.cx, self.cy, self.angle, self.scale)
        arcade.draw_polygon_filled(pts, (10, 20, 50, 240))
        arcade.draw_polygon_outline(pts, (0, 200, 255, 220), 2)

        glow_r = 52 * self.scale
        pulse_a = int(30 + 40 * math.sin(self._pulse_t * 3))
        arcade.draw_circle_outline(self.cx, self.cy, glow_r,
                                   (0, 180, 255, pulse_a), 8)
        arcade.draw_circle_outline(self.cx, self.cy, glow_r + 10,
                                   (0, 80, 160, pulse_a // 2), 4)

        rad = math.radians(self.angle + 180)
        ex = self.cx + math.cos(rad) * 36 * self.scale
        ey = self.cy + math.sin(rad) * 36 * self.scale
        for _ in range(3):
            ox = random.uniform(-8, 8)
            oy = random.uniform(-8, 8)
            a  = random.randint(80, 200)
            arcade.draw_circle_filled(ex + ox, ey + oy, random.uniform(1, 4),
                                      (255, 160, 40, a))


class V2Logo:
    def __init__(self, cx, cy):
        self.cx, self.cy = cx, cy
        self.reveal = 0.0
        self.shimmer_t = 0.0

    def update(self, t: float, reveal: float):
        self.reveal = min(1.0, reveal)
        self.shimmer_t = t

    def draw(self):
        r = self.reveal
        if r <= 0:
            return

        v_reveal = min(1.0, r / 0.6)
        alpha = int(v_reveal * 255)
        st = self.shimmer_t

        cx, cy = self.cx, self.cy + 30 * v_reveal
        w = 110 * v_reveal
        h = 100 * v_reveal
        th = 48 * v_reveal

        if r > 0.6:
            text_reveal = (r - 0.6) / 0.4
            text_a = int(text_reveal * 255)
            ease_out = 1.0 - (1.0 - text_reveal)**3

            text_x = self.cx + 20 + (60 * ease_out)
            text_y = self.cy - 35

            arcade.draw_text("PRODUCTION", text_x, text_y - 2,
                             (20, 30, 45, text_a),
                             font_size=42, bold=True, anchor_x="left", anchor_y="center", font_name="Times New Roman")
            arcade.draw_text("PRODUCTION", text_x, text_y,
                             (C_STEEL[0], C_STEEL[1], C_STEEL[2], text_a),
                             font_size=42, bold=True, anchor_x="left", anchor_y="center", font_name="Times New Roman")
            arcade.draw_text("PRODUCTION", text_x, text_y + 2,
                             (C_SILVER[0], C_SILVER[1], C_SILVER[2], text_a),
                             font_size=42, bold=True, anchor_x="left", anchor_y="center", font_name="Times New Roman")
            arcade.draw_text("PRODUCTION", text_x, text_y + 2,
                             (C_WHITE[0], C_WHITE[1], C_WHITE[2], int(text_a*0.6)),
                             font_size=42, bold=True, anchor_x="left", anchor_y="center", font_name="Times New Roman")

        pts_left = [
            (cx - w, cy + h),
            (cx - w + th*1.2, cy + h),
            (cx + th*0.2, cy - h + th*0.8),
            (cx - th*0.6, cy - h)
        ]

        pts_right = [
            (cx + w, cy + h),
            (cx + w - th*1.2, cy + h),
            (cx - th*0.2, cy - h + th*0.8),
            (cx + th*0.6, cy - h)
        ]

        bevel_left = [
            (cx - w + th*0.6, cy + h),
            (cx - th*0.2, cy - h + th*0.4),
            (cx - w, cy + h)
        ]
        bevel_right = [
            (cx + w - th*0.6, cy + h),
            (cx + th*0.2, cy - h + th*0.4),
            (cx + w, cy + h)
        ]

        arcade.draw_polygon_filled(pts_left, (C_SILVER[0], C_SILVER[1], C_SILVER[2], alpha))
        arcade.draw_polygon_filled(bevel_left, (C_STEEL[0], C_STEEL[1], C_STEEL[2], alpha))

        arcade.draw_polygon_filled(pts_right, (C_CHROME[0], C_CHROME[1], C_CHROME[2], alpha))
        arcade.draw_polygon_filled(bevel_right, (40, 50, 70, alpha))

        arcade.draw_polygon_outline(pts_left, (C_CYAN[0], C_CYAN[1], C_CYAN[2], int(alpha*0.8)), 3)
        arcade.draw_polygon_outline(pts_right, (C_CYAN[0], C_CYAN[1], C_CYAN[2], int(alpha*0.8)), 3)

        two_w = 48 * v_reveal
        two_h = 55 * v_reveal
        two_th = 16 * v_reveal
        tx = cx + w - th*0.3
        ty = cy + h

        L = two_th
        lx, rx = tx, tx + two_w
        y1, y2, y3 = ty - L/2, ty - two_h/2, ty - two_h + L/2

        arcade.draw_rectangle_filled((lx+rx)/2, y1, rx-lx, L, (C_SILVER[0], C_SILVER[1], C_SILVER[2], alpha))
        arcade.draw_rectangle_filled((lx+rx)/2, y2, rx-lx, L, (C_CHROME[0], C_CHROME[1], C_CHROME[2], alpha))
        arcade.draw_rectangle_filled((lx+rx)/2, y3, rx-lx, L, (C_SILVER[0], C_SILVER[1], C_SILVER[2], alpha))
        arcade.draw_rectangle_filled(rx - L/2, (y1+y2)/2, L, y1-y2 + L, (C_CHROME[0], C_CHROME[1], C_CHROME[2], alpha))
        arcade.draw_rectangle_filled(lx + L/2, (y2+y3)/2, L, y2-y3 + L, (C_STEEL[0], C_STEEL[1], C_STEEL[2], alpha))

        burst_x, burst_y = rx, ty
        for i in range(16):
            px = burst_x + math.sin(st*5 + i) * random.uniform(5, 30) * v_reveal
            py = burst_y + math.cos(st*4 + i*2) * random.uniform(5, 30) * v_reveal
            pa = int(alpha * random.uniform(0.4, 1.0))
            arcade.draw_circle_filled(px, py, random.uniform(1, 4), (C_CYAN[0], C_CYAN[1], C_CYAN[2], pa))
            arcade.draw_circle_filled(px, py, 1, (255, 255, 255, pa))
