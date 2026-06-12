import time

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def a_star(grid, start, goal):
    start_time = time.time()
    rows, cols = len(grid), len(grid[0])
    
    # Đổi thành kiểm tra tường = 99
    if grid[start[0]][start[1]] == 99 or grid[goal[0]][goal[1]] == 99:
        return [], [], 0, "0.0 ms"

    g_score = {start: 0}
    frontier = [(heuristic(start, goal), start)]
    reached = set()
    parent = {start: None}
    visited_order = []
    found = False

    while frontier:
        frontier.sort(key=lambda x: x[0])
        f_n, n = frontier.pop(0)

        if n != start and n != goal and n not in visited_order:
            visited_order.append(n)

        if n == goal:
            found = True
            break

        reached.add(n)

        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            m = (n[0] + dr, n[1] + dc)
            
            # Đổi điều kiện check tường thành != 99
            if 0 <= m[0] < rows and 0 <= m[1] < cols and grid[m[0]][m[1]] != 99:
                cost_m = grid[m[0]][m[1]] # Đọc chi phí thực tế từ ô lưới (1, 3, 5, 8)
                g_new_m = g_score[n] + cost_m
                
                in_frontier = False
                frontier_idx = -1
                for idx, item in enumerate(frontier):
                    if item[1] == m:
                        in_frontier = True
                        frontier_idx = idx
                        break

                if m in reached:
                    if g_new_m >= g_score.get(m, float('inf')):
                        continue
                    else:
                        reached.remove(m)
                        g_score[m] = g_new_m
                        f_m = g_new_m + heuristic(m, goal)
                        parent[m] = n
                        frontier.append((f_m, m))

                elif in_frontier:
                    if g_new_m < g_score.get(m, float('inf')):
                        g_score[m] = g_new_m
                        f_m = g_new_m + heuristic(m, goal)
                        parent[m] = n
                        frontier[frontier_idx] = (f_m, m)
                else:
                    g_score[m] = g_new_m
                    f_m = g_new_m + heuristic(m, goal)
                    parent[m] = n
                    frontier.append((f_m, m))

    path = []
    if found:
        curr = goal
        while curr is not None:
            if curr != start and curr != goal:
                path.append(curr)
            curr = parent[curr]
        path.reverse()

    end_time = time.time()
    exec_time = (end_time - start_time) * 1000
    return path, visited_order, len(visited_order), f"{exec_time:.2f} ms"