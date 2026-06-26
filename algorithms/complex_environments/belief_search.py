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

from algorithms.uninformed.bfs import bfs

MOVES = {
    "U": (-1,  0),
    "D": ( 1,  0),
    "L": ( 0, -1),
    "R": ( 0,  1),
}


# ======================================================================
#  Build belief graph
# ======================================================================

def _build_belief_graph(rows, cols, blocked, start, belief_goals):
    """
    Node = (pos, frozenset_remaining_goals)
    Graph dict kề đúng format bfs() có sẵn.
    """
    init_node = (start, frozenset(belief_goals) - {start})
    graph     = {}
    queue     = [init_node]
    visited   = {init_node}

    while queue:
        node = queue.pop(0)
        pos, remaining = node
        neighbors = []

        for action, (dr, dc) in MOVES.items():
            nr, nc = pos[0] + dr, pos[1] + dc
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue
            if (nr, nc) in blocked:
                continue
            new_pos       = (nr, nc)
            new_remaining = remaining - {new_pos}
            new_node      = (new_pos, new_remaining)
            neighbors.append(new_node)
            if new_node not in visited:
                visited.add(new_node)
                queue.append(new_node)

        graph[node] = neighbors

    return graph, init_node


def _find_goal_node(graph):
    """Goal = node có remaining == frozenset() (đã thăm hết)."""
    for node in graph:
        _, remaining = node
        if len(remaining) == 0:
            return node
    return None


def _reconstruct_actions(full_node_sequence):
    """Từ chuỗi nodes → list actions + pos_sequence."""
    actions, pos_sequence = [], []
    for i, node in enumerate(full_node_sequence):
        pos, _ = node
        pos_sequence.append(pos)
        if i < len(full_node_sequence) - 1:
            pos_next, _ = full_node_sequence[i + 1]
            dr, dc = pos_next[0] - pos[0], pos_next[1] - pos[1]
            for a, (d_r, d_c) in MOVES.items():
                if (d_r, d_c) == (dr, dc):
                    actions.append(a)
                    break
    return actions, pos_sequence


def _bfs_path_to_goal(rows, cols, blocked, start, goal):
    """
    BFS đơn giản từ start đến 1 goal cụ thể.
    Dùng khi đã xác định được goal thật.
    """
    # Build graph grid đơn giản
    graph = {}
    for r in range(rows):
        for c in range(cols):
            if (r, c) in blocked:
                continue
            neighbors = []
            for dr, dc in MOVES.values():
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in blocked:
                    neighbors.append((nr, nc))
            graph[(r, c)] = neighbors

    if start not in graph or goal not in graph:
        return [], []

    path_mid, _, _, _ = bfs(graph, start, goal)
    full = [start] + path_mid + [goal]

    actions, pos_seq = [], [start]
    for i in range(len(full) - 1):
        dr = full[i+1][0] - full[i][0]
        dc = full[i+1][1] - full[i][1]
        for a, (d_r, d_c) in MOVES.items():
            if (d_r, d_c) == (dr, dc):
                actions.append(a)
                break
        pos_seq.append(full[i+1])

    return actions, pos_seq


# ======================================================================
#  Agent
# ======================================================================

