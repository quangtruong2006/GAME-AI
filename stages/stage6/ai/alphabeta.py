"""
ALPHA-BETA PRUNING
------------------
- Cùng kết quả với Minimax nhưng NHANH HƠN đáng kể.
- Loại bỏ các nhánh chắc chắn không ảnh hưởng tới quyết định cuối.

Nguyên lý cắt tỉa:
    alpha = điểm tốt nhất Maximizer đã tìm được (khởi đầu -inf)
    beta  = điểm tốt nhất Minimizer đã tìm được (khởi đầu +inf)

    Khi beta <= alpha:
        - Maximizer sẽ không bao giờ chọn nhánh này
        - Cắt tỉa (break) ngay lập tức

- Ưu điểm: nhanh hơn Minimax, cùng kết quả.
- Nhược điểm: vẫn là worst-case như Minimax nếu thứ tự actions tệ.
"""

from evaluation import evaluate_state
from combat import Combat


class AlphaBeta:

    @staticmethod
    def run(gs, depth=2):
        """Entry point: trả về action tốt nhất."""
        is_p1 = (gs.turn_count % 2 == 0)
        _, action = AlphaBeta._ab(
            gs, depth,
            alpha=float('-inf'),
            beta=float('inf'),
            is_maximizing=True,
            is_p1=is_p1
        )
        return action

    @staticmethod
    def _ab(st, depth, alpha, beta, is_maximizing, is_p1):
        """
        Đệ quy Alpha-Beta Pruning.

        Tham số:
            st           : game state hiện tại
            depth        : độ sâu còn lại
            alpha        : best score Maximizer đảm bảo được
            beta         : best score Minimizer đảm bảo được
            is_maximizing: True = lượt AI, False = lượt địch
            is_p1        : góc nhìn đánh giá

        Trả về:
            (score, best_action)
        """
        if depth == 0 or st.is_game_over():
            return evaluate_state(st, is_p1), None

        acts = st.get_possible_actions()
        if not acts:
            return evaluate_state(st, is_p1), None

        best_action = acts[0]
        best_score  = float('-inf') if is_maximizing else float('inf')

        for a in acts:
            sim = st.clone()
            Combat.execute_action(sim, a, is_real_combat=False, force_hit=True)

            score, _ = AlphaBeta._ab(
                sim, depth - 1, alpha, beta, not is_maximizing, is_p1
            )

            if is_maximizing:
                if score > best_score:
                    best_score  = score
                    best_action = a
                alpha = max(alpha, best_score)
            else:
                if score < best_score:
                    best_score  = score
                    best_action = a
                beta = min(beta, best_score)

            if beta <= alpha:
                break

        return best_score, best_action
