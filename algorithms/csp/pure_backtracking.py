def solve_pure_backtracking(grid, rows, cols, start_r, start_c):
    """
    Pure Backtracking cho trò chơi laser.

    Theo đúng mã giả AIMA:
      function BACKTRACKING-SEARCH(csp)  →  return BACKTRACK({}, csp)
      function BACKTRACK(assignment, csp)
          if assignment is complete → return assignment
          var ← SELECT-UNASSIGNED-VARIABLE(assignment, csp)
          for each value in ORDER-DOMAIN-VALUES(var, assignment, csp):
              if CONSISTENT(var, value, assignment, csp):
                  add {var=value} to assignment
                  result ← BACKTRACK(assignment, csp)
                  if result ≠ failure → return result
                  remove {var=value} from assignment
          return failure

    KHÔNG dùng heuristic đích — thuật toán mù, thử domain theo thứ tự cố định.

    Quy ước grid:
      0 = trống   1 = gương '/'   2 = gương '\\'
      3 = tường   8 = nguồn laser  9 = lõi đích
    """

    START_DIR  = (0, 1)
    NODE_LIMIT = 200_000
    node_counter = [0]

    # ─── Hàm phụ trợ ──────────────────────────────────────────────────────────
    def reflect(dr, dc, val):
        if val == 1:
            return -dc, -dr
        if val == 2:
            return  dc,  dr
        return dr, dc

    def trace_laser(assignment):
        """
        Mô phỏng tia laser với assignment hiện tại.
        Trả về:
          ("goal", None)           – chạm đích
          ("var",  (r,c,dr,dc))    – gặp ô trống chưa gán → biến kế tiếp
          ("fail", None)           – ra biên / đâm tường / vòng lặp
        """
        r, c   = start_r, start_c
        dr, dc = START_DIR
        visited = set()

        while True:
            if not (0 <= r < rows and 0 <= c < cols):
                return "fail", None

            cell = grid[r][c]
            if cell == 3:
                return "fail", None
            if cell == 9:
                return "goal", None

            state = (r, c, dr, dc)
            if state in visited:
                return "fail", None
            visited.add(state)

            if cell == 0 and (r, c) not in assignment:
                return "var", (r, c, dr, dc)

            val    = assignment.get((r, c), cell)
            dr, dc = reflect(dr, dc, val)
            r, c   = r + dr, c + dc

    # ─── SELECT-UNASSIGNED-VARIABLE ──────────────────────────────────────────
    def SELECT_UNASSIGNED_VARIABLE(assignment):
        """Biến tiếp theo = ô trống đầu tiên tia laser gặp."""
        status, info = trace_laser(assignment)
        return info if status == "var" else None

    # ─── ORDER-DOMAIN-VALUES ─────────────────────────────────────────────────
    def ORDER_DOMAIN_VALUES(var, assignment):
        """
        Thứ tự cố định: 0 (đi thẳng), 1 (gương /), 2 (gương \\).
        Không dùng heuristic — thuật toán không biết đích ở đâu.
        """
        return [0, 1, 2]

    # ─── CONSISTENT ──────────────────────────────────────────────────────────
    def CONSISTENT(var, value, assignment):
        """Gán thử var=value, kiểm tra tia không lập tức thất bại."""
        r, c, _, _ = var
        assignment[(r, c)] = value
        status, _ = trace_laser(assignment)
        del assignment[(r, c)]
        return status != "fail"

    # ─── BACKTRACK ───────────────────────────────────────────────────────────
    def BACKTRACK(assignment):
        node_counter[0] += 1
        if node_counter[0] > NODE_LIMIT:
            return "failure"

        # if assignment is complete → return assignment
        status, _ = trace_laser(assignment)
        if status == "goal":
            return assignment
        if status == "fail":
            return "failure"

        # var ← SELECT-UNASSIGNED-VARIABLE(assignment, csp)
        var = SELECT_UNASSIGNED_VARIABLE(assignment)
        if var is None:
            return "failure"

        r, c, dr, dc = var
        old = grid[r][c]

        # for each value in ORDER-DOMAIN-VALUES(var, assignment, csp)
        for value in ORDER_DOMAIN_VALUES(var, assignment):

            # if CONSISTENT(var, value, assignment, csp)
            if CONSISTENT(var, value, assignment):

                # add {var=value} to assignment
                assignment[(r, c)] = value
                grid[r][c] = value
                yield "update"

                # result ← BACKTRACK(assignment, csp)
                result = yield from BACKTRACK(assignment)

                # if result ≠ failure → return result
                if result != "failure":
                    return result

                # remove {var=value} from assignment
                del assignment[(r, c)]
                grid[r][c] = old
                yield "update"

        return "failure"

    # ─── BACKTRACKING-SEARCH ─────────────────────────────────────────────────
    final = yield from BACKTRACK({})
    yield (final != "failure")