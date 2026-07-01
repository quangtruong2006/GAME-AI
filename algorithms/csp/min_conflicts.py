# File: algorithms/csp/min_conflicts.py
import random


def solve_min_conflicts(grid, rows, cols, start_r, start_c):
    """
    MIN-CONFLICTS bám mã giả AIMA, đồng bộ cấu trúc ràng buộc với bản
    Pure Backtracking (solve_pure_backtracking).

    RÀNG BUỘC:
        trace_laser() trả "fail" nếu tia ra biên / đâm đá / lặp vô hạn.
        "goal" không phải ràng buộc, chỉ là điều kiện kết thúc/thắng,
        kiểm tra riêng ở is_current_a_solution().

    GIỚI HẠN CHẠY:
        MAX_STEPS = 1000, STUCK_LIMIT = 50 để dừng sớm khi phát hiện
        lặp lại trạng thái cũ (plateau/local optimum), tránh chờ quá lâu.
    """

    MAX_STEPS   = 1000
    STUCK_LIMIT = 50

    variables = [(r, c) for r in range(rows) for c in range(cols) if grid[r][c] == 0]
    var_set = set(variables)

    if not variables:
        print("[MIN-CONFLICTS] Không có ô trống nào để gán biến -> failure ngay.")
        yield False
        return

    def reflect(dr, dc, val):
        if val == 1:
            return -dc, -dr
        if val == 2:
            return dc, dr
        return dr, dc

    def trace_laser():
        r, c, dr, dc = start_r, start_c, 0, 1
        visited_states = set()
        path = []
        while True:
            if not (0 <= r < rows and 0 <= c < cols):
                return "fail", path, "out_of_bounds"

            state = (r, c, dr, dc)
            if state in visited_states:
                return "fail", path, "loop"
            visited_states.add(state)
            path.append((r, c))

            v = grid[r][c]
            if v == 3:
                return "fail", path, "hit_rock"
            if v == 9:
                return "goal", path, None

            dr, dc = reflect(dr, dc, v)
            r, c = r + dr, c + dc

    def is_current_a_solution():
        status, path, _ = trace_laser()
        return (status == "goal"), path

    def CONFLICTS(var_r, var_c, v):
        old = grid[var_r][var_c]
        grid[var_r][var_c] = v
        status, _, _ = trace_laser()
        grid[var_r][var_c] = old
        return 0 if status == "goal" else 1

    # ── current <- an initial complete assignment for csp ──
    for (r, c) in variables:
        grid[r][c] = random.choice([0, 1, 2])
    yield "update"

    seen_states = set()
    stuck_counter = 0

    # ── for i = 1 to max_steps do ──
    for i in range(MAX_STEPS):

        is_solution, path = is_current_a_solution()
        if is_solution:
            for (r, c) in variables:
                if (r, c) not in path:
                    grid[r][c] = 0
            print(f"[MIN-CONFLICTS] Tìm ra nghiệm sau {i} bước.")
            yield "update"
            yield True
            return

        _, _, fail_reason = trace_laser()

        # ── Phát hiện bế tắc/plateau để dừng sớm ──
        state_key = tuple(grid[r][c] for (r, c) in variables)
        if state_key in seen_states:
            stuck_counter += 1
        else:
            seen_states.add(state_key)
            stuck_counter = 0
            if len(seen_states) > 2000:
                seen_states.clear()

        if stuck_counter >= STUCK_LIMIT:
            print(f"[MIN-CONFLICTS] DỪNG SỚM tại bước {i}: "
                  f"lặp lại cùng tập trạng thái {STUCK_LIMIT} lần liên tiếp "
                  f"(plateau/local optimum). Ràng buộc vi phạm lần cuối: '{fail_reason}'.")
            yield False
            return

        # var <- a randomly chosen conflicted variable
        conflicted_vars = [(r, c) for (r, c) in path if (r, c) in var_set]
        if not conflicted_vars:
            var_r, var_c = random.choice(variables)
        else:
            var_r, var_c = random.choice(conflicted_vars)

        # value <- the value v that minimizes CONFLICTS(var, v, current, csp)
        best_conflicts = float("inf")
        best_candidates = []
        for v in [0, 1, 2]:
            c_count = CONFLICTS(var_r, var_c, v)
            if c_count < best_conflicts:
                best_conflicts = c_count
                best_candidates = [v]
            elif c_count == best_conflicts:
                best_candidates.append(v)

        best_value = random.choice(best_candidates)
        grid[var_r][var_c] = best_value
        yield "update"

    print(f"[MIN-CONFLICTS] Hết {MAX_STEPS} bước mà chưa tìm được nghiệm -> failure.")
    yield False