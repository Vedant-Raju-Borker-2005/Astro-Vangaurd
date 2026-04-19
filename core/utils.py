import math
import random
import heapq
from typing import List, Tuple, Optional
from dataclasses import dataclass
from core.constants import GRID_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT

# ═══════════════════════════════════════════════════
# ALPHA-BETA PRUNING AI
# ═══════════════════════════════════════════════════

def minimax(depth: int, is_maximizing: bool, distance: float,
            alpha: float, beta: float) -> float:
    if depth == 0:
        return -distance
    if is_maximizing:
        value = -math.inf
        for _ in range(2):
            value = max(value, minimax(depth - 1, False, distance - 20, alpha, beta))
            alpha = max(alpha, value)
            if beta <= alpha:
                break
        return value
    else:
        value = math.inf
        for _ in range(2):
            value = min(value, minimax(depth - 1, True, distance + 20, alpha, beta))
            beta = min(beta, value)
            if beta <= alpha:
                break
        return value

# ═══════════════════════════════════════════════════
# A* PATHFINDING
# ═══════════════════════════════════════════════════

@dataclass
class Node:
    position: Tuple[int, int]
    parent: Optional['Node'] = None
    g: float = 0
    h: float = 0
    f: float = 0
    def __lt__(self, other: 'Node') -> bool:
        return self.f < other.f

def astar(start: Tuple[int, int], end: Tuple[int, int],
          max_iterations: int = 120) -> List[Tuple[int, int]]:
    open_list: List[Node] = []
    closed_set = set()
    heapq.heappush(open_list, Node(position=start))
    iterations = 0
    while open_list and iterations < max_iterations:
        iterations += 1
        current = heapq.heappop(open_list)
        closed_set.add(current.position)
        if current.position == end:
            path = []
            while current:
                path.append(current.position)
                current = current.parent
            return path[::-1]
        x, y = current.position
        for nx, ny in [
            (x + GRID_SIZE, y), (x - GRID_SIZE, y),
            (x, y + GRID_SIZE), (x, y - GRID_SIZE),
            (x + GRID_SIZE, y + GRID_SIZE), (x - GRID_SIZE, y - GRID_SIZE),
            (x + GRID_SIZE, y - GRID_SIZE), (x - GRID_SIZE, y + GRID_SIZE),
        ]:
            if not (0 <= nx <= SCREEN_WIDTH and 0 <= ny <= SCREEN_HEIGHT):
                continue
            if (nx, ny) in closed_set:
                continue
            n = Node(position=(nx, ny), parent=current)
            n.g = current.g + math.hypot(nx - x, ny - y)
            n.h = math.hypot(end[0] - nx, end[1] - ny)
            n.f = n.g + n.h
            heapq.heappush(open_list, n)
    return []

# ═══════════════════════════════════════════════════
# FORMATION SPAWNER
# ═══════════════════════════════════════════════════

class FormationSpawner:
    """Generates coordinated enemy spawn positions."""

    @staticmethod
    def v_wing(count: int) -> List[Tuple[float, float]]:
        positions = []
        cx = SCREEN_WIDTH / 2
        for i in range(count):
            side = 1 if i % 2 == 0 else -1
            idx  = (i // 2) + 1
            positions.append((cx + side * idx * 80, SCREEN_HEIGHT + 40 + idx * 40))
        return positions[:count]

    @staticmethod
    def column(count: int) -> List[Tuple[float, float]]:
        cx = random.randint(150, SCREEN_WIDTH - 150)
        return [(cx, SCREEN_HEIGHT + 40 + i * 60) for i in range(count)]

    @staticmethod
    def pincer(count: int) -> List[Tuple[float, float]]:
        left  = [(100 + i * 30, SCREEN_HEIGHT + 40 + i * 50) for i in range(count // 2)]
        right = [(SCREEN_WIDTH - 100 - i * 30, SCREEN_HEIGHT + 40 + i * 50)
                 for i in range(count - count // 2)]
        return left + right

    @staticmethod
    def diamond(count: int) -> List[Tuple[float, float]]:
        positions = []
        cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT + 100
        for i in range(count):
            a = (i / count) * math.pi * 2
            positions.append((cx + math.cos(a) * 140, cy + math.sin(a) * 60))
        return positions

    @classmethod
    def get_formation(cls, name: str, count: int) -> List[Tuple[float, float]]:
        return {
            "v_wing":  cls.v_wing,
            "column":  cls.column,
            "pincer":  cls.pincer,
            "diamond": cls.diamond,
        }.get(name, cls.v_wing)(count)

# ═══════════════════════════════════════════════════
# CAMERA
# ═══════════════════════════════════════════════════

class Camera:
    def __init__(self):
        self.shake_amount   = 0.0
        self.shake_duration = 0
        self._offset_x = self._offset_y = 0.0

    def shake(self, amount=10.0, duration=10):
        self.shake_amount   = max(self.shake_amount, amount)
        self.shake_duration = max(self.shake_duration, duration)

    def update(self):
        if self.shake_duration > 0:
            self.shake_duration -= 1
            decay = self.shake_duration / 10
            self._offset_x = random.uniform(-self.shake_amount, self.shake_amount) * min(1, decay + 0.3)
            self._offset_y = random.uniform(-self.shake_amount, self.shake_amount) * min(1, decay + 0.3)
            if self.shake_duration == 0:
                self.shake_amount = 0
                self._offset_x = self._offset_y = 0.0
        else:
            self._offset_x = self._offset_y = 0.0

    def get_offset(self) -> Tuple[float, float]:
        return self._offset_x, self._offset_y
