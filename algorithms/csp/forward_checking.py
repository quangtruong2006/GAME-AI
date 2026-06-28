def solve_backtracking_fc(grid, rows, cols, start_r, start_c):
    """
    Backtracking + Forward Checking cho trò chơi laser.

    Theo mã giả BACKTRACK chuẩn, mở rộng thêm bước FORWARD-CHECK:

      function BACKTRACK(assignment, csp)
          if assignment is complete → return assignment
          var ← SELECT-UNASSIGNED-VARIABLE(assignment, csp)
          for each value in ORDER-DOMAIN-VALUES(var, assignment, csp):
              if CONSISTENT(var, value, assignment, csp):
                  add {var=value} to assignment
                  ── FORWARD CHECK: ô kế tiếp có khả thi không? ──
                  if forward_check passes:
                      result ← BACKTRACK(assignment, csp)
                      if result ≠ failure → return result
                  remove {var=value} from assignment
          return failure

    Điểm khác biệt so với Pure BT:
      FC nhìn trước 1 bước — nếu ô kế tiếp chắc chắn thất bại (ra biên/tường),
      cắt ngay không đệ quy, thu hẹp miền trị tương lai.

    KHÔNG dùng heuristic đích — domain vẫn theo thứ tự cố định.

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

    # ─── FORWARD-CHECK ───────────────────────────────────────────────────────
    def FORWARD_CHECK(next_r, next_c):
        """
        Kiểm tra ô kế tiếp tia sẽ đến sau khi gán.
        Nếu ra biên hoặc là tường → miền trị tương lai rỗng → cắt sớm.
        """
        if not (0 <= next_r < rows and 0 <= next_c < cols):
            return "failure"
        if grid[next_r][next_c] == 3:
            return "failure"
        return "success"

    # ─── SELECT-UNASSIGNED-VARIABLE ──────────────────────────────────────────
    def SELECT_UNASSIGNED_VARIABLE(assignment):
        status, info = trace_laser(assignment)
        return info if status == "var" else None

    # ─── ORDER-DOMAIN-VALUES ─────────────────────────────────────────────────
    def ORDER_DOMAIN_VALUES(var, assignment):
        """
        Thứ tự cố định: 0, 1, 2.
        Không dùng heuristic — thuật toán không biết đích ở đâu.
        """
        return [0, 1, 2]

    # ─── CONSISTENT ──────────────────────────────────────────────────────────
    def CONSISTENT(var, value, assignment):
        r, c, _, _ = var
        assignment[(r, c)] = value
        status, _ = trace_laser(assignment)
        del assignment[(r, c)]
        return status != "fail"

    # ─── BACKTRACK với FORWARD CHECKING ──────────────────────────────────────
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

                # ── FORWARD CHECKING ──────────────────────────────────────
                ndr, ndc       = reflect(dr, dc, value)
                next_r, next_c = r + ndr, c + ndc

                if FORWARD_CHECK(next_r, next_c) != "failure":
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