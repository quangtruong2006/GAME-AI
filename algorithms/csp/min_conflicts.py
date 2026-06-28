# File: algorithms/csp/min_conflicts.py

import random

def solve_min_conflicts(grid, rows, cols, start_r, start_c):
    MAX_STEPS = 9000
    RESTART_LIMIT = 150 # Chờ 150 bước ngọn laser đứng im mới đập bàn cờ
    
    variables = [(r, c) for r in range(rows) for c in range(cols) if grid[r][c] == 0]
    var_set = set(variables)

    if not variables: yield False; return

    def reflect(dr, dc, v):
        if v == 1: return -dc, -dr
        if v == 2: return dc, dr
        return dr, dc

    def evaluate_board():
        r, c, dr, dc = start_r, start_c, 0, 1
        visited = set(); path = []
        while True:
            if not (0 <= r < rows and 0 <= c < cols): return "out_of_bounds", path
            
            st = (r, c, dr, dc)
            if st in visited: 
                try: return "loop", path[path.index((r, c)):]
                except ValueError: return "loop", path
                    
            visited.add(st); path.append((r, c))
            v = grid[r][c]
            
            if v == 3: return "hit_rock", path
            if v == 9: return "success", path
            dr, dc = reflect(dr, dc, v); r, c = r + dr, c + dc

    def CONFLICTS(var_r, var_c, v):
        old = grid[var_r][var_c]; grid[var_r][var_c] = v
        status, _ = evaluate_board()
        grid[var_r][var_c] = old
        
        score = 0
        if status == "loop": score += 10 
        elif status in ["hit_rock", "out_of_bounds"]: score += 1 
        if status != "success": score += 1
        return score

    # Khởi tạo ban đầu (Nhiều ô trống hơn để map sạch sẽ)
    for (r, c) in variables: grid[r][c] = random.choice([0, 0, 0, 1, 2])
    yield "update"

    stuck = 0
    last_endpoint = None

    for i in range(MAX_STEPS):
        status, path = evaluate_board()
        
        if status == "success":
            for (r, c) in variables:
                if (r, c) not in path: grid[r][c] = 0
            yield "update"; yield True; return

        current_endpoint = path[-1] if path else (start_r, start_c)
        if current_endpoint != last_endpoint:
            last_endpoint = current_endpoint
            stuck = 0 # Ngọn laser dịch chuyển -> Xóa án kẹt!
        else:
            stuck += 1 # Ngọn laser đứng im một chỗ -> Bắt đầu đếm kẹt

        conflicted = [(r, c) for (r, c) in path if (r, c) in var_set]
        
        if conflicted:
            if status == "loop": 
                mirrors = [p for p in conflicted if grid[p[0]][p[1]] in (1, 2)]
                var_r, var_c = random.choice(mirrors if mirrors else conflicted)
            else: 
                # ========================================================
                # CƠ CHẾ RÚT LUI CHIẾN THUẬT (KHÔNG BAO GIỜ DỰT VỀ TÍT TRƯỚC NỮA)
                # ========================================================
                # Cứ 3 bước kẹt ở ngọn, nó sẽ lùi về cái gương trước đó 1 nhịp
                retreat_steps = stuck // 3
                target_index = -1 - retreat_steps
                
                # Hàm max() để đảm bảo AI không lùi quá xa lọt ra ngoài mảng
                target_index = max(target_index, -len(conflicted)) 
                
                var_r, var_c = conflicted[target_index]
        else: 
            var_r, var_c = random.choice(list(var_set)) 

        current_val = grid[var_r][var_c]
        best_vals = []; min_conflicts = float("inf")
        
        for v in [0, 1, 2]:
            if v == current_val: continue
            c = CONFLICTS(var_r, var_c, v)
            if c < min_conflicts: min_conflicts = c; best_vals = [v]
            elif c == min_conflicts: best_vals.append(v)

        if not best_vals: best_vals = [v for v in [0, 1, 2] if v != current_val]
        grid[var_r][var_c] = random.choice(best_vals)
        yield "update"

        if stuck >= RESTART_LIMIT:
            for (r, c) in variables: grid[r][c] = random.choice([0, 0, 0, 1, 2])
            stuck = 0
            last_endpoint = None
            yield "update"

    yield False