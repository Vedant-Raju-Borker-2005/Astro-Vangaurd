"""
AstroVanguard: AI Tactical Space Siege — Loading Screen
V² Productions Presentation
Rockstar-studio style cinematic loading experience.

Requirements: arcade 3.0+, Python 3.9+
Run standalone: python astrovanguard_loading.py
"""

import pyglet
pyglet.options['audio'] = ('openal', 'directsound', 'silent')

import arcade
import math
import random
import time

SCREEN_WIDTH  = 1280
SCREEN_HEIGHT = 800
SCREEN_TITLE  = "AstroVanguard — Loading"

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


# ══════════════════════════════════════════════════════════
# STAR FIELD
# ══════════════════════════════════════════════════════════
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
            # Twinkle
            s[4] = int(80 + 140 * (0.5 + 0.5 * math.sin(t * 2.5 + s[5])))

    def draw(self):
        for x, y, size, _, alpha, _ in self.stars:
            col = (int(180 + 75 * (size / 2.2)),
                   int(180 + 75 * (size / 2.2)),
                   255, alpha)
            arcade.draw_circle_filled(x, y, size, col)


# ══════════════════════════════════════════════════════════
# NEBULA CLOUD (soft overlapping blobs)
# ══════════════════════════════════════════════════════════
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
            # Draw concentric ellipses for soft glow
            for i in range(6, 0, -1):
                f = i / 6
                a = int(col[3] * (1 - f * 0.7))
                c = (col[0], col[1], col[2], a)
                arcade.draw_ellipse_filled(x, y, rx * f, ry * f, c)


# ══════════════════════════════════════════════════════════
# METALLIC PANEL HELPERS
# ══════════════════════════════════════════════════════════
def draw_metal_panel(x, y, w, h, alpha=255, accent=False):
    """Layered rectangle simulating a subtle glass-like or light metal surface."""
    alpha = 0  # Force invisibility as requested
    # Base dark steel with much lower opacity
    base_a = min(110, alpha)
    arcade.draw_rectangle_filled(x, y, w, h, (12, 14, 22, base_a))
    # Highlight strip (top edge) - more subtle
    ht = max(1, int(h * 0.04))
    arcade.draw_rectangle_filled(x, y + (h - ht) / 2, w, ht,
                                 (90, 100, 130, min(80, alpha)))
    # Mid shine - more subtle
    hm = max(1, int(h * 0.02))
    arcade.draw_rectangle_filled(x, y, w, hm,
                                 (60, 68, 90, min(60, alpha)))
    # Bottom shadow - more subtle
    hs = max(1, int(h * 0.05))
    arcade.draw_rectangle_filled(x, y - (h - hs) / 2, w, hs,
                                 (4, 4, 10, min(90, alpha)))
    # Very light border instead of heavy outline
    brd_col = (C_GOLD[0], C_GOLD[1], C_GOLD[2], min(40, alpha)) if accent else \
              (50, 58, 80, min(30, alpha))
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
    # TL
    arcade.draw_line(x - w/2, y + h/2, x - w/2 + size, y + h/2, col, lw)
    arcade.draw_line(x - w/2, y + h/2, x - w/2, y + h/2 - size, col, lw)
    # TR
    arcade.draw_line(x + w/2, y + h/2, x + w/2 - size, y + h/2, col, lw)
    arcade.draw_line(x + w/2, y + h/2, x + w/2, y + h/2 - size, col, lw)
    # BL
    arcade.draw_line(x - w/2, y - h/2, x - w/2 + size, y - h/2, col, lw)
    arcade.draw_line(x - w/2, y - h/2, x - w/2, y - h/2 + size, col, lw)
    # BR
    arcade.draw_line(x + w/2, y - h/2, x + w/2 - size, y - h/2, col, lw)
    arcade.draw_line(x + w/2, y - h/2, x + w/2, y - h/2 + size, col, lw)


# ══════════════════════════════════════════════════════════
# LOADING BAR
# ══════════════════════════════════════════════════════════
class LoadingBar:
    def __init__(self, cx, cy, w, h):
        self.cx, self.cy = cx, cy
        self.w, self.h = w, h
        self.progress = 0.0       # 0.0 → 1.0
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

        # Trough
        arcade.draw_rectangle_filled(self.cx, self.cy, self.w, self.h, (8, 10, 20, 230))
        arcade.draw_rectangle_outline(self.cx, self.cy, self.w, self.h, (40, 50, 80, 200), 1)

        if self.progress <= 0:
            return

        fill_w = self.w * self.progress

        # Segmented fill
        seg_w = fill_w / self._segments
        gap   = max(1, seg_w * 0.12)
        for i in range(self._segments):
            sx = x + i * seg_w
            if sx + seg_w > x + fill_w:
                break
            t = i / self._segments
            # Color gradient: cyan → gold
            r = int(0   + 200 * t)
            g = int(210 - 50  * t)
            b = int(255 - 205 * t)
            arcade.draw_rectangle_filled(
                sx + seg_w / 2, self.cy,
                max(0, seg_w - gap), self.h - 2,
                (r, g, b, 220))

        # Glint sweep
        gx = x + self._glint_pos * self.w
        if gx < x + fill_w:
            gw = 30
            arcade.draw_rectangle_filled(
                min(gx + gw / 2, x + fill_w - gw / 2),
                self.cy, gw, self.h,
                (255, 255, 255, 60))

        # Mini spaceship at leading edge tracking progress
        ship_x = x + fill_w
        s = 8
        ship_pts = [
            (ship_x + s*2.5, self.cy),
            (ship_x - s,     self.cy + s*1.2),
            (ship_x - s/2,   self.cy),
            (ship_x - s,     self.cy - s*1.2),
        ]
        # Ship hull
        arcade.draw_polygon_filled(ship_pts, (240, 248, 255, 255))
        arcade.draw_polygon_outline(ship_pts, (0, 210, 255, 255), 1)
        
        # Engine flare trail behind the ship
        arcade.draw_circle_filled(ship_x - s - 2, self.cy, s*0.8, (255, 120, 0, 220))
        arcade.draw_circle_filled(ship_x - s - 5, self.cy, s*0.5, (255, 220, 0, 255))
        arcade.draw_circle_filled(ship_x - s - 9, self.cy, s*0.3, (255, 255, 255, 200))

        # Outline on fill
        arcade.draw_rectangle_outline(self.cx, self.cy, self.w, self.h,
                                      (60, 70, 100, 180), 1)


