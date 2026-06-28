"""
MINIMAX
-------
- Giả định đối thủ luôn chơi TỐI ƯU nhất có thể.
- AI (lượt chẵn) là Maximizer: muốn score càng cao càng tốt.
- Đối thủ (lượt lẻ) là Minimizer: muốn score càng thấp càng tốt.
- Không có yếu tố ngẫu nhiên: mọi đòn đánh đều được tính là HIT.
- Ưu điểm: đảm bảo kết quả tối ưu trong worst case.
- Nhược điểm: chậm vì không cắt tỉa nhánh.
"""

from game.evaluate import evaluate
from game.do_act import do_act


class Minimax:

    @staticmethod
    def run(gs, depth=2):
        """Entry point: trả về action tốt nhất."""
        is_p1 = (gs.turn % 2 == 0)
        _, action = Minimax._mm(gs, depth, True, is_p1)
        return action

    @staticmethod
    def _mm(st, depth, is_maximizing, is_p1):
        """
        Đệ quy Minimax.

        Tham số:
            st           : game state hiện tại (đã clone)
            depth        : độ sâu còn lại
            is_maximizing: True = lượt AI (muốn max), False = lượt địch (muốn min)
            is_p1        : góc nhìn đánh giá (True = p1, False = p2)

        Trả về:
            (score, best_action)
        """
        # Base case
        if depth == 0 or st.over():
            return evaluate(st, is_p1), None

        acts = st.actions()
        if not acts:
            return evaluate(st, is_p1), None

        best_action = acts[0]
        best_score  = float('-inf') if is_maximizing else float('inf')

        for a in acts:
            # Simulate trên bản sao, force_hit=True (bỏ qua ngẫu nhiên)
            sim = st.clone()
            do_act(sim, a, force=True)

            score, _ = Minimax._mm(sim, depth - 1, not is_maximizing, is_p1)

            if is_maximizing:
                if score > best_score:
                    best_score  = score
                    best_action = a
            else:
                if score < best_score:
                    best_score  = score
                    best_action = a

        return best_score, best_action