# algorithms/complex_environments/belief_search.py
"""
Belief-State Search:
- Tập belief_goals = {dấu ? trên map} + {GOAL thật}
- Agent không biết đâu là goal thật
- BFS duyệt từng state cho tới khi chạm goal thật
- Khi chạm ngôi sao → máy dò ngẫu nhiên 1 belief state:
    + Nếu không phải goal thật → xóa khỏi belief set, replan
    + Nếu là goal thật → chốt goal, đi thẳng tới đó
"""

import random  # ← PHẢI đặt đầu file

from algorithms.uninformed.bfs import bfs

MOVES = {
    "U": (-1,  0),
    "D": ( 1,  0),
    "L": ( 0, -1),
    "R": ( 0,  1),
}


# ======================================================================
#  Helpers
# ======================================================================

def _build_simple_graph(rows, cols, blocked):
    """Grid graph đơn giản (pos → [pos])."""
    graph = {}
    for r in range(rows):
        for c in range(cols):
            if (r, c) in blocked:
                continue
            neighbors = []
            for dr, dc in MOVES.values():
                nr, nc = r + dr, c + dc
                if (0 <= nr < rows and 0 <= nc < cols
                        and (nr, nc) not in blocked):
                    neighbors.append((nr, nc))
            graph[(r, c)] = neighbors
    return graph


def _bfs_simple(rows, cols, blocked, start, goal):
    if start == goal:
        return [], [start]

    graph = _build_simple_graph(rows, cols, blocked)
    if start not in graph or goal not in graph:
        return [], []

    # ════════════════════════════════════════════════
    # DEBUG: Xem bfs() trả về gì
    # ════════════════════════════════════════════════
    result = bfs(graph, start, goal)
    print(f"[DEBUG] bfs() returned: {type(result)}")
    print(f"[DEBUG] content: {result if not isinstance(result, list) or len(result) < 10 else result[:10]}")
    
    # Xử lý theo kiểu
    if isinstance(result, tuple):
        path_mid = result[0]
    else:
        path_mid = result
    
    if path_mid is None or not path_mid:
        return [], []

    full = _make_full_path(start, goal, path_mid)
    return _path_to_actions(full)


def _make_full_path(start, goal, path_mid):
    """
    Ghép path an toàn: tránh duplicate start/goal.
    bfs() của dự án này trả về các node trung gian
    (không gồm start, không gồm goal).
    """
    full = [start]
    for node in path_mid:
        if node != start and node != goal:
            full.append(node)
    if goal not in full:
        full.append(goal)
    return full


def _path_to_actions(full):
    """Chuyển chuỗi vị trí → (actions, pos_sequence)."""
    actions, pos_seq = [], [full[0]]
    for i in range(len(full) - 1):
        dr = full[i + 1][0] - full[i][0]
        dc = full[i + 1][1] - full[i][1]
        for a, (d_r, d_c) in MOVES.items():
            if (d_r, d_c) == (dr, dc):
                actions.append(a)
                break
        pos_seq.append(full[i + 1])
    return actions, pos_seq


def _nearest_belief(rows, cols, blocked, start, belief_goals):
    """
    Tìm belief goal gần nhất với start (BFS).
    Dùng để chọn đích tiếp theo khi replan từng bước.
    """
    graph = _build_simple_graph(rows, cols, blocked)
    if start not in graph:
        return None

    # BFS từ start, dừng khi chạm belief_goal đầu tiên
    from collections import deque
    visited = {start}
    queue   = deque([start])
    while queue:
        pos = queue.popleft()
        if pos in belief_goals:
            return pos
        for npos in graph.get(pos, []):
            if npos not in visited:
                visited.add(npos)
                queue.append(npos)
    return None


def _plan_visit_all(rows, cols, blocked, start, belief_goals):
    """
    Lập kế hoạch thăm tất cả belief goals theo thứ tự gần nhất (greedy).
    Trả về (actions, pos_sequence).
    Đây là heuristic: thăm nearest unvisited → nearest → ...
    """
    all_actions  = []
    all_pos      = [start]
    current      = start
    remaining    = set(belief_goals)

    while remaining:
        target = _nearest_belief(rows, cols, blocked, current, remaining)
        if target is None:
            break  # không đến được

        acts, pos_seq = _bfs_simple(rows, cols, blocked, current, target)
        if not acts and current != target:
            # Không tìm được đường → bỏ qua belief này
            remaining.discard(target)
            continue

        all_actions.extend(acts)
        # pos_seq[0] == current (đã có), bỏ qua
        all_pos.extend(pos_seq[1:])
        current = target
        remaining.discard(target)

    return all_actions, all_pos


# ======================================================================
#  Agent
# ======================================================================

