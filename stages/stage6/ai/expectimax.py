"""
EXPECTIMAX
----------
- Khác với Minimax: đối thủ KHÔNG được giả định chơi tối ưu.
- Thay vào đó, các action có yếu tố ngẫu nhiên (hit/miss) được
  xử lý qua CHANCE NODE với Expected Value.

Cấu trúc cây:
    MAX node  : lượt AI → chọn action có score cao nhất
    MIN node  : lượt địch → chọn action có score thấp nhất
    CHANCE node: khi có hit/miss → tính Expected Value

Công thức Chance Node:
    E[score] = acc × score(hit) + (1 - acc) × score(miss)

Trong đó:
    acc      = accuracy của skill (0.0 → 1.0)
    hit      : simulate với force=True  (đòn trúng)
    miss     : simulate với force=False (đòn trượt)

- Ưu điểm: xử lý tốt yếu tố ngẫu nhiên (phù hợp với skill Ultim acc=75%).
- Nhược điểm: chậm hơn AlphaBeta vì phải tính 2 nhánh cho mỗi action.
"""

from game.evaluate import evaluate
from game.do_act import do_act


class Expectimax:

    @staticmethod
    def run(gs, depth=2):
        """Entry point: trả về action tốt nhất."""
        is_p1 = (gs.turn % 2 == 0)
        _, action = Expectimax._ex(gs, depth, is_maximizing=True, is_p1=is_p1)
        return action

    @staticmethod
    def _ex(st, depth, is_maximizing, is_p1):
        """
        Đệ quy Expectimax.

        MAX node  → AI chọn action tốt nhất
        MIN node  → Địch chọn action tốt nhất cho nó
        CHANCE    → Được xử lý bên trong _chance()

        Trả về:
            (score, best_action)
        """
        if depth == 0 or st.over():
            return evaluate(st, is_p1), None

        acts = st.actions()
        if not acts:
            return evaluate(st, is_p1), None

        best_action = acts[0]
        best_score  = float('-inf') if is_maximizing else float('inf')

        for a in acts:
            # Mỗi action đi qua Chance Node để tính Expected Value
            score = Expectimax._chance(st, a, depth, not is_maximizing, is_p1)

            if is_maximizing:
                if score > best_score:
                    best_score  = score
                    best_action = a
            else:
                if score < best_score:
                    best_score  = score
                    best_action = a

        return best_score, best_action

    @staticmethod
    def _chance(st, action, depth, next_is_max, is_p1):
        """
        CHANCE NODE: tính Expected Value của một action.

        Xác định accuracy của skill được dùng:
            - Nếu action là switch → lấy skill của dragon mới
            - Nếu action là skill thường → lấy skill của active dragon

        Tính:
            E = acc × value(hit) + (1 - acc) × value(miss)

        Nếu acc = 1.0 (Slash, Power):
            Bỏ qua nhánh miss vì không bao giờ xảy ra
            → tiết kiệm tính toán

        Nếu acc < 1.0 (Ultim - accuracy 75%):
            Tính cả 2 nhánh và lấy trung bình có trọng số
        """
        cp  = st.cur()
        idx = action["di"] if action["t"] == "sw" else cp.ai
        acc = cp.dragons[idx].skills[action["si"]].accuracy / 100.0

        # Nhánh HIT (force=True): đòn luôn trúng
        sim_hit = st.clone()
        do_act(sim_hit, action, force=True)
        score_hit, _ = Expectimax._ex(sim_hit, depth - 1, next_is_max, is_p1)

        # Nhánh MISS (force=False): đòn luôn trượt
        score_miss = 0.0
        if acc < 1.0:
            sim_miss = st.clone()
            do_act(sim_miss, action, force=False)
            score_miss, _ = Expectimax._ex(sim_miss, depth - 1, next_is_max, is_p1)

        # Expected Value
        return acc * score_hit + (1.0 - acc) * score_miss