class BeliefSearchAgent:

    def __init__(self):
        # Kế hoạch hiện tại
        self.path:              list = []
        self.path_index:        int  = 0
        self.pos_sequence:      list = []

        # Belief state
        self.belief_goals:      set  = set()   # tập ô ? + goal thật (ban đầu)
        self.true_goal:         tuple = None   # goal thật (ẩn với agent)
        self.confirmed_goal:    tuple = None   # goal đã được xác nhận bởi máy dò
        self.eliminated:        set  = set()   # belief states đã loại

        # Trạng thái
        self.solved:            bool = False
        self.failed:            bool = False
        self.goal_confirmed:    bool = False   # đã biết goal thật chưa

        # Thống kê
        self.expansions:        int  = 0
        self.exec_time:         str  = "0.00 ms"
        self.detector_log:      list = []      # lịch sử máy dò

    # ------------------------------------------------------------------
    def reset(self):
        self.path             = []
        self.path_index       = 0
        self.pos_sequence     = []
        self.belief_goals     = set()
        self.true_goal        = None
        self.confirmed_goal   = None
        self.eliminated       = set()
        self.solved           = False
        self.failed           = False
        self.goal_confirmed   = False
        self.expansions       = 0
        self.exec_time        = "0.00 ms"
        self.detector_log     = []

    # ------------------------------------------------------------------
    def plan(self, rows, cols, start, belief_goals, blocked, true_goal):
        """
        Lập kế hoạch ban đầu:
          - belief_goals = tập dấu ? + goal thật
          - true_goal    = goal thật (ẩn, chỉ dùng để kiểm tra khi máy dò kích hoạt)
          - Dùng BFS trên belief space để thăm tất cả các ô trong belief_goals
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

        return self._replan(rows, cols, start, self.belief_goals, blocked)

    # ------------------------------------------------------------------
    def _replan(self, rows, cols, start, current_belief, blocked):
        """
        Build lại kế hoạch BFS với belief hiện tại.
        """
        if not current_belief:
            # Không còn belief nào → thất bại (không xác định được goal)
            self.failed = True
            return False

        # Nếu đã biết goal thật → đi thẳng tới đó
        if self.goal_confirmed and self.confirmed_goal:
            actions, pos_seq = _bfs_path_to_goal(
                rows, cols, blocked, start, self.confirmed_goal
            )
            if not actions and start != self.confirmed_goal:
                self.failed = True
                return False
            self.path         = actions
            self.path_index   = 0
            self.pos_sequence = pos_seq
            return True

        # BFS trên belief space
        graph, init_node = _build_belief_graph(rows, cols, blocked, start, current_belief)
        goal_node        = _find_goal_node(graph)

        if goal_node is None:
            self.failed = True
            return False

        path_mid, _, nodes_expanded, exec_time = bfs(graph, init_node, goal_node)
        self.expansions += nodes_expanded
        self.exec_time   = exec_time

        if not path_mid and init_node != goal_node:
            self.failed = True
            return False

        full_sequence     = [init_node] + path_mid + [goal_node]
        actions, pos_seq  = _reconstruct_actions(full_sequence)
        self.path         = actions
        self.path_index   = 0
        self.pos_sequence = pos_seq
        return True

    # ------------------------------------------------------------------
    def trigger_detector(self, current_pos):
        """
        Máy dò kích hoạt khi agent chạm ngôi sao.
        Chọn ngẫu nhiên 1 belief state còn lại:
          - Nếu là true_goal  → xác nhận goal, replan đi thẳng
          - Nếu không phải    → loại khỏi belief, replan
        
        Returns: dict với thông tin kết quả
        """
        remaining = self.belief_goals - self.eliminated
        if not remaining or self.goal_confirmed:
            return None

        # Chọn ngẫu nhiên 1 belief state để dò
        candidate = random.choice(list(remaining))

        result = {
            "candidate": candidate,
            "is_goal":   False,
            "msg":       "",
        }

        if candidate == self.true_goal:
            # Xác nhận goal thật!
            self.confirmed_goal  = candidate
            self.goal_confirmed  = True
            result["is_goal"]    = True
            result["msg"]        = f"🎯 Goal confirmed at {candidate}!"
            self.detector_log.append(result.copy())

            # Replan đi thẳng tới goal
            ok = self._replan(
                self._rows, self._cols, current_pos,
                {candidate}, self._blocked
            )
            if not ok:
                result["msg"] += " (but path blocked!)"
        else:
            # Loại khỏi belief
            self.eliminated.add(candidate)
            result["is_goal"] = False
            result["msg"]     = f"❌ {candidate} is NOT goal, eliminated."
            self.detector_log.append(result.copy())

            # Replan với belief còn lại
            new_belief = self.belief_goals - self.eliminated
            if not new_belief:
                # Hết belief state mà chưa tìm ra goal → chỉ còn true_goal
                self.confirmed_goal = self.true_goal
                self.goal_confirmed = True
                new_belief          = {self.true_goal}
                result["msg"]      += f" | Only true goal left: {self.true_goal}"

            ok = self._replan(
                self._rows, self._cols, current_pos,
                new_belief, self._blocked
            )
            if not ok:
                self.failed   = True
                result["msg"] += " | Replan failed!"

        return result

    # ------------------------------------------------------------------
    def has_next(self):
        return self.path_index < len(self.path) and not self.solved

    def next_action(self):
        if not self.has_next():
            return None
        a = self.path[self.path_index]
        self.path_index += 1
        return a

    def notify_position(self, pos):
        """
        Gọi sau mỗi bước di chuyển.
        Nếu đã biết goal thật và đến đó → solved.
        """
        if self.goal_confirmed and pos == self.confirmed_goal:
            self.solved = True
        elif not self.goal_confirmed and pos == self.true_goal:
            # Đến goal thật dù chưa dò → cũng thắng
            self.confirmed_goal = self.true_goal
            self.goal_confirmed = True
            self.solved         = True

    # ------------------------------------------------------------------
    @property
    def active_belief(self):
        """Tập belief còn lại (chưa bị loại)."""
        return self.belief_goals - self.eliminated

    @property
    def progress(self):
        if self.goal_confirmed:
            return f"Goal confirmed: {self.confirmed_goal}"
        elim = len(self.eliminated)
        total = len(self.belief_goals)
        return f"Eliminated: {elim}/{total} candidates"


import random  # để dùng trong trigger_detector