class BeliefSearchAgent:

    def __init__(self):
        self.path:           list  = []
        self.path_index:     int   = 0
        self.pos_sequence:   list  = []

        self.belief_goals:   set   = set()
        self.true_goal:      tuple = None
        self.confirmed_goal: tuple = None
        self.eliminated:     set   = set()

        self.solved:         bool  = False
        self.failed:         bool  = False
        self.goal_confirmed: bool  = False

        # ── FLAG MỚI: báo path đã thay đổi để stage4 rebuild đường vẽ ──
        self.path_changed:   bool  = False

        self.expansions:     int   = 0
        self.exec_time:      str   = "0.00 ms"
        self.detector_log:   list  = []

        self._rows    = 0
        self._cols    = 0
        self._blocked = set()

    # ------------------------------------------------------------------
    def reset(self):
        self.path           = []
        self.path_index     = 0
        self.pos_sequence   = []
        self.belief_goals   = set()
        self.true_goal      = None
        self.confirmed_goal = None
        self.eliminated     = set()
        self.solved         = False
        self.failed         = False
        self.goal_confirmed = False
        self.path_changed   = False  # ← THÊM
        self.expansions     = 0
        self.exec_time      = "0.00 ms"
        self.detector_log   = []
        self._rows          = 0
        self._cols          = 0
        self._blocked       = set()

    # ------------------------------------------------------------------
    def plan(self, rows, cols, start, belief_goals, blocked, true_goal):
        """
        Lập kế hoạch ban đầu.
        belief_goals = tập ô ? + goal thật.
        true_goal    = goal thật (ẩn với agent, chỉ dùng khi máy dò kích hoạt).
        """
        self.reset()
        self.belief_goals = set(belief_goals)
        self.true_goal    = true_goal
        self._rows        = rows
        self._cols        = cols
        self._blocked     = set(blocked)

        if not belief_goals:
            self.solved       = True
            self.pos_sequence = [start]
            return True

        return self._replan(start)

    # ------------------------------------------------------------------
    def _replan(self, start):
        """Xây lại kế hoạch từ vị trí hiện tại."""
        rows, cols, blocked = self._rows, self._cols, self._blocked

        # Đã biết goal thật → đi thẳng
        if self.goal_confirmed and self.confirmed_goal:
            actions, pos_seq = _bfs_simple(
                rows, cols, blocked, start, self.confirmed_goal)
            if not actions and start != self.confirmed_goal:
                self.failed = True
                return False
            self.path         = actions
            self.path_index   = 0
            self.pos_sequence = pos_seq
            self.path_changed = True  # ← THÊM
            return True

        # Chưa biết goal → thăm tất cả belief goals còn lại (greedy nearest)
        active = self.belief_goals - self.eliminated
        if not active:
            self.failed = True
            return False

        actions, pos_seq = _plan_visit_all(rows, cols, blocked, start, active)

        # Không tìm được bước nào mà start chưa phải goal
        if not actions and start not in active:
            self.failed = True
            return False

        self.path         = actions
        self.path_index   = 0
        self.pos_sequence = pos_seq
        self.expansions  += len(pos_seq)
        self.path_changed = True  # ← THÊM
        return True

    # ------------------------------------------------------------------
    def trigger_detector(self, current_pos):
        """
        Máy dò kích hoạt khi agent chạm ngôi sao.
        Chọn ngẫu nhiên 1 belief state còn lại:
          - Là true_goal  → xác nhận, replan đi thẳng
          - Không phải    → loại, replan
        """
        remaining = self.belief_goals - self.eliminated
        if not remaining or self.goal_confirmed:
            return None

        candidate = random.choice(list(remaining))
        result = {
            "candidate":  candidate,
            "is_goal":    False,
            "eliminated": None,
            "confirmed":  None,
            "msg":        "",
        }

        if candidate == self.true_goal:
            # Xác nhận goal thật
            self.confirmed_goal = candidate
            self.goal_confirmed = True
            result["is_goal"]   = True
            result["confirmed"] = candidate
            result["msg"]       = f"🎯 Goal confirmed: {candidate}!"
            self.detector_log.append(result.copy())

            ok = self._replan(current_pos)
            if not ok:
                result["msg"] += " (path blocked!)"
        else:
            # Loại belief này
            self.eliminated.add(candidate)
            result["eliminated"] = candidate
            result["msg"]        = f"❌ {candidate} NOT goal, eliminated."
            self.detector_log.append(result.copy())

            new_active = self.belief_goals - self.eliminated
            if not new_active:
                # Đã loại hết → chỉ còn true_goal
                self.confirmed_goal = self.true_goal
                self.goal_confirmed = True
                result["confirmed"] = self.true_goal
                result["msg"]      += f" | Only true_goal left: {self.true_goal}"
                new_active          = {self.true_goal}

            ok = self._replan(current_pos)
            if not ok:
                self.failed   = True
                result["msg"] += " | Replan failed!"

        return result

    # ------------------------------------------------------------------
    def has_next(self):
        return (not self.solved
                and not self.failed
                and self.path_index < len(self.path))

    def next_action(self):
        if not self.has_next():
            return None
        a = self.path[self.path_index]
        self.path_index += 1
        return a

    def notify_position(self, pos):
        """Gọi sau mỗi bước di chuyển để kiểm tra win condition."""
        if self.true_goal is None:
            return
        if pos == self.true_goal:
            self.confirmed_goal = self.true_goal
            self.goal_confirmed = True
            self.solved         = True

    # ------------------------------------------------------------------
    @property
    def active_belief(self):
        return self.belief_goals - self.eliminated

    @property
    def progress(self):
        if self.goal_confirmed:
            return f"Goal confirmed: {self.confirmed_goal}"
        elim  = len(self.eliminated)
        total = len(self.belief_goals)
        return f"Eliminated: {elim}/{total} candidates"