# ══════════════════════════════════════════════════════════
# SPINNING SHIP SILHOUETTE
# ══════════════════════════════════════════════════════════
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
        """Triangle ship silhouette points."""
        s = 36 * scale
        pts = [
            (0,     s * 1.5),   # nose
            (-s,   -s * 1.0),   # left wing
            (0,    -s * 0.5),   # tail center
            (s,    -s * 1.0),   # right wing
        ]
        rad = math.radians(angle_deg)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        return [(cx + x * cos_a - y * sin_a,
                 cy + x * sin_a + y * cos_a) for x, y in pts]

    def draw(self):
        # Trail ghosts
        for i, a in enumerate(self._trail):
            alpha = int(8 + 25 * (i / len(self._trail)))
            pts = self._ship_points(self.cx, self.cy, a, self.scale)
            arcade.draw_polygon_filled(pts, (0, 180, 255, alpha))

        # Main ship
        pts = self._ship_points(self.cx, self.cy, self.angle, self.scale)
        arcade.draw_polygon_filled(pts, (10, 20, 50, 240))
        arcade.draw_polygon_outline(pts, (0, 200, 255, 220), 2)

        # Glow ring
        glow_r = 52 * self.scale
        pulse_a = int(30 + 40 * math.sin(self._pulse_t * 3))
        arcade.draw_circle_outline(self.cx, self.cy, glow_r,
                                   (0, 180, 255, pulse_a), 8)
        arcade.draw_circle_outline(self.cx, self.cy, glow_r + 10,
                                   (0, 80, 160, pulse_a // 2), 4)

        # Engine sparks
        rad = math.radians(self.angle + 180)
        ex = self.cx + math.cos(rad) * 36 * self.scale
        ey = self.cy + math.sin(rad) * 36 * self.scale
        for _ in range(3):
            ox = random.uniform(-8, 8)
            oy = random.uniform(-8, 8)
            a  = random.randint(80, 200)
            arcade.draw_circle_filled(ex + ox, ey + oy, random.uniform(1, 4),
                                      (255, 160, 40, a))


# ══════════════════════════════════════════════════════════
# V² LOGO RENDERER
# ══════════════════════════════════════════════════════════
class V2Logo:
    def __init__(self, cx, cy):
        self.cx, self.cy = cx, cy
        self.reveal = 0.0     # 0→1
        self.shimmer_t = 0.0

    def update(self, t: float, reveal: float):
        self.reveal = min(1.0, reveal)
        self.shimmer_t = t

    def draw(self):
        r = self.reveal
        if r <= 0:
            return

        # V lands first (0.0 to 0.6)
        v_reveal = min(1.0, r / 0.6)
        alpha = int(v_reveal * 255)
        st = self.shimmer_t
        
        # Large Majestic 3D Metallic V
        cx, cy = self.cx, self.cy + 30 * v_reveal
        w = 110 * v_reveal       # half width at top
        h = 100 * v_reveal       # height
        th = 48 * v_reveal       # very thick arms

        # "PRODUCTION" text sliding out from behind the V to the right
        if r > 0.6:
            text_reveal = (r - 0.6) / 0.4
            text_a = int(text_reveal * 255)
            # Ease-out for smooth sliding
            ease_out = 1.0 - (1.0 - text_reveal)**3
            
            # Start behind V (cx + 20) and slide to the right (cx + 80)
            text_x = self.cx + 20 + (60 * ease_out)
            # Align slightly lower with the V's center
            text_y = self.cy - 35
            
            # Outer chrome emboss
            arcade.draw_text("PRODUCTION", text_x, text_y - 2,
                             (20, 30, 45, text_a),
                             font_size=42, bold=True, anchor_x="left", anchor_y="center", font_name="Times New Roman")
            arcade.draw_text("PRODUCTION", text_x, text_y,
                             (C_STEEL[0], C_STEEL[1], C_STEEL[2], text_a),
                             font_size=42, bold=True, anchor_x="left", anchor_y="center", font_name="Times New Roman")
            # Inner bright metallic text
            arcade.draw_text("PRODUCTION", text_x, text_y + 2,
                             (C_SILVER[0], C_SILVER[1], C_SILVER[2], text_a),
                             font_size=42, bold=True, anchor_x="left", anchor_y="center", font_name="Times New Roman")
            # Glowing core
            arcade.draw_text("PRODUCTION", text_x, text_y + 2,
                             (C_WHITE[0], C_WHITE[1], C_WHITE[2], int(text_a*0.6)),
                             font_size=42, bold=True, anchor_x="left", anchor_y="center", font_name="Times New Roman")
        
        # Left Arm
        pts_left = [
            (cx - w, cy + h),                   # Outer top
            (cx - w + th*1.2, cy + h),          # Inner top
            (cx + th*0.2, cy - h + th*0.8),     # Inner bottom junction
            (cx - th*0.6, cy - h)               # Outer bottom
        ]
        
        # Right Arm
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

        # Draw left arm
        arcade.draw_polygon_filled(pts_left, (C_SILVER[0], C_SILVER[1], C_SILVER[2], alpha))
        arcade.draw_polygon_filled(bevel_left, (C_STEEL[0], C_STEEL[1], C_STEEL[2], alpha))
        
        # Draw right arm
        arcade.draw_polygon_filled(pts_right, (C_CHROME[0], C_CHROME[1], C_CHROME[2], alpha))
        arcade.draw_polygon_filled(bevel_right, (40, 50, 70, alpha)) # Darker inner bevel
        
        arcade.draw_polygon_outline(pts_left, (C_CYAN[0], C_CYAN[1], C_CYAN[2], int(alpha*0.8)), 3)
        arcade.draw_polygon_outline(pts_right, (C_CYAN[0], C_CYAN[1], C_CYAN[2], int(alpha*0.8)), 3)
        
        # ── Superscript "2" — blocky geometric style (from rectangles) ──
        two_w  = 52 * v_reveal    # total width
        two_h  = 68 * v_reveal    # total height
        two_th = 13 * v_reveal    # bar thickness

        tx = cx + w + th * 0.05
        ty = cy + h + 25 * v_reveal   # ty = top edge of the "2" — raised above V top

        L  = two_th
        lx = tx              # left edge x
        rx = tx + two_w      # right edge x
        top_y = ty
        bot_y = ty - two_h
        mid_y = ty - two_h * 0.5

        # 1) Top horizontal bar
        arcade.draw_rectangle_filled(
            (lx + rx) / 2, top_y - L / 2,
            two_w, L,
            (C_SILVER[0], C_SILVER[1], C_SILVER[2], alpha))

        # 2) Right vertical drop: bottom-of-top-bar → top-of-mid-bar
        rt_top = top_y - L
        rt_bot = mid_y + L / 2
        if rt_top > rt_bot:
            arcade.draw_rectangle_filled(
                rx - L / 2, (rt_top + rt_bot) / 2,
                L, rt_top - rt_bot,
                (C_CHROME[0], C_CHROME[1], C_CHROME[2], alpha))

        # 3) Mid horizontal bar
        arcade.draw_rectangle_filled(
            (lx + rx) / 2, mid_y,
            two_w, L,
            (C_CHROME[0], C_CHROME[1], C_CHROME[2], alpha))

        # 4) Left vertical drop: bottom-of-mid-bar → top-of-bottom-bar
        lt_top = mid_y - L / 2
        lt_bot = bot_y + L
        if lt_top > lt_bot:
            arcade.draw_rectangle_filled(
                lx + L / 2, (lt_top + lt_bot) / 2,
                L, lt_top - lt_bot,
                (C_STEEL[0], C_STEEL[1], C_STEEL[2], alpha))

        # 5) Bottom horizontal bar
        arcade.draw_rectangle_filled(
            (lx + rx) / 2, bot_y + L / 2,
            two_w, L,
            (C_SILVER[0], C_SILVER[1], C_SILVER[2], alpha))

        # Cyan outline glow
        arcade.draw_rectangle_outline(
            (lx + rx) / 2, (top_y + bot_y) / 2,
            two_w, two_h,
            (C_CYAN[0], C_CYAN[1], C_CYAN[2], int(alpha * 0.45)), 1)

        # Sparkles near top-right of the "2"
        burst_x, burst_y = rx, top_y
        for i in range(16):
            px = burst_x + math.sin(st*5 + i) * random.uniform(4, 22) * v_reveal
            py = burst_y + math.cos(st*4 + i*2) * random.uniform(4, 22) * v_reveal
            pa = int(alpha * random.uniform(0.4, 1.0))
            arcade.draw_circle_filled(px, py, random.uniform(1, 3),
                                      (C_CYAN[0], C_CYAN[1], C_CYAN[2], pa))
            arcade.draw_circle_filled(px, py, 1, (255, 255, 255, pa))


# ══════════════════════════════════════════════════════════
# DIAGONAL SLICE TRANSITION  (NEW — does not modify above)
# ══════════════════════════════════════════════════════════
class DiagonalSliceTransition:
    """
    Cinematic 2D flat-vector transition:
      1. A sleek white spaceship flies rapidly from bottom-left to top-right.
      2. As it crosses screen centre the screen diagonally slices along the
         flight path angle.
      3. The two halves slide apart, fading the background to fully transparent.

    Call  start()  to trigger.
    Call  update(dt)  each frame.
    Call  draw()   after all other drawing is done.
    Read  .done    to know when the animation has finished.
    """

    # Flight angle matches the slice angle (bottom-left → top-right)
    ANGLE_DEG = 38.0          # degrees above horizontal

    # Durations (seconds)
    FLIGHT_DURATION  = 1.40   # ship crosses the full screen diagonal (slower, more cinematic)
    SLICE_START      = 0.45   # fraction along flight where slice begins
    SLICE_DURATION   = 0.65   # how long the halves slide apart
    FADE_DURATION    = 0.50   # opacity fade of each half

    def __init__(self, target_view=None):
        self._t       = 0.0
        self._active  = False
        self.done     = False
        self.target_view = target_view

        # ── derived geometry ──────────────────────────
        rad = math.radians(self.ANGLE_DEG)
        self._cos = math.cos(rad)
        self._sin = math.sin(rad)

        # Diagonal length of the screen
        self._diag = math.hypot(SCREEN_WIDTH, SCREEN_HEIGHT)

        # Ship spawns just off the bottom-left corner
        self._ship_start = (-60.0, -40.0)
        # Ship exits just past the top-right corner
        self._ship_end   = (SCREEN_WIDTH + 60.0, SCREEN_HEIGHT + 40.0)

        # Perpendicular unit vector to the flight path (points "upper-left")
        self._perp = (-self._sin, self._cos)   # 90° CCW from flight direction

        self._slice_t  = 0.0   # independent timer for the slice/fade phase
        self._slicing  = False

        # ── Load space_ship.png image texture ─────────
        import os as _os
        _base = _os.path.dirname(_os.path.abspath(__file__))
        _img_path = _os.path.join(_base, "assets", "images", "space_ship.png")
        try:
            self._ship_texture = arcade.load_texture(_img_path)
        except Exception:
            self._ship_texture = None

        # ── Load background.jpg (MenuView background) ──
        _bg_path = _os.path.join(_base, "assets", "images", "background.jpg")
        try:
            self._bg_texture = arcade.load_texture(_bg_path)
        except Exception:
            self._bg_texture = None

    # ── public API ────────────────────────────────────
    def start(self):
        self._t      = 0.0
        self._slice_t = 0.0
        self._active = True
        self._slicing = False
        self.done    = False

    @property
    def active(self):
        return self._active

    def update(self, dt: float):
        if not self._active or self.done:
            return

        self._t += dt

        # Update target view in the background if provided
        if self.target_view:
            self.target_view.on_update(dt)

        # When the ship reaches the centre of the screen, start slicing
        flight_frac = self._t / self.FLIGHT_DURATION
        if flight_frac >= self.SLICE_START and not self._slicing:
            self._slicing = True
            self._slice_t = 0.0

        if self._slicing:
            self._slice_t += dt

        # ── Hand off as soon as the ship exits top-right ──
        # The background.jpg has been visible in the growing gap the whole time;
        # switching views at this exact moment feels instant and seamless.
        if self._t >= self.FLIGHT_DURATION and not self.done:
            self.done    = True
            self._active = False

    # ── drawing helpers ───────────────────────────────
    @staticmethod
    def _ease_out_cubic(x: float) -> float:
        x = max(0.0, min(1.0, x))
        return 1.0 - (1.0 - x) ** 3

    @staticmethod
    def _ease_in_out(x: float) -> float:
        x = max(0.0, min(1.0, x))
        return x * x * (3 - 2 * x)

    def _ship_polygon(self, cx: float, cy: float, scale: float = 1.0):
        """
        Sleek white flat-vector ship pointing along the flight angle.
        Returns list of (x, y) tuples.
        """
        L  = 46 * scale   # body half-length
        Wf = 10 * scale   # fuselage half-width
        Ws = 32 * scale   # wing span half-width
        Wt =  8 * scale   # wing tip half-width
        Wr = 22 * scale   # wing root back offset

        # Local coords: +X = forward (nose), +Y = up (port side)
        body = [
            ( L,   0),       # nose
            ( Wr * 0.3,  Wf),  # fuselage top-front
            (-Wr,  Ws),      # port wing tip
            (-L,   Wt),      # port tail tip
            (-L * 0.7, 0),   # tail notch
            (-L,  -Wt),      # stbd tail tip
            (-Wr, -Ws),      # stbd wing tip
            ( Wr * 0.3, -Wf),# fuselage bottom-front
        ]

        # Rotate by flight angle and translate
        cos_a = self._cos
        sin_a = self._sin
        return [(cx + x * cos_a - y * sin_a,
                 cy + x * sin_a + y * cos_a) for x, y in body]

    def _engine_flare(self, ship_cx: float, ship_cy: float, scale: float):
        """Draw the engine exhaust behind the ship."""
        # Tail is in the -flight direction from centre
        tail_x = ship_cx - self._cos * 46 * scale
        tail_y = ship_cy - self._sin * 46 * scale

        for i, (radius, alpha, col) in enumerate([
            (12 * scale, 240, C_WHITE),
            (18 * scale, 180, (255, 200,  80, 255)),
            (26 * scale, 120, C_ORANGE),
            (36 * scale,  60, (200,  60,   0, 255)),
        ]):
            # Offset each layer further back along tail direction
            bx = tail_x - self._cos * i * 10 * scale
            by = tail_y - self._sin * i * 10 * scale
            c  = (*col[:3], alpha)
            arcade.draw_circle_filled(bx, by, radius, c)

    def _draw_slice_halves(self):
        """
        After the ship passes centre, slide the two screen halves apart
        perpendicularly to the flight path, revealing the menu background.
        """
        # Normalised progress through the slide phase
        slide_raw = self._slice_t / self.SLICE_DURATION
        slide     = self._ease_out_cubic(slide_raw)

        # Normalised progress through the fade phase (starts after slide)
        fade_raw  = (self._slice_t - self.SLICE_DURATION) / self.FADE_DURATION
        fade_raw  = max(0.0, fade_raw)
        fade      = self._ease_in_out(fade_raw)

        # Max displacement: half the screen diagonal
        max_disp  = self._diag * 0.55
        disp      = slide * max_disp

        # Panels are fully opaque during slide, then fade out together
        alpha_mul   = max(0.0, 1.0 - fade)
        panel_alpha = int(alpha_mul * 255)   # fully opaque while sliding
        if panel_alpha <= 0:
            return

        px, py = self._perp
        cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
        far    = self._diag + 200

        # ── Step 1: draw the menu background full-screen ──────────────
        # This is what becomes visible in the gap between the sliding halves.
        if hasattr(self, 'target_view') and self.target_view:
            self.target_view.on_draw()
        elif self._bg_texture is not None:
            arcade.draw_lrwh_rectangle_textured(
                0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, self._bg_texture)
        else:
            arcade.draw_rectangle_filled(
                SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2,
                SCREEN_WIDTH, SCREEN_HEIGHT, C_DEEP_SPACE)

        # ── Step 2: build the two sliding half-polygons ───────────────
        lp1 = (cx + self._cos * far, cy + self._sin * far)
        lp2 = (cx - self._cos * far, cy - self._sin * far)

        upper_off_x = px * disp
        upper_off_y = py * disp
        upper_pts = [
            (lp1[0] + upper_off_x, lp1[1] + upper_off_y),
            (lp2[0] + upper_off_x, lp2[1] + upper_off_y),
            (lp2[0] + upper_off_x + px * far, lp2[1] + upper_off_y + py * far),
            (lp1[0] + upper_off_x + px * far, lp1[1] + upper_off_y + py * far),
        ]

        lower_off_x = -px * disp
        lower_off_y = -py * disp
        lower_pts = [
            (lp1[0] + lower_off_x, lp1[1] + lower_off_y),
            (lp2[0] + lower_off_x, lp2[1] + lower_off_y),
            (lp2[0] + lower_off_x - px * far, lp2[1] + lower_off_y - py * far),
            (lp1[0] + lower_off_x - px * far, lp1[1] + lower_off_y - py * far),
        ]

        # Both halves use the same dark-space colour so they look like
        # physical screen pieces flying apart.
        panel_col = (C_DEEP_SPACE[0], C_DEEP_SPACE[1], C_DEEP_SPACE[2], panel_alpha)

        arcade.draw_polygon_filled(upper_pts, panel_col)
        arcade.draw_polygon_filled(lower_pts, panel_col)

        # Glowing cyan seam along each edge
        seam_alpha = int(alpha_mul * 220)
        if seam_alpha > 0:
            seam_col = (C_CYAN[0], C_CYAN[1], C_CYAN[2], seam_alpha)
            arcade.draw_line(
                lp1[0] + upper_off_x, lp1[1] + upper_off_y,
                lp2[0] + upper_off_x, lp2[1] + upper_off_y,
                seam_col, 2)
            arcade.draw_line(
                lp1[0] + lower_off_x, lp1[1] + lower_off_y,
                lp2[0] + lower_off_x, lp2[1] + lower_off_y,
                seam_col, 2)

    def draw(self):
        if not self._active and not self.done:
            return

        # ── Ship flight ───────────────────────────────
        flight_frac = min(1.0, self._t / self.FLIGHT_DURATION)
        # Ease-in-out for believable acceleration/deceleration
        flight_ease = self._ease_in_out(flight_frac)

        sx = self._ship_start[0] + (self._ship_end[0] - self._ship_start[0]) * flight_ease
        sy = self._ship_start[1] + (self._ship_end[1] - self._ship_start[1]) * flight_ease

        # Ship scale: slightly grows as it approaches, then shrinks into distance
        scale = 0.8 + 0.4 * math.sin(math.pi * flight_frac)

        # Only draw ship while it's still crossing the screen
        if flight_frac < 1.0:
            # Engine flare (drawn behind ship)
            self._engine_flare(sx, sy, scale)

            # Motion trail — faint ghost copies at prior positions
            trail_steps = 6
            for i in range(trail_steps, 0, -1):
                t_frac = max(0.0, flight_ease - i * 0.025)
                tx = self._ship_start[0] + (self._ship_end[0] - self._ship_start[0]) * t_frac
                ty = self._ship_start[1] + (self._ship_end[1] - self._ship_start[1]) * t_frac
                t_alpha = int(10 + 25 * ((trail_steps - i) / trail_steps))
                if self._ship_texture is not None:
                    # Use vector ghost so the engine flare (drawn separately)
                    # stays visible — the dark overlay approach killed the flame
                    ghost_pts = self._ship_polygon(tx, ty, scale * 0.9)
                    arcade.draw_polygon_filled(ghost_pts, (240, 248, 255, t_alpha))
                else:
                    ghost_pts = self._ship_polygon(tx, ty, scale * 0.9)
                    arcade.draw_polygon_filled(ghost_pts, (240, 248, 255, t_alpha))

            # ── Main ship — use space_ship.png if available ──
            if self._ship_texture is not None:
                ship_draw_w = self._ship_texture.width  * 0.13 * scale
                ship_draw_h = self._ship_texture.height * 0.13 * scale
                arcade.draw_texture_rectangle(
                    sx, sy, ship_draw_w, ship_draw_h,
                    self._ship_texture,
                    angle=-(self.ANGLE_DEG))
            else:
                # Fallback: vector polygon
                ship_pts = self._ship_polygon(sx, sy, scale)
                arcade.draw_polygon_filled(ship_pts, (245, 250, 255, 255))
                arcade.draw_polygon_outline(ship_pts,
                                            (C_CYAN[0], C_CYAN[1], C_CYAN[2], 200), 1)
                ck_x = sx + self._cos * 20 * scale
                ck_y = sy + self._sin * 20 * scale
                arcade.draw_circle_filled(ck_x, ck_y, 5 * scale, (200, 230, 255, 200))

        # ── Diagonal slice ────────────────────────────
        if self._slicing:
            self._draw_slice_halves()


# ══════════════════════════════════════════════════════════
# LOADING VIEW
# ══════════════════════════════════════════════════════════
class LoadingView(arcade.View):
    """
    Full cinematic loading screen.
    Phases:
      0 → 1.5 s  : V² Productions logo reveal (fade-in)
      1.5→ 3.0 s : Hold logo
      3.0→ 4.2 s : Logo fade to game title
      4.2→ end   : Loading bar + tips + game HUD chrome
    """

    LOADING_STEPS = [
        (0.08,  "Initialising quantum drive arrays..."),
        (0.18,  "Loading star charts..."),
        (0.27,  "Calibrating weapon systems..."),
        (0.38,  "Spawning enemy AI matrices..."),
        (0.49,  "Compiling A* pathfinding grids..."),
        (0.58,  "Deploying boss encounter data..."),
        (0.67,  "Charging particle accelerators..."),
        (0.76,  "Syncing achievement registry..."),
        (0.85,  "Rendering nebula fields..."),
        (0.93,  "Priming gesture recognition..."),
        (0.98,  "Final systems check..."),
        (1.00,  "SYSTEMS ONLINE — LAUNCHING"),
    ]

    TIPS = [
        "TIP  Use SHIFT to dodge-roll through enemy fire — grants i-frames.",
        "TIP  Piercing rounds pass through multiple targets. Aim for tight groups.",
        "TIP  Press G at any time to switch to Gesture Control mode.",
        "TIP  SHIELDED enemies must have their shield broken before taking HP damage.",
        "TIP  Combo multipliers boost score — keep killing to maintain the chain.",
        "TIP  Boss BEAM attack telegraphs its aim — dodge before it fires.",
        "TIP  Power-up drops are magnetised — you don't need to walk over them.",
        "TIP  Upgrade every 2 waves — prioritise fire rate or dash cooldown early.",
    ]

    def __init__(self, target_view=None, next_view_fn=None):
        super().__init__()
        self.target_view = target_view
        self.next_view_fn = next_view_fn  # callable → next view, or None for demo loop
        self.t = 0.0
        self.frame = 0
        self._step_idx = 0
        self._tip_idx  = random.randint(0, len(self.TIPS) - 1)
        self._tip_timer = 0.0
        self._launched = False

        # Sub-components
        self.stars   = LoadingStarField()
        self.nebula  = NebulaCloud()
        self.bar     = LoadingBar(SCREEN_WIDTH // 2, 108, 760, 16)
        self.ship    = ShipSilhouette(SCREEN_WIDTH // 2 + 430, 500)
        self.v2logo  = V2Logo(SCREEN_WIDTH // 2 - 80, SCREEN_HEIGHT // 2)

        # ── NEW: diagonal slice transition ────────────
        self.slice_transition = DiagonalSliceTransition(self.target_view)

        # Phase timing
        self._phase = "logo"          # logo | hold | transition | game
        self._logo_alpha  = 0.0
        self._title_alpha = 0.0
        self._hud_alpha   = 0.0

        # Decorative scan lines
        self._scan_y = SCREEN_HEIGHT
        self._scan_speed = 3.5

    # ── helpers ──────────────────────────────────────────
    @property
    def _logo_reveal(self) -> float:
        if self.t < 0.4:
            return 0.0
        return min(1.0, (self.t - 0.4) / 1.1)

    @property
    def _title_reveal(self) -> float:
        if self.t < 3.0:
            return 0.0
        return min(1.0, (self.t - 3.0) / 1.2)

    @property
    def _hud_reveal(self) -> float:
        if self.t < 4.2:
            return 0.0
        return min(1.0, (self.t - 4.2) / 1.0)

    def _advance_loading(self):
        if self._step_idx < len(self.LOADING_STEPS):
            prog, _ = self.LOADING_STEPS[self._step_idx]
            self.bar.set_target(prog)
            self._step_idx += 1

    def _current_status(self) -> str:
        if self._step_idx == 0:
            return "INITIALISING..."
        prog, msg = self.LOADING_STEPS[min(self._step_idx - 1,
                                           len(self.LOADING_STEPS) - 1)]
        return msg

    # ── update ───────────────────────────────────────────
    def on_update(self, delta_time: float):
        self.t     += delta_time
        self.frame += 1
        self._tip_timer += delta_time

        # Update target view in the background at all times
        if self.target_view and not self.slice_transition.active:
            self.target_view.on_update(delta_time)

        # Cycle tips
        if self._tip_timer > 5.0:
            self._tip_timer = 0.0
            self._tip_idx = (self._tip_idx + 1) % len(self.TIPS)

        # Phase transitions
        if self.t < 1.5:
            self._phase = "logo"
        elif self.t < 3.0:
            self._phase = "hold"
        elif self.t < 4.2:
            self._phase = "transition"
        else:
            self._phase = "game"

        # Logo / overlay alphas
        if self._phase == "logo":
            self._logo_alpha = min(1.0, (self.t - 0.2) / 0.8)
        elif self._phase == "hold":
            self._logo_alpha = 1.0
        elif self._phase == "transition":
            fade = (self.t - 3.0) / 1.2
            self._logo_alpha  = max(0.0, 1.0 - fade * 2)
            self._title_alpha = min(1.0, fade)
        else:
            self._logo_alpha  = 0.0
            self._title_alpha = 1.0

        self._hud_alpha = self._hud_reveal

        # Stars / nebula
        self.stars.update(self.t)

        # Ship (game phase)
        if self._phase in ("transition", "game"):
            self.ship.update(self.t)

        # Loading bar
        if self._phase == "game":
            self.bar.update()
            # Advance steps with delay
            if self.frame % 48 == 0:
                self._advance_loading()

        # Scan line
        self._scan_y -= self._scan_speed
        if self._scan_y < 0:
            self._scan_y = SCREEN_HEIGHT

        # ── NEW: trigger slice transition on load complete ──
        if (self._phase == "game" and
                self.bar.progress >= 1.0 and
                not self.slice_transition.active and
                not self.slice_transition.done):
            self.slice_transition.start()

        # Always update the transition (active or finishing) so timing is tight
        self.slice_transition.update(delta_time)

        # Launch the moment the ship exits the top-right (slice_transition.done)
        if (not self._launched and
                self._phase == "game" and
                self.bar.progress >= 1.0 and
                self.slice_transition.done):
            self._launched = True
            if self.next_view_fn:
                self.next_view_fn()

    # ── draw ─────────────────────────────────────────────
    def on_draw(self):
        self.window.clear()

        # ── Deep-space background ──────────────────────
        arcade.draw_rectangle_filled(
            SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
            SCREEN_WIDTH, SCREEN_HEIGHT, C_DEEP_SPACE)

        self.nebula.draw()
        self.stars.draw()

        # ── Scan line (subtle CRT effect) ──────────────
        arcade.draw_line(0, self._scan_y, SCREEN_WIDTH, self._scan_y,
                         (120, 180, 255, 14), 2)
        arcade.draw_line(0, self._scan_y + 2, SCREEN_WIDTH, self._scan_y + 2,
                         (80, 120, 200, 7), 1)

        # ── PHASE: LOGO ───────────────────────────────
        if self._phase in ("logo", "hold"):
            self._draw_logo_phase()

        # ── PHASE: TRANSITION ─────────────────────────
        elif self._phase == "transition":
            self._draw_logo_phase()
            self._draw_game_phase()

        # ── PHASE: GAME / LOADING ─────────────────────
        else:
            self._draw_game_phase()

        # ── NEW: diagonal slice transition (drawn last, on top of everything)
        self.slice_transition.draw()

        # ── Always: subtle vignette ────────────────────
        self._draw_vignette()

    def _draw_logo_phase(self):
        alpha = int(self._logo_alpha * 255)
        if alpha <= 0:
            return

        # Dark overlay for logo clarity
        overlay_a = min(210, int(self._logo_alpha * 210))
        arcade.draw_rectangle_filled(
            SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
            SCREEN_WIDTH, SCREEN_HEIGHT,
            (2, 4, 12, overlay_a))

        # V² logo
        self.v2logo.update(self.t, self._logo_reveal)
        self.v2logo.draw()

        # Tagline below logo
        if self._logo_reveal > 0.8:
            tag_a = int((self._logo_reveal - 0.8) * 5 * alpha)
            tag_a = min(255, tag_a)
            arcade.draw_text(
                "PRESENTS",
                SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100,
                (C_CHROME[0], C_CHROME[1], C_CHROME[2], tag_a),
                font_size=14, bold=True, anchor_x="center", font_name="Times New Roman")

    def _draw_game_phase(self):
        hud_a = self._hud_alpha

        # ── Game title block ───────────────────────────
        ty = SCREEN_HEIGHT - 120
        title_a = int(self._title_alpha * 255)

        if title_a > 0:
            # Subtle title plate
            draw_metal_panel(SCREEN_WIDTH // 2, ty, 860, 140,
                             alpha=min(180, int(self._title_alpha * 120)),
                             accent=True)

            # "ASTROVANGUARD" — huge chrome lettering
            shimmer_x = 6 * math.sin(self.t * 1.4)
            arcade.draw_text(
                "ASTROVANGUARD",
                SCREEN_WIDTH // 2 + shimmer_x, ty + 24,
                (C_CHROME[0], C_CHROME[1], C_CHROME[2], title_a),
                font_size=52, bold=True, anchor_x="center", font_name="Times New Roman")
            # Shadow pass
            arcade.draw_text(
                "ASTROVANGUARD",
                SCREEN_WIDTH // 2 + shimmer_x + 2, ty + 22,
                (C_GOLD_DARK[0], C_GOLD_DARK[1], C_GOLD_DARK[2], int(title_a * 0.35)),
                font_size=52, bold=True, anchor_x="center", font_name="Times New Roman")

            # Subtitle
            arcade.draw_text(
                "AI  TACTICAL  SPACE  SIEGE  —  ENHANCED  EDITION  v5.0",
                SCREEN_WIDTH // 2, ty - 28,
                (C_GOLD[0], C_GOLD[1], C_GOLD[2], title_a),
                font_size=13, bold=True, anchor_x="center", font_name="Times New Roman")

            # Gold separator lines
            lx1 = SCREEN_WIDTH // 2 - 360
            lx2 = SCREEN_WIDTH // 2 + 360
            arcade.draw_line(lx1, ty - 8, lx2, ty - 8,
                             (C_GOLD[0], C_GOLD[1], C_GOLD[2], int(title_a * 0.6)), 1)

        # ── Spinning ship ──────────────────────────────
        if self._title_alpha > 0.3:
            self.ship.draw()

        if hud_a <= 0:
            return

        ia = int(hud_a * 255)

        # ── Left panel — studio branding ──────────────
        draw_metal_panel(170, 480, 280, 200, alpha=int(hud_a * 100))

        arcade.draw_text("A", 170, 528,
                         (C_GOLD[0], C_GOLD[1], C_GOLD[2], ia),
                         font_size=42, bold=True, anchor_x="center", font_name="Times New Roman")
        arcade.draw_text("V² PRODUCTIONS", 170, 488,
                         (C_SILVER[0], C_SILVER[1], C_SILVER[2], ia),
                         font_size=11, bold=True, anchor_x="center", font_name="Times New Roman")
        arcade.draw_line(110, 482, 230, 482,
                         (C_GOLD[0], C_GOLD[1], C_GOLD[2], int(ia * 0.5)), 1)
        arcade.draw_text("PRESENTS", 170, 465,
                         (C_STEEL[0], C_STEEL[1], C_STEEL[2], ia),
                         font_size=9, bold=True, anchor_x="center", font_name="Times New Roman")

        # Small hex badges
        for i, bx in enumerate([120, 170, 220]):
            draw_hex_badge(bx, 400, 14, (6, 10, 28), int(ia * 0.8))

        # ── Right panel — game stats ───────────────────
        draw_metal_panel(1090, 460, 300, 260, alpha=int(hud_a * 100))

        stats = [
            ("ENEMIES",     "40+  UNIQUE"),
            ("WEAPONS",     "3  TYPES  ×  3  TIERS"),
            ("ACHIEVEMENTS","12  CHALLENGES"),
            ("AI SYSTEMS",  "A* + ALPHA-BETA"),
            ("CONTROL",     "KEYBOARD / GESTURE"),
        ]
        sy = 555
        for label, val in stats:
            arcade.draw_text(label, 960, sy,
                             (C_GOLD[0], C_GOLD[1], C_GOLD[2], ia),
                             font_size=9, bold=True, font_name="Times New Roman")
            arcade.draw_text(val, 1215, sy,
                             (C_CHROME[0], C_CHROME[1], C_CHROME[2], ia),
                             font_size=9, anchor_x="right", font_name="Times New Roman")
            arcade.draw_line(960, sy - 4, 1215, sy - 4,
                             (C_CYAN_DIM[0], C_CYAN_DIM[1], C_CYAN_DIM[2], int(ia * 0.25)), 1)
            sy -= 38

        # ── Center bottom: loading bar ─────────────────
        bar_y_center = 108
        # Background chrome panel
        draw_metal_panel(SCREEN_WIDTH // 2, bar_y_center + 42, 860, 110,
                         alpha=int(hud_a * 100))

        self.bar.draw()

        # Status text
        status = self._current_status()
        blink_a = int(ia * (0.5 + 0.5 * math.sin(self.t * 8))) if "ONLINE" in status else ia
        arcade.draw_text(
            status,
            SCREEN_WIDTH // 2, bar_y_center + 28,
            (C_CYAN[0], C_CYAN[1], C_CYAN[2], blink_a),
            font_size=11, bold=True, anchor_x="center", font_name="Times New Roman")

        # Progress percentage
        pct = int(self.bar.progress * 100)
        arcade.draw_text(
            f"{pct}%",
            SCREEN_WIDTH // 2 + 400, bar_y_center - 2,
            (C_GOLD_LIGHT[0], C_GOLD_LIGHT[1], C_GOLD_LIGHT[2], ia),
            font_size=13, bold=True, anchor_x="center", font_name="Times New Roman")

        # Tip
        tip_a = int(ia * min(1.0, self._tip_timer / 0.6)
                    * min(1.0, (5.0 - self._tip_timer) / 0.5))
        arcade.draw_text(
            self.TIPS[self._tip_idx],
            SCREEN_WIDTH // 2, bar_y_center + 70,
            (C_STEEL[0], C_STEEL[1], C_STEEL[2], max(0, tip_a)),
            font_size=11, anchor_x="center", italic=True, font_name="Times New Roman")

        # ── Copyright footer ───────────────────────────
        arcade.draw_text(
            "© 2025  V² PRODUCTIONS  ·  ALL RIGHTS RESERVED  ·  "
            "ASTROVANGUARD v5.0",
            SCREEN_WIDTH // 2, 18,
            (C_STEEL[0], C_STEEL[1], C_STEEL[2], int(ia * 0.7)),
            font_size=9, anchor_x="center", font_name="Times New Roman")

        # ── Decorative horizontal rule top of bar area ──
        arcade.draw_line(80, 155, SCREEN_WIDTH - 80, 155,
                         (C_GOLD[0], C_GOLD[1], C_GOLD[2], int(ia * 0.4)), 1)

        # ── Blinking ENTER prompt once loaded ──────────
        if self.bar.progress >= 1.0 and not self.slice_transition.active:
            pulse = int(180 + 75 * math.sin(self.t * 6))
            arcade.draw_text(
                "PRESS  ENTER  TO  LAUNCH",
                SCREEN_WIDTH // 2, bar_y_center - 20,
                (C_GOLD_LIGHT[0], C_GOLD_LIGHT[1], C_GOLD_LIGHT[2], pulse),
                font_size=14, bold=True, anchor_x="center", font_name="Times New Roman")

    def _draw_vignette(self):
        """Darken screen edges for cinematic depth."""
        pass

    # ── Input ─────────────────────────────────────────────
    def on_key_press(self, symbol, modifiers):
        if symbol == arcade.key.ENTER and self.bar.progress >= 1.0:
            if self.next_view_fn:
                self.next_view_fn()
        elif symbol == arcade.key.ESCAPE:
            arcade.close_window()
        # Dev shortcut: skip loading
        elif symbol == arcade.key.F12:
            self.bar.set_target(1.0)
            self.bar.progress = 1.0


# ══════════════════════════════════════════════════════════
# STANDALONE DEMO  (loop loading screen → restart)
# ══════════════════════════════════════════════════════════
def _restart(window):
    view = LoadingView(next_view_fn=lambda: _restart(window))
    window.show_view(view)


def main():
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE,
                           resizable=False)
    window.background_color = arcade.color.BLACK

    def on_done():
        # In production: window.show_view(MenuView(settings))
        # Here we just loop the loading screen as a demo
        _restart(window)

    view = LoadingView(next_view_fn=on_done)
    window.show_view(view)
    arcade.run()


if __name__ == "__main__":
    main()