# algorithms/complex_environments/online_search.py
from __future__ import annotations

from dataclasses import dataclass
from heapq import heappush, heappop
from typing import Dict, Iterable, List, Optional, Tuple

Pos = Tuple[int, int]          # (r, c)
Action = Tuple[int, int]       # (dr, dc)

UNKNOWN = 0
FREE = 1
BLOCKED = 2


def manhattan(a: Pos, b: Pos) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


@dataclass
class Node:
    f: float
    g: float
    pos: Pos
    parent: Optional[Pos]


class OnlineReplanningAStar:
    """
    Online search (replanning A*):
    - Agent chỉ "biết" các ô đã quan sát.
    - Mỗi step: observe(3x3) -> cập nhật known map -> chạy A* trên known map
      (coi UNKNOWN là đi được nhưng cost cao hơn) -> đi 1 bước.

    Dùng tốt cho môi trường "online/partial observability" như fog-of-war.
    """

    def __init__(
        self,
        rows: int,
        cols: int,
        start: Pos,
        goal: Optional[Pos],
        unknown_cost: float = 1.25,
    ):
        self.rows = rows
        self.cols = cols
        self.unknown_cost = unknown_cost

        self.known = [[UNKNOWN for _ in range(cols)] for _ in range(rows)]
        self.pos = start
        self.goal = goal

        self.known[start[0]][start[1]] = FREE

        self._cached_path: List[Pos] = []  # includes current pos

    def reset(self, start: Pos, goal: Optional[Pos]):
        self.known = [[UNKNOWN for _ in range(self.cols)] for _ in range(self.rows)]
        self.pos = start
        self.goal = goal
        self.known[start[0]][start[1]] = FREE
        self._cached_path = []

    def set_goal(self, goal: Optional[Pos]):
        self.goal = goal
        self._cached_path = []

    def set_position(self, pos: Pos):
        self.pos = pos

    def observe(self, observations: Dict[Pos, bool]):
        """
        observations: dict[(r,c)] = blocked(True/False)
        """
        for (r, c), blocked in observations.items():
            if 0 <= r < self.rows and 0 <= c < self.cols:
                self.known[r][c] = BLOCKED if blocked else FREE
        # nếu path cũ đi qua ô vừa phát hiện BLOCKED => xoá cache
        if self._cached_path:
            for p in self._cached_path:
                if self.known[p[0]][p[1]] == BLOCKED:
                    self._cached_path = []
                    break

    def known_blocked_cells(self) -> Iterable[Pos]:
        for r in range(self.rows):
            for c in range(self.cols):
                if self.known[r][c] == BLOCKED:
                    yield (r, c)

    def next_action(self, current_pos: Pos) -> Action:
        """
        Trả về (dr,dc). Nếu không có goal hoặc đang ở goal -> (0,0).
        """
        self.pos = current_pos
        if self.goal is None:
            return (0, 0)
        if self.pos == self.goal:
            return (0, 0)

        # Ensure we have a path
        if not self._cached_path or self._cached_path[0] != self.pos:
            self._cached_path = self._plan_astar(self.pos, self.goal)

        # If still no path, đứng yên (có thể thay bằng random explore nếu muốn)
        if not self._cached_path or len(self._cached_path) < 2:
            return (0, 0)

        nxt = self._cached_path[1]
        dr = nxt[0] - self.pos[0]
        dc = nxt[1] - self.pos[1]

        # nếu bước tiếp theo vừa bị biết là BLOCKED, xoá cache và đứng yên (frame sau sẽ replan)
        if self.known[nxt[0]][nxt[1]] == BLOCKED:
            self._cached_path = []
            return (0, 0)

        # shift cached path forward
        self._cached_path = self._cached_path[1:]
        return (dr, dc)

    def _neighbors(self, p: Pos) -> Iterable[Pos]:
        r, c = p
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                if self.known[nr][nc] != BLOCKED:
                    yield (nr, nc)

    def _step_cost(self, p: Pos) -> float:
        """
        Cost bước vào ô p:
        - FREE: 1
        - UNKNOWN: unknown_cost (>1) để ưu tiên đường đã biết
        """
        st = self.known[p[0]][p[1]]
        if st == FREE:
            return 1.0
        if st == UNKNOWN:
            return float(self.unknown_cost)
        return 10_000.0  # BLOCKED shouldn't be expanded anyway

    def _plan_astar(self, start: Pos, goal: Pos) -> List[Pos]:
        open_heap: List[Tuple[float, int, Pos]] = []
        g_cost: Dict[Pos, float] = {start: 0.0}
        parent: Dict[Pos, Optional[Pos]] = {start: None}

        # tie-breaker counter
        counter = 0
        heappush(open_heap, (manhattan(start, goal), counter, start))

        closed = set()

        while open_heap:
            _, _, cur = heappop(open_heap)
            if cur in closed:
                continue
            closed.add(cur)

            if cur == goal:
                return self._reconstruct(parent, goal)

            for nb in self._neighbors(cur):
                if nb in closed:
                    continue

                ng = g_cost[cur] + self._step_cost(nb)
                if nb not in g_cost or ng < g_cost[nb]:
                    g_cost[nb] = ng
                    parent[nb] = cur
                    counter += 1
                    f = ng + manhattan(nb, goal)
                    heappush(open_heap, (f, counter, nb))

        return []

    def _reconstruct(self, parent: Dict[Pos, Optional[Pos]], end: Pos) -> List[Pos]:
        path = []
        cur: Optional[Pos] = end
        while cur is not None:
            path.append(cur)
            cur = parent.get(cur)
        path.reverse()
        return path